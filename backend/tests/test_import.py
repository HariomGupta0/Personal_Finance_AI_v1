"""
Tests for the CSV/image import feature.

Tests are split into:
  - Unit tests (no DB, no LLM):  test_csv_*, test_image_*, test_pipeline_*
  - Integration tests (require live DB): marked with [LIVE-DB] in the name
  - API integration tests: test_api_*  (require running FastAPI + session)

Run unit tests only:
    python -m pytest backend/tests/test_import.py -k "not live_db and not api" -v

Run all tests (requires configured .env):
    python -m pytest backend/tests/test_import.py -v
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TEST_DATA_DIR = Path(__file__).parent / "test-data"

# ===========================================================================
# CSV Parser Tests
# ===========================================================================

from backend.app.services.csv_parser import (
    CSVParseError,
    _parse_amount,
    _parse_date,
    detect_columns,
    parse_csv,
)
import pandas as pd


class TestParseDate:
    def test_iso_format(self):
        assert _parse_date("2026-09-15") == "2026-09-15"

    def test_dmy_dash(self):
        assert _parse_date("15-09-2026") == "2026-09-15"

    def test_dmy_slash(self):
        assert _parse_date("15/09/2026") == "2026-09-15"

    def test_dmy_dot(self):
        assert _parse_date("15.09.2026") == "2026-09-15"

    def test_month_name_short(self):
        assert _parse_date("15 Sep 2026") == "2026-09-15"

    def test_month_name_with_dash(self):
        assert _parse_date("15-Sep-2026") == "2026-09-15"

    def test_blank_returns_none(self):
        assert _parse_date("") is None

    def test_gibberish_returns_none(self):
        assert _parse_date("NOT_A_DATE") is None

    def test_yyyymmdd_slash(self):
        assert _parse_date("2026/09/15") == "2026-09-15"


class TestParseAmount:
    def test_plain_float(self):
        assert _parse_amount("1500.50") == 1500.50

    def test_with_rupee_symbol(self):
        assert _parse_amount("₹1,500.00") == 1500.00

    def test_with_commas(self):
        assert _parse_amount("1,00,000") == 100000.0

    def test_negative(self):
        assert _parse_amount("-2500.00") == -2500.00

    def test_parenthesised_negative(self):
        assert _parse_amount("(1234.56)") == -1234.56

    def test_blank_returns_none(self):
        assert _parse_amount("") is None

    def test_none_input(self):
        assert _parse_amount(None) is None

    def test_dash_returns_none(self):
        assert _parse_amount("-") is None

    def test_nil_returns_none(self):
        assert _parse_amount("nil") is None

    def test_na_returns_none(self):
        assert _parse_amount("N/A") is None


class TestDetectColumns:
    def _make_df(self, cols):
        return pd.DataFrame(columns=cols)

    def test_debit_credit_mode(self):
        df = self._make_df(["Date", "Description", "Debit", "Credit", "Balance"])
        result = detect_columns(df)
        assert result.mapping["amount_mode"] == "debit_credit"
        assert result.mapping["debit"] == "Debit"
        assert result.mapping["credit"] == "Credit"
        # Balance must not be used
        assert result.mapping.get("amount_col") is None

    def test_signed_amount_mode(self):
        df = self._make_df(["Date", "Narration", "Amount", "Ref No"])
        result = detect_columns(df)
        assert result.mapping["amount_mode"] == "signed"
        assert result.mapping["amount_col"] == "Amount"

    def test_balance_col_ignored(self):
        df = self._make_df(["Date", "Description", "Amount", "Closing Balance"])
        result = detect_columns(df)
        assert "Balance" not in str(result.mapping.get("amount_col", ""))

    def test_missing_amount_raises(self):
        df = self._make_df(["Date", "Description"])
        with pytest.raises(CSVParseError):
            detect_columns(df)

    def test_withdrawal_deposit_mapped(self):
        df = self._make_df(["Transaction Date", "Narration", "Withdrawal Amount", "Deposit Amount", "Closing Balance"])
        result = detect_columns(df)
        assert result.mapping["amount_mode"] == "debit_credit"


class TestParseCsv:
    def _read(self, filename):
        return (TEST_DATA_DIR / filename).read_bytes()

    def test_synthetic_bank_parses_correctly(self):
        content = self._read("synthetic_bank.csv")
        result = parse_csv(content)
        assert len(result["errors"]) == 0, f"Unexpected errors: {result['errors']}"
        assert len(result["rows"]) == 10
        # First row is income (Credit column)
        income_rows = [r for r in result["rows"] if r["type"] == "INCOME"]
        expense_rows = [r for r in result["rows"] if r["type"] == "EXPENSE"]
        assert len(income_rows) == 2  # Salary + Freelance
        assert len(expense_rows) == 8

    def test_synthetic_narration_parses_correctly(self):
        content = self._read("synthetic_narration.csv")
        result = parse_csv(content)
        assert len(result["errors"]) == 0
        assert len(result["rows"]) == 10
        income_rows = [r for r in result["rows"] if r["type"] == "INCOME"]
        assert len(income_rows) == 2  # Salary + Freelance

    def test_edge_cases_handles_missing_amount(self):
        content = self._read("synthetic_edge_cases.csv")
        result = parse_csv(content)
        # Missing amount row (REF004) should be in errors
        error_refs = [e.get("raw", {}).get("Ref No") for e in result["errors"]]
        assert "REF004" in error_refs, f"Expected REF004 in errors, got: {error_refs}"

    def test_edge_cases_handles_invalid_amount(self):
        content = self._read("synthetic_edge_cases.csv")
        result = parse_csv(content)
        error_refs = [e.get("raw", {}).get("Ref No") for e in result["errors"]]
        assert "REF005" in error_refs

    def test_edge_cases_zero_amount_rejected(self):
        content = self._read("synthetic_edge_cases.csv")
        result = parse_csv(content)
        # Zero amount (REF009) must not appear in valid rows
        valid_refs = [r.get("source_ref") for r in result["rows"]]
        assert "REF009" not in valid_refs

    def test_edge_cases_refund_as_income(self):
        content = self._read("synthetic_edge_cases.csv")
        result = parse_csv(content)
        refund_rows = [r for r in result["rows"] if r.get("source_ref") == "REF003"]
        assert len(refund_rows) == 1
        assert refund_rows[0]["type"] == "INCOME"

    def test_description_with_commas_and_quotes(self):
        content = self._read("synthetic_edge_cases.csv")
        result = parse_csv(content)
        quoted_rows = [r for r in result["rows"] if "quoted text" in (r.get("description") or "").lower()]
        assert len(quoted_rows) == 1

    def test_source_ref_extracted(self):
        content = self._read("synthetic_bank.csv")
        result = parse_csv(content)
        refs = [r["source_ref"] for r in result["rows"]]
        assert "SAL2026090001" in refs

    def test_empty_file_raises(self):
        with pytest.raises(CSVParseError):
            parse_csv(b"")

    def test_non_csv_raises(self):
        with pytest.raises(CSVParseError):
            parse_csv(b'{"key": "this is json not csv"}')

    def test_balance_column_not_used_as_amount(self):
        """No row should have amount equal to the closing balance values."""
        content = self._read("synthetic_bank.csv")
        result = parse_csv(content)
        amounts = {r["amount"] for r in result["rows"]}
        # 105000 is a balance value, not a transaction
        assert 105000.0 not in amounts


# ===========================================================================
# Image Extractor Tests (mocked Groq)
# ===========================================================================

from backend.app.services.image_extractor import (
    _detect_mime,
    _sanitise_extraction,
    extract_from_image,
)

FAKE_JPEG_HEADER = b"\xff\xd8\xff\xe0" + b"\x00" * 100
FAKE_PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


class TestDetectMime:
    def test_jpeg(self):
        assert _detect_mime(FAKE_JPEG_HEADER) == "image/jpeg"

    def test_png(self):
        assert _detect_mime(FAKE_PNG_HEADER) == "image/png"

    def test_unsupported_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            _detect_mime(b"NOTANIMAGE00000")


class TestSanitiseExtraction:
    def test_valid_extraction(self):
        raw = {
            "date": "2026-09-15",
            "amount": 1500.0,
            "currency": "INR",
            "merchant_or_recipient": "BigBazaar",
            "direction": "expense",
            "transaction_status": "SUCCESS",
            "reference_id": "UPI123",
            "confidence": "high",
            "warnings": [],
        }
        result = _sanitise_extraction(raw)
        assert result["amount"] == 1500.0
        assert result["type"] == "EXPENSE"
        assert result["source_ref"] == "UPI123"
        assert result["date"] == "2026-09-15"

    def test_zero_amount_nulled(self):
        raw = {"amount": 0, "direction": "expense", "transaction_status": "SUCCESS",
               "confidence": "high", "warnings": []}
        result = _sanitise_extraction(raw)
        assert result["amount"] is None
        assert any("zero" in w.lower() or "null" in w.lower() for w in result["warnings"])

    def test_unknown_status_generates_warning(self):
        raw = {"amount": 500, "direction": "expense", "transaction_status": "PENDING",
               "confidence": "high", "warnings": []}
        result = _sanitise_extraction(raw)
        assert any("PENDING" in w for w in result["warnings"])

    def test_refund_maps_to_income(self):
        raw = {"amount": 999, "direction": "refund", "transaction_status": "SUCCESS",
               "confidence": "high", "warnings": []}
        result = _sanitise_extraction(raw)
        assert result["type"] == "INCOME"

    def test_unknown_direction_type_is_none(self):
        raw = {"amount": 500, "direction": "unknown", "transaction_status": "SUCCESS",
               "confidence": "medium", "warnings": []}
        result = _sanitise_extraction(raw)
        assert result["type"] is None

    def test_low_confidence_generates_warning(self):
        raw = {"amount": 500, "direction": "expense", "transaction_status": "SUCCESS",
               "confidence": "low", "warnings": []}
        result = _sanitise_extraction(raw)
        assert any("low" in w.lower() for w in result["warnings"])

    def test_bad_date_nulled(self):
        raw = {"date": "15 Sep 2026", "amount": 500, "direction": "expense",
               "transaction_status": "SUCCESS", "confidence": "high", "warnings": []}
        result = _sanitise_extraction(raw)
        assert result["date"] is None
        assert any("date" in w.lower() for w in result["warnings"])


class TestExtractFromImage:
    """Unit tests that mock the Groq vision API."""

    def test_success_response_parsed(self):
        mock_response_json = """{
            "date": "2026-09-15",
            "amount": 350.00,
            "currency": "INR",
            "merchant_or_recipient": "Uber Technologies",
            "direction": "expense",
            "transaction_status": "SUCCESS",
            "reference_id": "UPI20260912A",
            "source_type": "image",
            "confidence": "high",
            "warnings": []
        }"""

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=mock_response_json))]
        )

        with patch("backend.app.services.image_extractor.Groq", return_value=mock_client):
            result = extract_from_image(FAKE_JPEG_HEADER)

        assert result["extraction_success"] is True
        assert result["amount"] == 350.0
        assert result["type"] == "EXPENSE"
        assert result["source_ref"] == "UPI20260912A"

    def test_api_failure_returns_fallback(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API timeout")

        with patch("backend.app.services.image_extractor.Groq", return_value=mock_client):
            result = extract_from_image(FAKE_JPEG_HEADER)

        assert result["extraction_success"] is False
        assert result["amount"] is None
        assert any("failed" in w.lower() or "API" in w for w in result["warnings"])

    def test_malformed_json_returns_fallback(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="This is not JSON at all!"))]
        )

        with patch("backend.app.services.image_extractor.Groq", return_value=mock_client):
            result = extract_from_image(FAKE_JPEG_HEADER)

        assert result["extraction_success"] is False

    def test_unsupported_format_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            extract_from_image(b"NOTANIMAGE00000")


# ===========================================================================
# Import Pipeline Tests
# ===========================================================================

from backend.app.services.import_pipeline import (
    infer_category,
    run_pipeline,
)


class TestInferCategory:
    def test_rent_maps_to_housing(self):
        assert infer_category("Monthly Rent Payment", "EXPENSE") == "Housing"

    def test_grocery_maps_to_food(self):
        assert infer_category("BigBazaar Grocery Shopping", "EXPENSE") == "Food"

    def test_salary_income_maps_correctly(self):
        cat = infer_category("Salary September 2026", "INCOME")
        assert cat in ("Salary", "Income")

    def test_unknown_maps_to_general(self):
        assert infer_category("Random Transaction XYZ", "EXPENSE") == "General"


class TestRunPipeline:
    def test_valid_rows_pass(self):
        rows = [
            {"date": "2026-09-01", "amount": 60000, "description": "Salary", "type": "INCOME"},
            {"date": "2026-09-05", "amount": 1500, "description": "Rent", "type": "EXPENSE"},
        ]
        result = run_pipeline(rows, user_id="U001", db=None, skip_dedup=True)
        assert len(result["valid_rows"]) == 2
        assert len(result["invalid_rows"]) == 0

    def test_missing_amount_rejected(self):
        rows = [{"date": "2026-09-01", "amount": None, "description": "Missing", "type": "EXPENSE"}]
        result = run_pipeline(rows, user_id="U001", db=None, skip_dedup=True)
        assert len(result["invalid_rows"]) == 1
        assert len(result["valid_rows"]) == 0

    def test_zero_amount_rejected(self):
        rows = [{"date": "2026-09-01", "amount": 0, "description": "Zero", "type": "EXPENSE"}]
        result = run_pipeline(rows, user_id="U001", db=None, skip_dedup=True)
        assert len(result["invalid_rows"]) == 1

    def test_invalid_type_rejected(self):
        rows = [{"date": "2026-09-01", "amount": 500, "description": "Bad", "type": "TRANSFER"}]
        result = run_pipeline(rows, user_id="U001", db=None, skip_dedup=True)
        assert len(result["invalid_rows"]) == 1

    def test_refund_type_converted_to_income(self):
        rows = [{"date": "2026-09-01", "amount": 999, "description": "Amazon Refund", "type": "REFUND"}]
        result = run_pipeline(rows, user_id="U001", db=None, skip_dedup=True)
        assert len(result["valid_rows"]) == 1
        assert result["valid_rows"][0]["type"] == "INCOME"

    def test_category_inferred_if_missing(self):
        rows = [{"date": "2026-09-01", "amount": 500, "description": "Swiggy Dinner", "type": "EXPENSE"}]
        result = run_pipeline(rows, user_id="U001", db=None, skip_dedup=True)
        assert result["valid_rows"][0]["category"] == "Food"

    def test_date_defaults_to_today_if_missing(self):
        from datetime import date
        rows = [{"amount": 500, "description": "Test", "type": "EXPENSE"}]
        result = run_pipeline(rows, user_id="U001", db=None, skip_dedup=True)
        assert result["valid_rows"][0]["date"] == date.today().isoformat()

    def test_duplicate_detection_mocked(self):
        """Verify that duplicate_status field is set on each valid row."""
        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_db.driver.session.return_value.__enter__ = lambda s: mock_session
        mock_db.driver.session.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.run.return_value.single.return_value = None
        mock_session.run.return_value.__iter__ = iter([])

        rows = [{"date": "2026-09-01", "amount": 1500, "description": "Test", "type": "EXPENSE",
                 "source_ref": "REF_UNIQUE_001"}]
        result = run_pipeline(rows, user_id="U001", db=mock_db, skip_dedup=False)
        assert result["valid_rows"][0]["duplicate_status"] in ("OK", "POSSIBLE_DUPLICATE", "CONFIRMED_DUPLICATE")


# ===========================================================================
# API Integration Tests (require configured FastAPI + session)
# [LIVE-DB] means requires running Neo4j
# ===========================================================================

class TestImportAPIUnit:
    """Tests using FastAPI TestClient with mocked services — no DB required."""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        from fastapi.testclient import TestClient
        from backend.config import APP_PASSWORD, APP_USERNAME, SESSION_SECRET

        if not APP_PASSWORD or not SESSION_SECRET:
            pytest.skip("[LIVE-DB] APP_PASSWORD / SESSION_SECRET not configured")

        # Patch Neo4j so these tests don't need a live DB
        with patch("backend.app.api.import_api.db") as mock_db, \
             patch("backend.app.api.import_api.ingestion") as mock_ingestion:

            mock_db.driver.session.return_value.__enter__ = lambda s: MagicMock(
                run=MagicMock(return_value=MagicMock(single=MagicMock(return_value=None), __iter__=iter([])))
            )
            mock_db.driver.session.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.database = "finance-ai-antigravity"

            mock_ingestion.ingest_transaction.return_value = {
                "status": "SUCCESS",
                "transaction": {"transaction_id": "T_TEST001", "amount": 1500.0},
                "before_metrics": None,
                "after_metrics": {"savings_rate": 50.0, "monthly_expenses": 21000,
                                  "recommended_emergency_fund": 63000, "emergency_fund_shortfall": 0},
                "impact_summary": "Test"
            }

            from backend.main import app
            self.client = TestClient(app)

            # Login
            login = self.client.post("/api/auth/login",
                                     json={"username": APP_USERNAME, "password": APP_PASSWORD})
            if login.status_code != 200:
                pytest.skip("[LIVE-DB] Login failed — check credentials and Neo4j")

            yield

    def test_csv_upload_valid_file(self):
        csv_content = (TEST_DATA_DIR / "synthetic_bank.csv").read_bytes()
        resp = self.client.post(
            "/api/import/csv",
            files={"file": ("synthetic_bank.csv", csv_content, "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "PARSED"
        assert data["stats"]["valid"] > 0

    def test_csv_upload_rejects_oversized_content(self):
        oversized = b"Date,Description,Amount,Transaction Type\n"
        oversized += b"2026-09-01,Test,100,DR\n" * 300000  # ~17MB
        resp = self.client.post(
            "/api/import/csv",
            files={"file": ("big.csv", oversized, "text/csv")},
        )
        assert resp.status_code == 413

    def test_csv_upload_rejects_non_csv_extension(self):
        resp = self.client.post(
            "/api/import/csv",
            files={"file": ("statement.pdf", b"fake pdf content", "application/pdf")},
        )
        assert resp.status_code == 400

    def test_image_upload_rejects_unsupported_format(self):
        resp = self.client.post(
            "/api/import/image",
            files={"file": ("doc.pdf", b"NOT_AN_IMAGE", "application/pdf")},
        )
        assert resp.status_code == 400

    def test_confirm_requires_auth(self):
        """Without a session cookie the confirm endpoint should return 401."""
        from fastapi.testclient import TestClient
        from backend.main import app
        anon_client = TestClient(app)
        resp = anon_client.post("/api/import/confirm", json={
            "rows": [{"date": "2026-09-01", "description": "Test",
                      "amount": 100, "type": "EXPENSE"}]
        })
        assert resp.status_code == 401

    def test_confirm_saves_expense(self):
        resp = self.client.post("/api/import/confirm", json={
            "rows": [{"date": "2026-09-01", "description": "Test Expense",
                      "amount": 1500.0, "type": "EXPENSE"}]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["saved"] == 1
        assert data["status"] == "SUCCESS"

    def test_confirm_rejects_zero_amount(self):
        resp = self.client.post("/api/import/confirm", json={
            "rows": [{"date": "2026-09-01", "description": "Zero",
                      "amount": 0, "type": "EXPENSE"}]
        })
        assert resp.status_code == 422  # Pydantic validation error

    def test_confirm_rejects_invalid_type(self):
        resp = self.client.post("/api/import/confirm", json={
            "rows": [{"date": "2026-09-01", "description": "Bad Type",
                      "amount": 500, "type": "TRANSFER"}]
        })
        assert resp.status_code == 422


if __name__ == "__main__":
    # Run unit tests only (no DB, no LLM)
    import subprocess
    subprocess.run([
        sys.executable, "-m", "pytest",
        str(__file__),
        "-k", "not live_db",
        "-v", "--tb=short"
    ])
