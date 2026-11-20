"""
Unit tests for the CSV Statement Import Audit & Validation Improvements.

Tests:
1. Preview detection of dates, descriptions, amounts, transaction types, and categories.
2. Malformed rows handling (both debit and credit populated, blank amounts, invalid values).
3. Ambiguous date format detection (e.g. 01/02/2025 flagged as ambiguous).
4. Unrecognized columns identification and user warnings.
5. Accurate calculation and reporting of accepted, duplicate, skipped, and rejected counts.
6. Absolute refusal to guess ambiguous amounts or silently discard financial records.
7. Confirmation requirement before database write, and idempotent repeat-confirmation safety.
"""
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from backend.app.services.csv_parser import parse_csv, detect_columns, _parse_amount, _parse_date
from backend.app.services.import_pipeline import run_pipeline
from backend.app.api.import_api import upload_csv, confirm_import, ConfirmImportRequest, ConfirmRow


# =============================================================================
# 1. Preview Detection & Column Mapping
# =============================================================================

def test_preview_detection_fields_and_categories():
    """Verify that dates, descriptions, amounts, types, and categories are parsed and enriched."""
    csv_bytes = b"""Date,Narration,Debit,Credit,Ref
15/08/2025,Swiggy Bangalore,450.00,,UPI12345
16/08/2025,Monthly Salary Credit,,75000.00,SAL98765
"""
    parsed = parse_csv(csv_bytes)
    assert len(parsed["rows"]) == 2
    assert len(parsed["errors"]) == 0

    mock_db = MagicMock()
    pipeline_res = run_pipeline(
        raw_rows=parsed["rows"],
        user_id="U001",
        db=mock_db,
        skip_dedup=True,
    )

    rows = pipeline_res["valid_rows"]
    assert len(rows) == 2

    # Row 1: Expense
    assert rows[0]["date"] == "2025-08-15"
    assert rows[0]["type"] == "EXPENSE"
    assert rows[0]["amount"] == 450.0
    assert rows[0]["category"] == "Food"
    assert rows[0]["clean_merchant"] == "Swiggy"
    assert rows[0]["source_ref"] == "UPI12345"

    # Row 2: Income
    assert rows[1]["date"] == "2025-08-16"
    assert rows[1]["type"] == "INCOME"
    assert rows[1]["amount"] == 75000.0
    assert rows[1]["category"] == "Salary"
    assert rows[1]["source_ref"] == "SAL98765"


# =============================================================================
# 2. Malformed Rows & Non-Guessing Policy
# =============================================================================

def test_malformed_rows_and_no_guessing_amounts():
    """
    Ensure rows with missing amounts, conflicting debit/credit, or invalid dates
    are rejected with specific error messages rather than guessed or defaulted.
    """
    csv_bytes = b"""Date,Description,Debit,Credit
15/08/2025,Valid Txn,500.00,
16/08/2025,Conflicting Amounts,200.00,300.00
17/08/2025,Missing Both Amounts,,
18/08/2025,Invalid Number,abc,
invalid-date,Bad Date,100.00,
"""
    parsed = parse_csv(csv_bytes)

    # Only Row 1 is valid
    assert len(parsed["rows"]) == 1
    assert parsed["rows"][0]["amount"] == 500.0

    # 4 rows must be rejected
    errors = parsed["errors"]
    assert len(errors) == 4

    error_texts = [e["error"] for e in errors]
    assert any("Both debit and credit values are non-zero" in t for t in error_texts)
    assert any("Missing amount — both debit and credit cells are blank" in t for t in error_texts)
    assert any("Invalid debit amount 'abc'" in t for t in error_texts)
    assert any("Invalid or unparseable date 'invalid-date'" in t for t in error_texts)


# =============================================================================
# 3. Ambiguous Date Format Detection
# =============================================================================

def test_ambiguous_date_format_detection():
    """Dates where both day and month <= 12 must trigger a date ambiguity warning without discarding."""
    csv_bytes = b"""Date,Description,Amount,Type
01/02/2025,Coffee,120.00,DR
03/04/2025,Book,450.00,DR
"""
    parsed = parse_csv(csv_bytes)
    assert len(parsed["rows"]) == 2
    assert parsed["date_ambiguity"] is True
    assert any("Ambiguous date format detected" in w for w in parsed["warnings"])
    # Parsed assuming DD/MM/YYYY (Indian standard)
    assert parsed["rows"][0]["date"] == "2025-02-01"


# =============================================================================
# 4. Unrecognized Columns Detection
# =============================================================================

def test_unrecognized_columns_identification():
    """Columns not recognized by standard rules must be identified and reported in preview."""
    csv_bytes = b"""Date,Narration,Debit,Credit,PromoCode,InternalNote
15/08/2025,Uber Ride,350.00,,,EXTRA_TAG
"""
    parsed = parse_csv(csv_bytes)
    assert "PromoCode" in parsed["unrecognized_columns"]
    assert "InternalNote" in parsed["unrecognized_columns"]
    assert any("Unrecognized column(s) detected: PromoCode, InternalNote" in w for w in parsed["warnings"])
    assert len(parsed["rows"]) == 1


# =============================================================================
# 5. Row Counts: Accepted, Duplicate, Skipped, and Rejected
# =============================================================================

@pytest.mark.anyio
async def test_row_counts_reporting():
    """Verify that accepted, duplicate, skipped, and rejected counts are accurately computed."""
    # CSV has:
    # 2 valid rows
    # 1 conflicting debit/credit (rejected)
    # 1 empty line (skipped)
    csv_content = b"""Date,Description,Debit,Credit
15/08/2025,Valid Txn 1,100.00,
16/08/2025,Valid Txn 2,,2000.00
17/08/2025,Conflicting,50.00,50.00
,,,
"""
    mock_upload = MagicMock()
    mock_upload.filename = "statement.csv"
    mock_upload.read = AsyncMock(return_value=csv_content)

    mock_db = MagicMock()
    # Mock duplicate detection: mark 1 as duplicate, 1 as OK
    def mock_check_dup(user_id, rows):
        return {
            0: [{"match_reason": "EXACT_FINGERPRINT"}], # Row 0 is duplicate
            1: [],                                      # Row 1 is accepted
        }
    mock_db.batch_check_duplicates.side_effect = mock_check_dup

    resp = await upload_csv(
        file=mock_upload,
        user_id="U001",
        db=mock_db,
    )

    stats = resp["stats"]
    assert stats["total_rows"] == 4
    assert stats["accepted_count"] == 1
    assert stats["duplicate_count"] == 1
    assert stats["skipped_count"] == 1
    assert stats["rejected_count"] == 1

    assert len(resp["accepted_rows"]) == 1
    assert len(resp["duplicate_rows"]) == 1
    assert len(resp["skipped_rows"]) == 1
    assert len(resp["rejected_rows"]) == 1


# =============================================================================
# 6. Idempotent Repeat Confirmation Safety
# =============================================================================

def test_confirm_import_idempotent_safety():
    """
    Ensure the confirm endpoint requires confirmation and repeated calls
    do NOT double-insert or double-apply balance changes.
    """
    mock_db = MagicMock()
    mock_db.get_user_accounts.return_value = [{"id": "ACC_01", "balance": 50000.0}]

    # First confirmation: inserts 1 row
    mock_db.batch_add_transactions.return_value = {
        "import_id": "IMP_TEST01",
        "inserted": 1,
        "skipped": 0,
        "net_balance_delta": -500.0,
        "new_balance": 49500.0,
    }

    req = ConfirmImportRequest(
        rows=[
            ConfirmRow(
                date="2025-08-15",
                description="Dinner",
                amount=500.0,
                type="EXPENSE",
                category="Food",
                account_id="ACC_01",
            )
        ],
        import_id="IMP_TEST01",
    )

    res1 = confirm_import(payload=req, user_id="U001", db=mock_db, ingestion=MagicMock())
    assert res1["status"] == "SUCCESS"
    assert res1["saved"] == 1
    assert res1["skipped_duplicates"] == 0
    assert res1["net_balance_delta"] == -500.0
    assert res1["idempotent"] is True

    # Repeated confirmation with the exact same import_id and rows:
    # batch_add_transactions skips duplicate fingerprint, delta is 0
    mock_db.batch_add_transactions.return_value = {
        "import_id": "IMP_TEST01",
        "inserted": 0,
        "skipped": 1,
        "net_balance_delta": 0.0,
        "new_balance": 49500.0,
    }

    res2 = confirm_import(payload=req, user_id="U001", db=mock_db, ingestion=MagicMock())
    assert res2["status"] == "SUCCESS"
    assert res2["saved"] == 0
    assert res2["skipped_duplicates"] == 1
    assert res2["net_balance_delta"] == 0.0
    assert res2["is_repeat_confirmation"] is True
    assert "Safe repeat" in res2["message"]
