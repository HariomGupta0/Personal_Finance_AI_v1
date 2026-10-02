"""
Import API — CSV and image upload endpoints.

Endpoints:
  POST /api/import/csv    — upload a bank statement CSV; returns parsed preview
  POST /api/import/image  — upload a receipt/screenshot; returns extracted fields
  POST /api/import/confirm — persist confirmed rows to Neo4j

Security:
  - All endpoints require an authenticated session cookie.
  - File size is limited (5 MB for CSV, 10 MB for images).
  - Actual MIME type is validated from magic bytes, not the Content-Type header.
  - Uploaded content is never logged at statement level.
  - Users can only confirm their own import jobs (session-bound).
  - The LLM/OCR service NEVER writes to the database directly.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field, field_validator

from backend.app.api.deps import get_current_user_id
from backend.app.database.neo4j_service import Neo4jService
from backend.app.services.csv_parser import CSVParseError, parse_csv
from backend.app.services.image_extractor import (
    SUPPORTED_MIME_TYPES,
    _detect_mime,
    extract_from_image,
)
from backend.app.services.import_pipeline import run_pipeline
from backend.app.services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/import", tags=["Import"])

# Limits
MAX_CSV_BYTES = 5 * 1024 * 1024    # 5 MB
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB


# ---------------------------------------------------------------------------
# Shared DB instances (same pattern as existing routers)
# ---------------------------------------------------------------------------

db = Neo4jService()
ingestion = IngestionService(db=db)


# ---------------------------------------------------------------------------
# Pydantic schemas for confirm endpoint
# ---------------------------------------------------------------------------

class ConfirmRow(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    description: str = Field(..., min_length=1, max_length=250)
    amount: float = Field(..., gt=0)
    type: str = Field(..., description="EXPENSE or INCOME")
    category: Optional[str] = Field(None, max_length=100)
    account_id: Optional[str] = None
    source_ref: Optional[str] = Field(None, max_length=200)
    source_type: Optional[str] = Field(None, max_length=50)

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        normalized = v.upper().strip()
        if normalized not in {"EXPENSE", "INCOME"}:
            raise ValueError("type must be EXPENSE or INCOME")
        return normalized


class ConfirmImportRequest(BaseModel):
    rows: List[ConfirmRow] = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/csv")
async def upload_csv(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    user_mapping: Optional[str] = None,   # JSON string of column mapping override
):
    """
    Parse a bank statement CSV and return a preview for user confirmation.
    Does NOT write anything to the database.
    """
    # Size check
    content = await file.read(MAX_CSV_BYTES + 1)
    if len(content) > MAX_CSV_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"CSV file exceeds {MAX_CSV_BYTES // (1024 * 1024)} MB limit.",
        )

    # Filename extension check (soft — not a security boundary)
    filename = file.filename or ""
    if not filename.lower().endswith((".csv", ".tsv", ".txt")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .csv / .tsv / .txt files are accepted.",
        )

    # Parse user_mapping override if supplied
    parsed_mapping = None
    if user_mapping:
        import json
        try:
            parsed_mapping = json.loads(user_mapping)
        except Exception:
            raise HTTPException(status_code=400, detail="user_mapping is not valid JSON.")

    try:
        parse_result = parse_csv(content, user_mapping=parsed_mapping)
    except CSVParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("CSV parse unexpected error: %s", type(exc).__name__)
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {exc}")

    # Run normalize + validate + dedup pipeline
    pipeline_result = run_pipeline(
        raw_rows=parse_result["rows"],
        user_id=user_id,
        db=db,
    )

    return {
        "status": "PARSED",
        "filename": filename,
        "columns": parse_result["columns"],
        "mapping": parse_result["mapping"],
        "ambiguous": parse_result["ambiguous"],
        "valid_rows": pipeline_result["valid_rows"],
        "invalid_rows": pipeline_result["invalid_rows"],
        "warnings": parse_result["warnings"] + pipeline_result["warnings"],
        "stats": {
            "total_rows": len(parse_result["rows"]) + len(parse_result["errors"]),
            "parse_errors": len(parse_result["errors"]),
            "valid": len(pipeline_result["valid_rows"]),
            "invalid": len(pipeline_result["invalid_rows"]),
            "possible_duplicates": sum(
                1 for r in pipeline_result["valid_rows"]
                if r.get("duplicate_status") == "POSSIBLE_DUPLICATE"
            ),
            "confirmed_duplicates": sum(
                1 for r in pipeline_result["valid_rows"]
                if r.get("duplicate_status") == "CONFIRMED_DUPLICATE"
            ),
        },
        "parse_errors": parse_result["errors"],
    }


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
):
    """
    Extract transaction information from a receipt or payment screenshot.
    Returns extracted fields for user review — does NOT write to the database.
    """
    content = await file.read(MAX_IMAGE_BYTES + 1)
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image exceeds {MAX_IMAGE_BYTES // (1024 * 1024)} MB limit.",
        )

    # Validate actual image format from magic bytes
    try:
        _detect_mime(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    filename = file.filename or "upload"

    try:
        extraction = extract_from_image(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Image extraction unexpected error: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail=f"Image extraction failed: {exc}")

    # Remove raw_response (not useful to user; may contain base64 fragments)
    extraction.pop("raw_response", None)

    # If extraction produced a usable row, run it through the pipeline for dedup
    pipeline_rows = []
    pipeline_warnings: list[str] = []
    if extraction.get("extraction_success") and extraction.get("amount"):
        pipeline_result = run_pipeline(
            raw_rows=[{
                "date": extraction.get("date"),
                "amount": extraction.get("amount"),
                "description": extraction.get("description") or f"Image import ({filename})",
                "type": extraction.get("type") or "EXPENSE",
                "category": None,
                "source_ref": extraction.get("source_ref"),
                "source_type": "image",
            }],
            user_id=user_id,
            db=db,
        )
        pipeline_rows = pipeline_result["valid_rows"]
        pipeline_warnings = pipeline_result["warnings"]

    return {
        "status": "EXTRACTED",
        "filename": filename,
        "extraction": extraction,
        "preview_rows": pipeline_rows,
        "warnings": extraction.get("warnings", []) + pipeline_warnings,
        "requires_review": (
            not extraction.get("extraction_success")
            or extraction.get("confidence") in ("low", "medium")
            or extraction.get("transaction_status") != "SUCCESS"
        ),
    }


@router.post("/confirm")
def confirm_import(
    payload: ConfirmImportRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Persist confirmed rows to Neo4j.

    Only rows explicitly selected and confirmed by the user are saved.
    Any row that fails to save is reported individually — partial saves are allowed
    but the overall status reflects failures.
    """
    results = []
    saved = 0
    failed = 0

    for row in payload.rows:
        try:
            if row.type == "INCOME":
                record = ingestion.ingest_income(
                    user_id=user_id,
                    source=row.description,
                    amount=row.amount,
                    date_str=row.date,
                    account_id=row.account_id,
                )
                # Store source_ref on the income node if available
                if row.source_ref and record.get("income", {}).get("income_id"):
                    _attach_source_ref(
                        db, "Income", record["income"]["income_id"], row.source_ref, row.source_type
                    )
                results.append({
                    "status": "SAVED",
                    "type": "INCOME",
                    "description": row.description,
                    "amount": row.amount,
                    "record": record.get("income"),
                })
            else:
                record = ingestion.ingest_transaction(
                    user_id=user_id,
                    account_id=row.account_id,
                    amount=row.amount,
                    description=row.description,
                    category_name=row.category or "General",
                    transaction_type=row.type,
                    date_str=row.date,
                )
                tx = record.get("transaction", {})
                # Store source_ref on the transaction node if available
                if row.source_ref and tx.get("transaction_id"):
                    _attach_source_ref(
                        db, "Transaction", tx["transaction_id"], row.source_ref, row.source_type
                    )
                results.append({
                    "status": "SAVED",
                    "type": row.type,
                    "description": row.description,
                    "amount": row.amount,
                    "record": tx,
                })
            saved += 1

        except Exception as exc:
            logger.error(
                "Failed to save import row (user=%s, desc=%s): %s",
                user_id,
                row.description[:40] if row.description else "?",
                type(exc).__name__,
            )
            results.append({
                "status": "FAILED",
                "type": row.type,
                "description": row.description,
                "amount": row.amount,
                "error": str(exc),
            })
            failed += 1

    overall = "SUCCESS" if failed == 0 else ("PARTIAL" if saved > 0 else "FAILED")

    return {
        "status": overall,
        "saved": saved,
        "failed": failed,
        "results": results,
    }


# ---------------------------------------------------------------------------
# Helper: attach source_ref property to an existing node
# ---------------------------------------------------------------------------

def _attach_source_ref(db: Neo4jService, label: str, node_id: str, source_ref: str, source_type: Optional[str]):
    """Idempotent: set source_ref and source_type on a Transaction or Income node."""
    if label not in ("Transaction", "Income"):
        return
    id_field = "id"
    cypher = (
        f"MATCH (n:{label} {{{id_field}: $node_id}}) "
        "SET n.source_ref = $source_ref, n.source_type = $source_type"
    )
    try:
        with db.driver.session(database=db.database) as session:
            session.run(cypher, node_id=node_id, source_ref=source_ref, source_type=source_type or "import")
    except Exception:
        pass  # Non-fatal
