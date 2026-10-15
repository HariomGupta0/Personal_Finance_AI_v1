"""
Unit tests for backend/app/services/csv_parser.py

Tests bank statement parsing across Indian/international formats:
- Debit / Credit two-column format (HDFC, SBI, ICICI style)
- Single amount + Type column format (UPI, netbanking)
- Signed amount format
- Date formats (DD/MM/YYYY, YYYY-MM-DD, DD-Mon-YYYY)
- Dirty amounts (₹, $, commas, whitespace)
- Balance column exclusion (never treating Closing Balance as transaction amount)
- Edge cases and error handling (empty file, JSON/HTML injection, unparseable rows)
"""
import pytest
from backend.app.services.csv_parser import parse_csv, CSVParseError, _parse_date, _parse_amount


class TestDateParsing:
    def test_iso_date(self):
        assert _parse_date("2026-10-15") == "2026-10-15"

    def test_indian_dmy_slashes(self):
        assert _parse_date("15/10/2026") == "2026-10-15"

    def test_indian_dmy_hyphens(self):
        assert _parse_date("15-10-2026") == "2026-10-15"

    def test_month_abbreviation(self):
        assert _parse_date("15-Oct-2026") == "2026-10-15"

    def test_invalid_date_returns_none(self):
        assert _parse_date("not-a-date") is None
        assert _parse_date("") is None


class TestAmountParsing:
    def test_clean_number(self):
        assert _parse_amount("1500.50") == 1500.50

    def test_amount_with_rupee_and_commas(self):
        assert _parse_amount("₹1,25,000.00") == 125000.0

    def test_amount_with_dollar(self):
        assert _parse_amount("$450.00") == 450.0

    def test_parenthesised_negative(self):
        assert _parse_amount("(2500)") == -2500.0

    def test_blank_and_na_cells_return_none(self):
        assert _parse_amount("") is None
        assert _parse_amount("—") is None
        assert _parse_amount("N/A") is None
        assert _parse_amount(None) is None


class TestDualColumnDebitCreditCSV:
    def test_debit_credit_format(self):
        csv_data = b"""Date,Narration,Debit,Credit,Balance
15/10/2026,Swiggy Food,450.00,,45000.00
16/10/2026,Monthly Salary,,60000.00,105000.00
"""
        res = parse_csv(csv_data)
        assert len(res["rows"]) == 2
        assert len(res["errors"]) == 0

        # Row 1: Swiggy Expense
        row1 = res["rows"][0]
        assert row1["type"] == "EXPENSE"
        assert row1["amount"] == 450.0
        assert row1["date"] == "2026-10-15"
        assert "Swiggy" in row1["description"]

        # Row 2: Salary Income
        row2 = res["rows"][1]
        assert row2["type"] == "INCOME"
        assert row2["amount"] == 60000.0
        assert row2["date"] == "2026-10-16"

        # Verify Balance column was ignored as amount
        assert any("Balance" in w for w in res["warnings"])

    def test_both_debit_and_credit_flagged_as_error(self):
        csv_data = b"""Date,Description,Debit,Credit
15/10/2026,Ambiguous Tx,500.00,1000.00
"""
        res = parse_csv(csv_data)
        assert len(res["rows"]) == 0
        assert len(res["errors"]) == 1
        assert "Both debit and credit" in res["errors"][0]["error"]


class TestSingleAmountAndTypeCSV:
    def test_amount_and_type_columns(self):
        csv_data = b"""Transaction Date,Details,Amount,Type
2026-09-01,Groceries,1200.00,DR
2026-09-02,Client Payment,15000.00,CR
"""
        res = parse_csv(csv_data)
        assert len(res["rows"]) == 2
        assert res["rows"][0]["type"] == "EXPENSE"
        assert res["rows"][0]["amount"] == 1200.0
        assert res["rows"][1]["type"] == "INCOME"
        assert res["rows"][1]["amount"] == 15000.0


class TestSignedAmountCSV:
    def test_signed_amounts(self):
        csv_data = b"""Date,Particulars,Amount
2026-09-10,Amazon Shopping,-3500.00
2026-09-11,Freelance Income,20000.00
"""
        res = parse_csv(csv_data)
        assert len(res["rows"]) == 2
        assert res["rows"][0]["type"] == "EXPENSE"
        assert res["rows"][0]["amount"] == 3500.0
        assert res["rows"][1]["type"] == "INCOME"
        assert res["rows"][1]["amount"] == 20000.0


class TestInvalidFilesAndEdgeCases:
    def test_empty_csv_raises_error(self):
        with pytest.raises(CSVParseError):
            parse_csv(b"")

    def test_html_content_rejected(self):
        with pytest.raises(CSVParseError) as exc_info:
            parse_csv(b"<!DOCTYPE html><html><body>Error</body></html>")
        assert "HTML" in str(exc_info.value)

    def test_json_content_rejected(self):
        with pytest.raises(CSVParseError) as exc_info:
            parse_csv(b'{"transactions": []}')
        assert "JSON" in str(exc_info.value)

    def test_missing_amount_columns_raises_error(self):
        with pytest.raises(CSVParseError):
            parse_csv(b"Date,Description,Category\n2026-10-01,Test,Food\n")
