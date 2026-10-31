"""
Security audit tests for authentication, user data isolation, IDOR prevention,
upload validation, and credential redaction.
"""

from __future__ import annotations

import io
import logging
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.app.api.auth import create_session_token, SESSION_COOKIE_NAME
from backend.app.api.deps import get_current_user_id, get_neo4j_service, get_ingestion_service
from backend.app.core.logging_config import SensitiveDataFilter
from backend.app.database.neo4j_service import Neo4jService


client = TestClient(app)


# ===========================================================================
# 1. Authentication & Session Security Tests
# ===========================================================================

@pytest.mark.unit
class TestAuthenticationSecurity:
    def test_unauthenticated_requests_return_401(self):
        endpoints = [
            ("GET", "/api/finance/summary"),
            ("GET", "/api/finance/expenses"),
            ("GET", "/api/finance/savings"),
            ("GET", "/api/finance/debt"),
            ("GET", "/api/finance/health"),
            ("GET", "/api/transactions"),
            ("POST", "/api/transactions"),
            ("GET", "/api/goals"),
            ("POST", "/api/goals"),
            ("POST", "/api/assistant/query"),
            ("POST", "/api/import/confirm"),
        ]
        for method, endpoint in endpoints:
            if method == "GET":
                resp = client.get(endpoint)
            else:
                resp = client.post(endpoint, json={})
            assert resp.status_code == 401, f"{method} {endpoint} expected 401, got {resp.status_code}"
            assert "Authentication required" in resp.json().get("detail", "")

    def test_tampered_session_cookie_returns_401(self):
        valid_token = create_session_token("U_LEGIT")
        payload, sig = valid_token.split(".", 1)
        # Tamper payload
        tampered_token = f"eyJuZXdfc3ViIjoiVXRleHQifQ.{sig}"

        client.cookies.set(SESSION_COOKIE_NAME, tampered_token)
        resp = client.get("/api/finance/summary")
        assert resp.status_code == 401
        client.cookies.clear()

    def test_forged_signature_returns_401(self):
        valid_token = create_session_token("U_LEGIT")
        payload, _ = valid_token.split(".", 1)
        forged_token = f"{payload}.invalidsignature12345"

        client.cookies.set(SESSION_COOKIE_NAME, forged_token)
        resp = client.get("/api/transactions")
        assert resp.status_code == 401
        client.cookies.clear()


# ===========================================================================
# 2. Cross-User Data Isolation & IDOR Prevention Tests
# ===========================================================================

@pytest.mark.unit
class TestCrossUserDataIsolation:
    @pytest.fixture
    def isolated_db_mock(self):
        """
        Mock DB maintaining separate data for User A ('U_ALICE') and User B ('U_BOB').
        """
        db = MagicMock(spec=Neo4jService)

        alice_accounts = [{"id": "ACC_ALICE_1", "bank": "HDFC", "balance": 50000.0}]
        bob_accounts = [{"id": "ACC_BOB_1", "bank": "ICICI", "balance": 20000.0}]

        alice_txns = [
            {"id": "TX_ALICE_1", "description": "Alice Secret Spent", "amount": 1000.0, "type": "EXPENSE"}
        ]
        bob_txns = [
            {"id": "TX_BOB_1", "description": "Bob Lunch", "amount": 200.0, "type": "EXPENSE"}
        ]

        def get_user_accounts(user_id):
            if user_id == "U_ALICE":
                return alice_accounts
            if user_id == "U_BOB":
                return bob_accounts
            return []

        def get_all_transactions(user_id, limit=100):
            if user_id == "U_ALICE":
                return alice_txns
            if user_id == "U_BOB":
                return bob_txns
            return []

        def update_transaction(user_id, transaction_id, **kwargs):
            if user_id == "U_ALICE" and transaction_id == "TX_ALICE_1":
                return {"id": transaction_id, "amount": kwargs.get("amount", 1000.0)}
            if user_id == "U_BOB" and transaction_id == "TX_BOB_1":
                return {"id": transaction_id, "amount": kwargs.get("amount", 200.0)}
            raise ValueError(f"Transaction with id '{transaction_id}' not found")

        def delete_transaction(user_id, transaction_id):
            if user_id == "U_ALICE" and transaction_id == "TX_ALICE_1":
                return {"account_id": "ACC_ALICE_1", "restored_balance": 51000.0}
            if user_id == "U_BOB" and transaction_id == "TX_BOB_1":
                return {"account_id": "ACC_BOB_1", "restored_balance": 20200.0}
            raise ValueError(f"Transaction with id '{transaction_id}' not found")

        db.get_user_accounts.side_effect = get_user_accounts
        db.get_all_transactions.side_effect = get_all_transactions
        db.update_transaction.side_effect = update_transaction
        db.delete_transaction.side_effect = delete_transaction
        db.get_categories.return_value = ["General", "Food"]

        return db

    def test_bob_cannot_read_alice_transactions(self, isolated_db_mock):
        app.dependency_overrides[get_current_user_id] = lambda: "U_BOB"
        app.dependency_overrides[get_neo4j_service] = lambda: isolated_db_mock

        resp = client.get("/api/transactions")
        assert resp.status_code == 200
        data = resp.json()

        # Bob MUST only see Bob's transactions and accounts
        descriptions = [t["description"] for t in data["transactions"]]
        assert "Bob Lunch" in descriptions
        assert "Alice Secret Spent" not in descriptions
        assert data["accounts"][0]["id"] == "ACC_BOB_1"

        app.dependency_overrides.clear()

    def test_bob_cannot_modify_alice_transaction(self, isolated_db_mock):
        app.dependency_overrides[get_current_user_id] = lambda: "U_BOB"
        app.dependency_overrides[get_neo4j_service] = lambda: isolated_db_mock

        # Bob attempts to update Alice's transaction ID
        resp = client.put("/api/transactions/TX_ALICE_1", json={"amount": 9999.0})
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

        # Bob attempts to delete Alice's transaction ID
        del_resp = client.delete("/api/transactions/TX_ALICE_1")
        assert del_resp.status_code == 404

        app.dependency_overrides.clear()

    def test_bob_cannot_create_transaction_on_alice_account(self, isolated_db_mock):
        app.dependency_overrides[get_current_user_id] = lambda: "U_BOB"
        app.dependency_overrides[get_neo4j_service] = lambda: isolated_db_mock

        # Bob attempts to create a transaction specifying Alice's account
        resp = client.post("/api/transactions", json={
            "account_id": "ACC_ALICE_1",
            "amount": 500.0,
            "description": "Unauthorized spend on Alice's account",
            "transaction_type": "EXPENSE",
        })
        assert resp.status_code == 403
        assert "Access denied" in resp.json()["detail"]

        app.dependency_overrides.clear()

    def test_bob_cannot_import_into_alice_account(self, isolated_db_mock):
        app.dependency_overrides[get_current_user_id] = lambda: "U_BOB"
        app.dependency_overrides[get_neo4j_service] = lambda: isolated_db_mock

        # Bob attempts to confirm import targeting Alice's account
        resp = client.post("/api/import/confirm", json={
            "rows": [
                {
                    "account_id": "ACC_ALICE_1",
                    "date": "2026-03-01",
                    "amount": 2500.0,
                    "description": "Malicious import into Alice",
                    "type": "EXPENSE",
                }
            ]
        })
        assert resp.status_code == 403
        assert "Access denied" in resp.json()["detail"]

        app.dependency_overrides.clear()


# ===========================================================================
# 3. File Upload Security Validation Tests
# ===========================================================================

@pytest.mark.unit
class TestUploadSecurityValidation:
    def test_upload_binary_null_bytes_rejected(self):
        app.dependency_overrides[get_current_user_id] = lambda: "U_TEST"
        app.dependency_overrides[get_neo4j_service] = lambda: MagicMock()

        # Upload binary content disguised with .csv extension
        binary_payload = b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        files = {"file": ("malicious.csv", io.BytesIO(binary_payload), "text/csv")}

        resp = client.post("/api/import/csv", files=files)
        assert resp.status_code == 400
        assert "Binary file detected" in resp.json()["detail"]

        app.dependency_overrides.clear()

    def test_upload_empty_csv_rejected(self):
        app.dependency_overrides[get_current_user_id] = lambda: "U_TEST"
        app.dependency_overrides[get_neo4j_service] = lambda: MagicMock()

        files = {"file": ("empty.csv", io.BytesIO(b"   \n\n  "), "text/csv")}
        resp = client.post("/api/import/csv", files=files)
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

        app.dependency_overrides.clear()

    def test_upload_invalid_extension_rejected(self):
        app.dependency_overrides[get_current_user_id] = lambda: "U_TEST"
        app.dependency_overrides[get_neo4j_service] = lambda: MagicMock()

        files = {"file": ("exploit.exe", io.BytesIO(b"Date,Amount\n2026-01-01,100"), "text/plain")}
        resp = client.post("/api/import/csv", files=files)
        assert resp.status_code == 400
        assert "Only .csv / .tsv / .txt files are accepted" in resp.json()["detail"]

        app.dependency_overrides.clear()


# ===========================================================================
# 4. Sensitive Credential & Financial Log Redaction Tests
# ===========================================================================

@pytest.mark.unit
class TestSensitiveDataRedaction:
    def test_log_filter_redacts_credentials_and_tokens(self):
        filter_obj = SensitiveDataFilter()

        def make_record(msg, args=None):
            return logging.LogRecord(
                name="test_logger",
                level=logging.INFO,
                pathname=__file__,
                lineno=10,
                msg=msg,
                args=args,
                exc_info=None,
            )

        # 1. Password redaction
        rec1 = make_record('User login failed for password="SuperSecretPassword123!"')
        filter_obj.filter(rec1)
        assert "SuperSecretPassword123!" not in rec1.msg
        assert "[REDACTED_PASSWORD]" in rec1.msg

        # 2. Session cookie redaction
        rec2 = make_record("Received cookie finance_session=eyJzdWIiOiJVMDAxIn0.valid_signature_abc")
        filter_obj.filter(rec2)
        assert "eyJzdWIiOiJVMDAxIn0.valid_signature_abc" not in rec2.msg
        assert "finance_session=[REDACTED_SESSION]" in rec2.msg

        # 3. API key redaction
        rec3 = make_record("Connecting to LLM with provider key gsk_3k2j1h4g5f6e7d8c9b0a1z2y3x4w")
        filter_obj.filter(rec3)
        assert "gsk_3k2j1h4g5f6e7d8c9b0a1z2y3x4w" not in rec3.msg
        assert "[REDACTED_API_KEY]" in rec3.msg

        # 4. Bearer token redaction
        rec4 = make_record("Header Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz")
        filter_obj.filter(rec4)
        assert "Bearer [REDACTED_TOKEN]" in rec4.msg

        # 5. Credit card number redaction
        rec5 = make_record("Payment processed on card 4111 2222 3333 4444")
        filter_obj.filter(rec5)
        assert "4111 2222 3333 4444" not in rec5.msg
        assert "[REDACTED_CARD_NUMBER]" in rec5.msg


# ===========================================================================
# 5. Neo4jService Strict user_id Parameter Validation
# ===========================================================================

@pytest.mark.unit
class TestNeo4jServiceUserIdRequirements:
    def test_missing_or_empty_user_id_raises_value_error(self):
        service = Neo4jService(database="test-db", driver=MagicMock())

        invalid_ids = [None, "", 123, []]
        for bad_id in invalid_ids:
            with pytest.raises(ValueError, match="user_id must be a non-empty string"):
                service.get_financial_context(bad_id)

            with pytest.raises(ValueError, match="user_id must be a non-empty string"):
                service.get_all_transactions(bad_id)

            with pytest.raises(ValueError, match="user_id must be a non-empty string"):
                service.get_user_accounts(bad_id)

            with pytest.raises(ValueError, match="user_id must be a non-empty string"):
                service.add_transaction(bad_id, amount=100)

            with pytest.raises(ValueError, match="user_id must be a non-empty string"):
                service.add_income(bad_id, amount=100)

            with pytest.raises(ValueError, match="user_id must be a non-empty string"):
                service.batch_add_transactions(bad_id, rows=[])
