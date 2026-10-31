"""
Shared import pipeline.

Responsibilities:
  1. Normalize raw parsed rows into the canonical transaction schema.
  2. Validate each row (amount > 0, date parseable, type valid).
  3. Detect possible duplicates against Neo4j without writing anything.

The pipeline does NOT write to the database. That is done only after
the user explicitly confirms which rows to import (POST /api/import/confirm).
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Optional

from backend.app.core.money import normalize_rupees, to_paise

# ---------------------------------------------------------------------------
# Category inference (reuses same logic as transaction_extractor.py)
# ---------------------------------------------------------------------------

CATEGORY_KEYWORDS = {
    "Housing": ["rent", "maintenance", "landlord", "apartment", "mortgage", "housing"],
    "Food": ["food", "groceries", "grocery", "restaurant", "swiggy", "zomato",
             "dinner", "lunch", "breakfast", "snacks", "cafe", "coffee", "bakery"],
    "Transport": ["travel", "bus", "auto", "metro", "cab", "uber", "ola",
                  "petrol", "diesel", "fuel", "train", "flight", "taxi", "rapido"],
    "Utilities": ["electricity", "water", "wifi", "internet", "gas", "recharge",
                  "phone bill", "utility", "power bill", "broadband"],
    "Shopping": ["shopping", "clothes", "shirt", "shoes", "amazon", "flipkart",
                 "electronics", "gadget", "laptop", "mobile", "myntra"],
    "Entertainment": ["movie", "cinema", "netflix", "prime", "hotstar", "game",
                      "outing", "concert", "spotify"],
    "Healthcare": ["doctor", "medicine", "pharmacy", "hospital", "clinic",
                   "health", "dental", "apollo"],
    "Education": ["tuition", "books", "course", "fees", "school", "college", "exam"],
    "Salary": ["salary", "payroll", "wage", "stipend"],
}

INCOME_SIGNALS = {
    "salary", "bonus", "freelance", "dividend", "interest",
    "cashback", "refund", "credited", "received",
}


from collections import Counter
from backend.app.services.merchant_normalizer import normalize_narration
from backend.app.services.fingerprint import compute_transaction_fingerprint


def infer_category(description: str, tx_type: str) -> str:
    norm = normalize_narration(description, tx_type)
    return norm.category


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

VALID_TYPES = {"EXPENSE", "INCOME"}


def _validate_row(row: dict, idx: int) -> Optional[str]:
    """Return an error string, or None if the row is valid."""
    amount = row.get("amount")
    if amount is None:
        return f"Row {idx}: Amount is missing."
    try:
        amt = normalize_rupees(amount)
    except (TypeError, ValueError):
        return f"Row {idx}: Amount '{amount}' is not a valid number."
    if amt <= 0:
        return f"Row {idx}: Amount must be greater than zero (got {amount})."

    tx_type = str(row.get("type") or "").upper()
    if tx_type not in VALID_TYPES:
        return f"Row {idx}: type must be EXPENSE or INCOME (got '{tx_type}')."

    raw_date = row.get("date")
    if raw_date:
        try:
            datetime.strptime(str(raw_date), "%Y-%m-%d")
        except ValueError:
            return f"Row {idx}: date '{raw_date}' is not in YYYY-MM-DD format."

    return None


# ---------------------------------------------------------------------------
# Duplicate detection (batched Cypher query)
# ---------------------------------------------------------------------------

def detect_duplicates(rows: list[dict], user_id: str, db) -> list[dict]:
    """
    Check whether matching records already exist in Neo4j using a single
    batched Cypher query instead of N individual queries.

    Returns the rows list with added 'duplicate_status' and 'duplicate_matches'.
    This function NEVER writes to the database.
    """
    if not rows:
        return []

    # Use batch_check_duplicates if supported on db
    if hasattr(db, "batch_check_duplicates"):
        try:
            matches_by_row = db.batch_check_duplicates(user_id, rows)
            enriched = []
            for i, r in enumerate(rows):
                row = dict(r)
                matches = matches_by_row.get(i, [])
                if any(m.get("match_reason") in ("EXACT_FINGERPRINT", "EXACT_REF") for m in matches):
                    status = "CONFIRMED_DUPLICATE"
                elif matches:
                    status = "POSSIBLE_DUPLICATE"
                else:
                    status = "OK"
                row["duplicate_status"] = status
                row["duplicate_matches"] = matches
                enriched.append(row)
            return enriched
        except Exception:
            pass

    # Fallback to single-pass session check
    from neo4j.time import Date as Neo4jDate
    _EXACT_REF_QUERY = """
    MATCH (u:User {id: $user_id})-[:HAS_ACCOUNT]->(:Account)-[:MADE_TRANSACTION]->(t:Transaction)
    WHERE t.source_ref IS NOT NULL AND t.source_ref = $source_ref
    RETURN t.id AS id, t.description AS description, round(toFloat(t.amount_paise) / 100.0, 2) AS amount, t.date AS date
    LIMIT 1
    """
    _CANDIDATE_QUERY = """
    MATCH (u:User {id: $user_id})-[:HAS_ACCOUNT]->(:Account)-[:MADE_TRANSACTION]->(t:Transaction)
    WHERE t.amount_paise = $amount_paise
      AND t.type = $tx_type
      AND date(t.date) >= date($date_from)
      AND date(t.date) <= date($date_to)
    RETURN t.id AS id, t.description AS description, round(toFloat(t.amount_paise) / 100.0, 2) AS amount, t.date AS date
    LIMIT 3
    """

    enriched = []
    for row in rows:
        row = dict(row)
        source_ref = row.get("source_ref")
        tx_type = str(row.get("type", "EXPENSE")).upper()
        tx_date = row.get("date") or date.today().isoformat()
        try:
            amount = normalize_rupees(row.get("amount", 0))
        except Exception:
            amount = 0.0
        matches = []
        status = "OK"

        try:
            with db.driver.session(database=db.database) as session:
                if source_ref:
                    result = session.run(_EXACT_REF_QUERY, user_id=user_id, source_ref=source_ref)
                    rec = result.single()
                    if rec:
                        d = dict(rec)
                        if isinstance(d.get("date"), Neo4jDate):
                            d["date"] = d["date"].iso_format()
                        matches.append(d)
                        status = "CONFIRMED_DUPLICATE"

                if status == "OK":
                    dt = datetime.strptime(tx_date, "%Y-%m-%d").date()
                    date_from = (dt - timedelta(days=1)).isoformat()
                    date_to = (dt + timedelta(days=1)).isoformat()
                    amount_paise = to_paise(amount)
                    result = session.run(_CANDIDATE_QUERY, user_id=user_id, amount_paise=amount_paise, tx_type=tx_type, date_from=date_from, date_to=date_to)
                    for rec in result:
                        d = dict(rec)
                        if isinstance(d.get("date"), Neo4jDate):
                            d["date"] = d["date"].iso_format()
                        matches.append(d)
                    if matches:
                        status = "POSSIBLE_DUPLICATE"
        except Exception:
            status = "OK"

        row["duplicate_status"] = status
        row["duplicate_matches"] = matches
        enriched.append(row)

    return enriched


# ---------------------------------------------------------------------------
# Main pipeline entry point
# ---------------------------------------------------------------------------

def run_pipeline(
    raw_rows: list[dict],
    user_id: str,
    db,
    skip_dedup: bool = False,
    account_id: str = "A001",
) -> dict:
    """
    Normalize → Enrich (Merchant & Tiered Category) → Fingerprint → Validate → Detect Duplicates.

    Parameters
    ----------
    raw_rows    : list of dicts from csv_parser.parse_csv or image_extractor.extract_from_image
    user_id     : authenticated user's Neo4j id
    db          : Neo4jService instance
    skip_dedup  : set True in unit tests to avoid DB calls
    account_id  : account ID for deterministic fingerprint generation

    Returns
    -------
    dict with:
        valid_rows   : list[dict]  — pass these to the confirm endpoint
        invalid_rows : list[dict]  — {row, error}
        warnings     : list[str]
    """
    valid_rows: list[dict] = []
    invalid_rows: list[dict] = []
    warnings: list[str] = []

    # Track in-file occurrences so duplicate identical transactions (e.g. ₹20 chai twice)
    # produce unique deterministic fingerprints without colliding
    occurrence_counter: Counter = Counter()

    for i, raw in enumerate(raw_rows):
        row = dict(raw)
        tx_type = str(row.get("type") or "EXPENSE").upper().strip()
        if tx_type == "REFUND":
            tx_type = "INCOME"
        row["type"] = tx_type

        # Enrich description and category with Tiered Merchant Normalizer
        desc = row.get("description", "")
        norm = normalize_narration(desc, tx_type)
        row["clean_merchant"] = norm.clean_merchant
        row["channel"] = norm.channel
        if not row.get("category"):
            row["category"] = norm.category
        row["category_source"] = norm.category_source
        row["confidence"] = norm.confidence

        # Default date to today if missing
        if not row.get("date"):
            row["date"] = date.today().isoformat()

        # Validate
        error = _validate_row(row, i + 1)
        if error:
            invalid_rows.append({"row": row, "error": error})
        else:
            # Deterministic fingerprint with occurrence tracking
            amt = normalize_rupees(row.get("amount") or 0.0)
            amt_paise = to_paise(amt)
            tuple_key = (str(row.get("date")), amt_paise, tx_type, norm.clean_merchant.lower(), str(row.get("source_ref") or "").lower())
            occ = occurrence_counter[tuple_key]
            occurrence_counter[tuple_key] += 1
            row["amount"] = amt

            row["fingerprint"] = compute_transaction_fingerprint(
                account_id=account_id,
                date_str=str(row["date"]),
                amount=amt,
                tx_type=tx_type,
                description=norm.clean_merchant,
                source_ref=row.get("source_ref"),
                occurrence_index=occ,
            )
            valid_rows.append(row)

    # Deduplication (Single batch query)
    if not skip_dedup and valid_rows:
        try:
            valid_rows = detect_duplicates(valid_rows, user_id, db)
        except Exception as exc:
            warnings.append(f"Duplicate detection could not complete: {exc}. All rows marked OK.")
            for row in valid_rows:
                row.setdefault("duplicate_status", "OK")
                row.setdefault("duplicate_matches", [])
    else:
        for row in valid_rows:
            row.setdefault("duplicate_status", "OK")
            row.setdefault("duplicate_matches", [])

    accepted_rows = [r for r in valid_rows if r.get("duplicate_status") == "OK"]
    duplicate_rows = [
        r for r in valid_rows
        if r.get("duplicate_status") in ("CONFIRMED_DUPLICATE", "POSSIBLE_DUPLICATE")
    ]

    return {
        "valid_rows": valid_rows,
        "accepted_rows": accepted_rows,
        "duplicate_rows": duplicate_rows,
        "invalid_rows": invalid_rows,
        "warnings": warnings,
        "accepted_count": len(accepted_rows),
        "duplicate_count": len(duplicate_rows),
        "invalid_count": len(invalid_rows),
    }
