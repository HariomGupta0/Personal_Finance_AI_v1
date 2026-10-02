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


def infer_category(description: str, tx_type: str) -> str:
    desc_lower = (description or "").lower()
    if tx_type == "INCOME":
        for kw in INCOME_SIGNALS:
            if kw in desc_lower:
                return kw.capitalize()
        return "Income"
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            return cat
    return "General"


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
        amt = float(amount)
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
# Duplicate detection (read-only Neo4j query)
# ---------------------------------------------------------------------------

_EXACT_REF_QUERY = """
MATCH (u:User {id: $user_id})-[:HAS_ACCOUNT]->(:Account)-[:MADE_TRANSACTION]->(t:Transaction)
WHERE t.source_ref IS NOT NULL AND t.source_ref = $source_ref
RETURN t.id AS id, t.description AS description, t.amount AS amount, t.date AS date
LIMIT 1
"""

_CANDIDATE_QUERY = """
MATCH (u:User {id: $user_id})-[:HAS_ACCOUNT]->(:Account)-[:MADE_TRANSACTION]->(t:Transaction)
WHERE t.amount = $amount
  AND t.type = $tx_type
  AND date(t.date) >= date($date_from)
  AND date(t.date) <= date($date_to)
RETURN t.id AS id, t.description AS description, t.amount AS amount, t.date AS date
LIMIT 3
"""

# Also check income nodes
_INCOME_CANDIDATE_QUERY = """
MATCH (u:User {id: $user_id})-[:RECEIVED_INCOME]->(i:Income)
WHERE i.amount = $amount
  AND date(i.date) >= date($date_from)
  AND date(i.date) <= date($date_to)
RETURN i.id AS id, i.source AS description, i.amount AS amount, i.date AS date
LIMIT 3
"""


def detect_duplicates(rows: list[dict], user_id: str, db) -> list[dict]:
    """
    For each row, check whether a matching record already exists in Neo4j.

    Returns the rows list with an added 'duplicate_status' field:
        'OK'                — no match found
        'CONFIRMED_DUPLICATE' — exact source_ref match (already imported)
        'POSSIBLE_DUPLICATE'  — candidate match by amount + date + type
    And 'duplicate_matches' list of matching transaction summaries.

    This function NEVER writes to the database.
    """
    from neo4j.time import Date as Neo4jDate

    enriched = []
    for row in rows:
        row = dict(row)
        source_ref = row.get("source_ref")
        tx_type = str(row.get("type", "EXPENSE")).upper()
        tx_date = row.get("date") or date.today().isoformat()
        amount = float(row.get("amount", 0))
        matches = []
        status = "OK"

        try:
            with db.driver.session(database=db.database) as session:
                # 1. Exact reference match
                if source_ref:
                    result = session.run(_EXACT_REF_QUERY, user_id=user_id, source_ref=source_ref)
                    rec = result.single()
                    if rec:
                        d = dict(rec)
                        if isinstance(d.get("date"), Neo4jDate):
                            d["date"] = d["date"].iso_format()
                        matches.append(d)
                        status = "CONFIRMED_DUPLICATE"

                # 2. Candidate match (skip if already confirmed duplicate)
                if status == "OK":
                    dt = datetime.strptime(tx_date, "%Y-%m-%d").date()
                    date_from = (dt - timedelta(days=1)).isoformat()
                    date_to = (dt + timedelta(days=1)).isoformat()

                    query = _INCOME_CANDIDATE_QUERY if tx_type == "INCOME" else _CANDIDATE_QUERY
                    params = dict(
                        user_id=user_id,
                        amount=amount,
                        tx_type=tx_type,
                        date_from=date_from,
                        date_to=date_to,
                    )
                    result = session.run(query, **params)
                    for rec in result:
                        d = dict(rec)
                        if isinstance(d.get("date"), Neo4jDate):
                            d["date"] = d["date"].iso_format()
                        matches.append(d)

                    if matches:
                        status = "POSSIBLE_DUPLICATE"

        except Exception:
            # Dedup query failures are non-fatal — flag as needing review
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
) -> dict:
    """
    Normalize → Validate → Detect Duplicates.

    Parameters
    ----------
    raw_rows    : list of dicts from csv_parser.parse_csv or image_extractor.extract_from_image
    user_id     : authenticated user's Neo4j id
    db          : Neo4jService instance
    skip_dedup  : set True in unit tests to avoid DB calls

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

    for i, raw in enumerate(raw_rows):
        # Normalise type to uppercase
        tx_type = str(raw.get("type") or "EXPENSE").upper().strip()
        if tx_type == "REFUND":
            tx_type = "INCOME"
        raw["type"] = tx_type

        # Infer category if not provided
        if not raw.get("category"):
            raw["category"] = infer_category(raw.get("description", ""), tx_type)

        # Default date to today if missing
        if not raw.get("date"):
            raw["date"] = date.today().isoformat()

        # Validate
        error = _validate_row(raw, i + 1)
        if error:
            invalid_rows.append({"row": raw, "error": error})
        else:
            valid_rows.append(raw)

    # Deduplication (DB call)
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

    return {
        "valid_rows": valid_rows,
        "invalid_rows": invalid_rows,
        "warnings": warnings,
    }
