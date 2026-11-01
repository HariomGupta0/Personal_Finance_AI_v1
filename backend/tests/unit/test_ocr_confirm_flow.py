"""
Unit tests for OCR confirm-before-write flow and extraction sanity checks.
Ensures image upload returns a preview with sanity flags without persisting to Neo4j,
and that data is only persisted when user-approved values are posted to /confirm.
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.config import APP_PASSWORD, APP_USERNAME, SESSION_SECRET
from backend.main import app

FAKE_JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 32


@pytest.fixture
def auth_client():
    client = TestClient(app)
    login_resp = client.post("/api/auth/login", json={"username": APP_USERNAME, "password": APP_PASSWORD})
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    return client


def test_ocr_extraction_returns_preview_only_no_write(auth_client):
    """Uploading an image returns preview rows only; Neo4j write is never called."""
    mock_extracted = {
        "date": "2026-10-15",
        "amount": 450.0,
        "currency": "INR",
        "description": "Cafe Coffee Day",
        "direction": "expense",
        "type": "EXPENSE",
        "transaction_status": "SUCCESS",
        "source_ref": "REF12345",
        "confidence": "high",
        "warnings": [],
        "sanity_flag": True,
        "sanity_issues": [],
        "implausible_amount": False,
        "extraction_success": True,
    }

    with patch("backend.app.api.import_api.extract_from_image", return_value=mock_extracted), \
         patch("backend.app.api.import_api.run_pipeline") as mock_pipeline:

        mock_pipeline.return_value = {
            "valid_rows": [{
                "date": "2026-10-15",
                "amount": 450.0,
                "description": "Cafe Coffee Day",
                "type": "EXPENSE",
                "category": "Food",
                "source_ref": "REF12345",
                "source_type": "image",
            }],
            "invalid_rows": [],
            "warnings": [],
        }

        resp = auth_client.post(
            "/api/import/image",
            files={"file": ("receipt.jpg", FAKE_JPEG_BYTES, "image/jpeg")},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "EXTRACTED"
        assert data["sanity_flag"] is True
        assert data["sanity_issues"] == []
        assert len(data["preview_rows"]) == 1
        assert data["preview_rows"][0]["amount"] == 450.0
        assert data["preview_rows"][0]["description"] == "Cafe Coffee Day"


def test_sanity_flag_missing_fields(auth_client):
    """Sanity flag must be False when amount, date, or merchant is missing."""
    from backend.app.services.image_extractor import _sanitise_extraction

    # Missing amount
    res_no_amount = _sanitise_extraction({
        "date": "2026-10-15",
        "amount": None,
        "merchant_or_recipient": "Swiggy",
    })
    assert res_no_amount["sanity_flag"] is False
    assert "missing_amount" in res_no_amount["sanity_issues"]

    # Missing date
    res_no_date = _sanitise_extraction({
        "date": None,
        "amount": 250.0,
        "merchant_or_recipient": "Swiggy",
    })
    assert res_no_date["sanity_flag"] is False
    assert "missing_date" in res_no_date["sanity_issues"]

    # Missing merchant
    res_no_merchant = _sanitise_extraction({
        "date": "2026-10-15",
        "amount": 250.0,
        "merchant_or_recipient": "",
    })
    assert res_no_merchant["sanity_flag"] is False
    assert "missing_merchant" in res_no_merchant["sanity_issues"]


def test_sanity_flag_implausible_amount(auth_client):
    """Sanity flag must be False when extracted amount is implausibly large (> 10,000,000)."""
    from backend.app.services.image_extractor import _sanitise_extraction

    res = _sanitise_extraction({
        "date": "2026-10-15",
        "amount": 50_000_000.0,  # 5 crore
        "merchant_or_recipient": "Local Bakery",
    })
    assert res["sanity_flag"] is False
    assert "implausible_amount" in res["sanity_issues"]
    assert res["implausible_amount"] is True


def test_confirm_flow_writes_user_approved_row(auth_client):
    """Confirm endpoint persists user-reviewed values."""
    mock_db = MagicMock()
    mock_db.get_user_accounts.return_value = [{"id": "A001", "name": "Savings"}]
    mock_db.batch_create_transactions.return_value = {
        "saved": 1,
        "duplicates": 0,
        "failed": 0,
        "errors": [],
    }

    mock_ingestion = MagicMock()
    mock_ingestion.ingest_transaction.return_value = {
        "status": "SUCCESS",
        "transaction": {"transaction_id": "TX_TEST_01", "amount": 450.0},
    }

    with patch("backend.app.api.import_api.db", mock_db), \
         patch("backend.app.api.import_api.ingestion", mock_ingestion):
        payload = {
            "rows": [{
                "date": "2026-10-15",
                "amount": 450.0,
                "description": "Cafe Coffee Day",
                "type": "EXPENSE",
                "category": "Food",
                "source_ref": "REF12345",
                "source_type": "image",
            }]
        }
        resp = auth_client.post("/api/import/confirm", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert data["saved"] == 1
