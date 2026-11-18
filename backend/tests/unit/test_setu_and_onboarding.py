"""
Unit and integration tests for:
1. 60-Second Onboarding Wizard API (/api/onboarding/bootstrap)
2. Setu Account Aggregator Integration (/api/import/aa/*)
3. PDF Bank Statement Parser
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from backend.main import app
from backend.app.api.deps import get_current_user_id, get_neo4j_service
from backend.app.services.setu_client import setu_client, BANK_METADATA
from backend.app.services.pdf_parser import (
    convert_pdf_text_to_csv,
    PDFPasswordRequiredError,
    PDFIncorrectPasswordError,
)

client = TestClient(app)

MOCK_USER_ID = "usr_test_onboarding_456"


@pytest.fixture
def mock_dependencies():
    mock_db = MagicMock()
    mock_db.database = "neo4j"
    mock_db.driver.session.return_value.__enter__.return_value.run.return_value = None

    # Mock user financials bootstrap
    mock_db.bootstrap_user_financials.return_value = {
        "status": "BOOTSTRAPPED",
        "user_id": MOCK_USER_ID,
        "account_id": "ACC_HDFC_MOCK",
        "liquid_balance_paise": 15000000,
        "monthly_income_paise": 7500000,
        "monthly_emi_paise": 1500000,
        "loan_type": "Personal Loan",
        "runway_months": 2.5,
        "dti_ratio": 20.0,
        "health_score": 78,
    }

    mock_db.get_user_accounts.return_value = [{"id": "ACC_HDFC_MOCK", "name": "HDFC Bank", "balance": 150000.0}]
    mock_db.batch_check_duplicates.return_value = {}

    mock_db.batch_add_transactions.return_value = {
        "import_id": "IMP_TEST123",
        "total": 42,
        "inserted": 42,
        "skipped": 0,
        "net_balance_delta": 45000.0,
        "new_balance": 195000.0,
    }

    app.dependency_overrides[get_current_user_id] = lambda: MOCK_USER_ID
    app.dependency_overrides[get_neo4j_service] = lambda: mock_db

    yield mock_db

    app.dependency_overrides.clear()


def test_setu_client_discover_accounts():
    res = setu_client.discover_accounts(phone="9876543210", fip_id="HDFC")
    accounts = res["accounts"]
    assert len(accounts) >= 1
    assert accounts[0]["fip_id"] == "HDFC-FIP"
    assert "account_id" in accounts[0]
    assert "masked_number" in accounts[0]


def test_setu_client_consent_request():
    consent = setu_client.create_consent_request(
        phone="9876543210",
        fip_id="HDFC",
        account_ids=["ACC_HDFC_4102"],
    )
    assert consent["status"] == "PENDING"
    assert "consent_id" in consent
    assert consent["demo_otp_hint"] == "123456"


def test_setu_client_fetch_statement_rows():
    rows = setu_client.fetch_statement_rows(
        phone="9876543210",
        otp="123456",
        account_id="ACC_HDFC_4102",
        fip_id="HDFC",
    )
    if isinstance(rows, tuple):
        rows = rows[0]
    assert len(rows) > 0
    first = rows[0]
    assert "date" in first
    assert "amount" in first
    assert "type" in first


def test_onboarding_bootstrap_api(mock_dependencies):
    payload = {
        "bank_name": "HDFC Bank",
        "liquid_balance": 150000.0,
        "monthly_income": 75000.0,
        "monthly_emi": 15000.0,
        "loan_type": "Personal Loan",
    }
    resp = client.post("/api/onboarding/bootstrap", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["user_id"] == MOCK_USER_ID
    assert "deterministic_metrics" in data
    assert data["deterministic_metrics"]["emergency_runway_months"] == 4.0
    assert data["deterministic_metrics"]["debt_to_income_ratio"] == 20.0
    assert data["deterministic_metrics"]["financial_health_score"] >= 50.0


def test_aa_banks_list_api(mock_dependencies):
    resp = client.get("/api/import/aa/banks")
    assert resp.status_code == 200
    banks = resp.json()["banks"]
    assert len(banks) >= 4
    fip_ids = [b["id"] for b in banks]
    assert "HDFC" in fip_ids
    assert "SBI" in fip_ids


def test_aa_sync_api_success(mock_dependencies):
    payload = {
        "phone": "9876543210",
        "otp": "123456",
        "account_id": "ACC_HDFC_4102",
        "fip_id": "HDFC",
        "consent_id": "CONSENT_TEST",
    }
    resp = client.post("/api/import/aa/sync", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["synced_transactions"] == 42
    assert data["accounts_linked"] == 1


def test_aa_sync_api_invalid_otp(mock_dependencies):
    payload = {
        "phone": "9876543210",
        "otp": "000000",  # invalid sandbox OTP
        "account_id": "ACC_HDFC_4102",
        "fip_id": "HDFC",
    }
    resp = client.post("/api/import/aa/sync", json=payload)
    # Circuit breaker / setu client rejects invalid OTP with 502 or 400
    assert resp.status_code in [400, 502]


def test_pdf_text_to_csv_conversion():
    sample_text = """
    HDFC BANK STATEMENT
    Date Narration Chq/Ref No Value Dt Withdrawal Amt Deposit Amt Closing Balance
    01/03/2026 SALARY CREDIT REF100 01/03/2026 85,000.00 1,20,000.00
    04/03/2026 SWIGGY BANGALORE REF101 04/03/2026 450.00 1,19,550.00
    08/03/2026 ELECTRICITY BESCOM REF102 08/03/2026 2,100.00 1,17,450.00
    """
    csv_str = convert_pdf_text_to_csv(sample_text)
    assert "Date,Description,Debit,Credit,Balance" in csv_str
    assert "SALARY CREDIT" in csv_str
    assert "SWIGGY BANGALORE" in csv_str
    assert "450.00" in csv_str
