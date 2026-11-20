"""
Unit tests verifying FastAPI routers with dependency injection (Audit Gap C4).

Demonstrates that endpoints can be tested in CI without a running Neo4j instance
by using FastAPI's app.dependency_overrides.
"""
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.app.api.deps import get_current_user_id, get_neo4j_service
from backend.tests.unit.test_financial_engine import MOCK_CONTEXT

client = TestClient(app)


@pytest.fixture(autouse=True)
def override_dependencies():
    mock_db = MagicMock()
    mock_db.get_financial_context.return_value = MOCK_CONTEXT
    mock_db.get_savings_context.return_value = MOCK_CONTEXT
    mock_db.get_all_transactions.return_value = MOCK_CONTEXT["transactions"]
    mock_db.get_categories.return_value = ["Housing", "Food", "Transport", "Utilities"]
    mock_db.get_user_accounts.return_value = MOCK_CONTEXT["accounts"]

    app.dependency_overrides[get_current_user_id] = lambda: "U001"
    app.dependency_overrides[get_neo4j_service] = lambda: mock_db

    yield mock_db

    app.dependency_overrides.clear()


def test_api_summary_with_mock_db(override_dependencies):
    resp = client.get("/api/finance/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "savings_rate" in data
    assert data["savings_rate"] > 0
    override_dependencies.get_financial_context.assert_called_with("U001")



def test_api_expenses_with_mock_db(override_dependencies):
    resp = client.get("/api/finance/expenses")
    assert resp.status_code == 200
    data = resp.json()
    assert "categories" in data or "total_expenses" in data


def test_api_transactions_list_with_mock_db(override_dependencies):
    resp = client.get("/api/transactions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["transactions"]) == 4
    assert len(data["categories"]) == 4
    override_dependencies.get_all_transactions.assert_called_with("U001", limit=100)


def test_api_goals_list_with_mock_db(override_dependencies):
    resp = client.get("/api/goals")
    assert resp.status_code == 200
    data = resp.json()
    assert "goals" in data
    assert len(data["goals"]) == len(MOCK_CONTEXT.get("goals", []))


def test_api_goal_create_and_delete(override_dependencies):
    from backend.app.api.deps import get_ingestion_service
    mock_ingestion = MagicMock()
    mock_ingestion.ingest_goal.return_value = {
        "status": "SUCCESS",
        "goal": {"name": "Vacation Fund", "target_amount": 50000.0, "current_amount": 10000.0},
    }
    mock_ingestion.remove_goal.return_value = {"status": "SUCCESS", "deleted": True}
    app.dependency_overrides[get_ingestion_service] = lambda: mock_ingestion

    post_resp = client.post("/api/goals", json={
        "name": "Vacation Fund",
        "target_amount": 50000.0,
        "current_amount": 10000.0,
    })
    assert post_resp.status_code == 200
    assert post_resp.json()["status"] == "SUCCESS"

    del_resp = client.delete("/api/goals/Vacation Fund")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True
