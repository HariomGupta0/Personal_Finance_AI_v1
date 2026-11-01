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

from backend.app.api.deps import (
    get_current_user_id,
    get_ingestion_service,
    get_neo4j_service,
)
from backend.app.core.money import normalize_rupees, to_paise
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

# Module-level references kept for test mocking compatibility
db = None
ingestion = None

router = APIRouter(prefix="/api/import", tags=["Import"])

# Limits
MAX_CSV_BYTES = 5 * 1024 * 1024    # 5 MB
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB


# ---------------------------------------------------------------------------

# Pydantic schemas for confirm endpoint
# ---------------------------------------------------------------------------

class ConfirmRow(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    description: str = Field(..., min_length=1, max_length=250)
    amount: float = Field(..., gt=0)
    type: str = Field(..., description="EXPENSE or INCOME")
    category: Optional[str] = Field(None, max_length=100)
    category_source: Optional[str] = Field(None, max_length=50)
    clean_merchant: Optional[str] = Field(None, max_length=100)
    fingerprint: Optional[str] = Field(None, max_length=100)
    account_id: Optional[str] = None
    source_ref: Optional[str] = Field(None, max_length=200)
    source_type: Optional[str] = Field(None, max_length=50)

    @field_validator("amount", mode="before")
    @classmethod
    def _normalize_amount(cls, v):
        if v is None:
            return v
        try:
            return normalize_rupees(v)
        except Exception:
            return v

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        normalized = v.upper().strip()
        if normalized not in {"EXPENSE", "INCOME"}:
            raise ValueError("type must be EXPENSE or INCOME")
        return normalized


class ConfirmImportRequest(BaseModel):
    rows: List[ConfirmRow] = Field(..., min_length=1)
    import_id: Optional[str] = Field(None, description="Optional idempotency key / import job identifier")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/csv")
async def upload_csv(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    user_mapping: Optional[str] = None,   # JSON string of column mapping override
    db: Neo4jService = Depends(get_neo4j_service),
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

    # Empty check
    if not content or len(content.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # Binary check (null bytes indicate binary/executable files)
    if b"\x00" in content[:1024]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Binary file detected. Only plain-text CSV, TSV, or TXT statements are supported.",
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

    accepted_rows = pipeline_result.get("accepted_rows", [])
    duplicate_rows = pipeline_result.get("duplicate_rows", [])
    skipped_rows = parse_result.get("skipped_rows", [])
    parse_errors = parse_result.get("errors", [])
    invalid_rows = pipeline_result.get("invalid_rows", [])

    all_rejected = [
        {
            "row_index": e.get("row_index", 0),
            "error": e.get("error", ""),
            "reason": e.get("reason", e.get("error", "")),
            "raw": e.get("raw", {}),
        }
        for e in parse_errors
    ] + [
        {
            "row_index": inv.get("row_index", 0),
            "error": inv.get("error", ""),
            "reason": inv.get("error", ""),
            "raw": inv.get("row", {}),
        }
        for inv in invalid_rows
    ]

    total_rows = len(accepted_rows) + len(duplicate_rows) + len(skipped_rows) + len(all_rejected)

    stats = {
        "total_rows": total_rows,
        "accepted_count": len(accepted_rows),
        "duplicate_count": len(duplicate_rows),
        "skipped_count": len(skipped_rows),
        "rejected_count": len(all_rejected),
        # Backward compatibility
        "valid": len(pipeline_result["valid_rows"]),
        "invalid": len(invalid_rows),
        "parse_errors": len(parse_errors),
        "possible_duplicates": sum(
            1 for r in pipeline_result["valid_rows"]
            if r.get("duplicate_status") == "POSSIBLE_DUPLICATE"
        ),
        "confirmed_duplicates": sum(
            1 for r in pipeline_result["valid_rows"]
            if r.get("duplicate_status") == "CONFIRMED_DUPLICATE"
        ),
    }

    return {
        "status": "PARSED",
        "filename": filename,
        "columns": parse_result["columns"],
        "mapping": parse_result["mapping"],
        "ambiguous": parse_result["ambiguous"],
        "date_ambiguity": parse_result.get("date_ambiguity", False),
        "unrecognized_columns": parse_result.get("unrecognized_columns", []),
        "valid_rows": pipeline_result["valid_rows"],
        "accepted_rows": accepted_rows,
        "duplicate_rows": duplicate_rows,
        "rejected_rows": all_rejected,
        "skipped_rows": skipped_rows,
        "warnings": parse_result["warnings"] + pipeline_result["warnings"],
        "confirmation_required": True,
        "stats": stats,
        # Backward compatibility
        "invalid_rows": invalid_rows,
        "parse_errors": parse_errors,
    }


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    db: Neo4jService = Depends(get_neo4j_service),
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

    sanity_flag = extraction.get("sanity_flag", False)
    sanity_issues = extraction.get("sanity_issues", [])

    return {
        "status": "EXTRACTED",
        "filename": filename,
        "extraction": extraction,
        "preview_rows": pipeline_rows,
        "warnings": extraction.get("warnings", []) + pipeline_warnings,
        "sanity_flag": sanity_flag,
        "sanity_issues": sanity_issues,
        "requires_review": (
            not sanity_flag
            or not extraction.get("extraction_success")
            or extraction.get("confidence") in ("low", "medium")
            or extraction.get("transaction_status") != "SUCCESS"
        ),
    }


@router.post("/confirm")
def confirm_import(
    payload: ConfirmImportRequest,
    user_id: str = Depends(get_current_user_id),
    db: Neo4jService = Depends(get_neo4j_service),
    ingestion: IngestionService = Depends(get_ingestion_service),
):
    """
    Persist confirmed rows to Neo4j.
    Uses high-speed batch UNWIND insertion with idempotency constraints.
    """
    if not payload.rows:
        return {"status": "SUCCESS", "saved": 0, "failed": 0, "results": []}

    user_accounts = db.get_user_accounts(user_id)
    if not user_accounts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No account found for user '{user_id}'. Please create an account before importing transactions.",
        )
    user_account_ids = {a["id"] for a in user_accounts}

    account_id = payload.rows[0].account_id
    if account_id:
        if account_id not in user_account_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Account '{account_id}' does not belong to authenticated user.",
            )
    else:
        account_id = user_accounts[0]["id"]

    for r in payload.rows:
        if r.account_id and r.account_id not in user_account_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Transaction specifies account '{r.account_id}' which does not belong to authenticated user.",
            )
        r.account_id = account_id

    from collections import Counter
    from backend.app.services.fingerprint import compute_transaction_fingerprint
    from backend.app.services.merchant_normalizer import normalize_narration

    occurrence_counter = Counter()
    batch_rows = []

    for r in payload.rows:
        row_dict = r.model_dump()
        tx_type = r.type
        amt = normalize_rupees(r.amount)
        amt_paise = to_paise(amt)
        desc = r.description
        source_ref = r.source_ref

        tuple_key = (r.date, amt_paise, tx_type, desc.lower(), str(source_ref or "").lower())
        occ = occurrence_counter[tuple_key]
        occurrence_counter[tuple_key] += 1

        fp = r.fingerprint or compute_transaction_fingerprint(
            account_id=account_id or "A001",
            date_str=r.date,
            amount=amt,
            tx_type=tx_type,
            description=desc,
            source_ref=source_ref,
            occurrence_index=occ,
        )
        row_dict["fingerprint"] = fp

        if not row_dict.get("clean_merchant"):
            norm = normalize_narration(desc, tx_type)
            row_dict["clean_merchant"] = norm.clean_merchant
            row_dict.setdefault("category_source", norm.category_source)

        batch_rows.append(row_dict)

    if hasattr(db, "batch_add_transactions"):
        try:
            batch_result = db.batch_add_transactions(
                user_id=user_id,
                account_id=account_id,
                rows=batch_rows,
                import_id=payload.import_id,
            )
            is_repeat = (batch_result["inserted"] == 0 and batch_result["skipped"] > 0)
            return {
                "status": "SUCCESS",
                "saved": batch_result["inserted"],
                "skipped_duplicates": batch_result["skipped"],
                "failed": 0,
                "net_balance_delta": batch_result["net_balance_delta"],
                "import_id": batch_result["import_id"],
                "idempotent": True,
                "is_repeat_confirmation": is_repeat,
                "message": (
                    f"Successfully imported {batch_result['inserted']} new transaction(s)."
                    + (f" Skipped {batch_result['skipped']} duplicate(s)." if batch_result["skipped"] > 0 else "")
                    + (" (Safe repeat: no duplicate balances applied)" if is_repeat else "")
                ),
                "results": [
                    {
                        "status": "SAVED",
                        "type": r["type"],
                        "description": r["description"],
                        "amount": r["amount"],
                        "fingerprint": r["fingerprint"],
                    }
                    for r in batch_rows
                ],
            }
        except Exception as exc:
            logger.warning("Batch insertion failed, falling back to sequential ingestion: %s", exc)

    # Fallback to sequential row-by-row if batch is not supported or failed
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
                results.append({"status": "SAVED", "type": "INCOME", "description": row.description, "amount": row.amount, "record": record.get("income")})
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
                results.append({"status": "SAVED", "type": row.type, "description": row.description, "amount": row.amount, "record": record.get("transaction")})
            saved += 1
        except Exception as exc:
            failed += 1
            results.append({"status": "FAILED", "type": row.type, "description": row.description, "amount": row.amount, "error": str(exc)})

    return {
        "status": "SUCCESS" if failed == 0 else ("PARTIAL" if saved > 0 else "FAILED"),
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
