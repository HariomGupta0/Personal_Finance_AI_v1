"""
Unit tests for graph schema consistency checker (T7).
Verifies:
1. Consistency check on healthy/seeded graph returns 0 inconsistencies.
2. Inconsistency detection logic (property vs edge conflict, currency mismatch, duplicate income).
"""

from unittest.mock import MagicMock
import pytest

from scripts.check_graph_consistency import check_graph_consistency, format_report


def test_consistency_on_mock_healthy_graph():
    mock_service = MagicMock()
    mock_session = MagicMock()
    mock_service.driver.session.return_value.__enter__.return_value = mock_session
    mock_service.database = "finance-ai-antigravity"

    # 1. tx categories: 1 tx with edge, no prop
    mock_session.run.side_effect = [
        # query_tx_categories
        [{"tx_id": "T001", "description": "Rent", "category_prop": None, "category_edge_name": "Housing", "category_edge_id": "C001"}],
        # query_incomes
        [{"income_id": "I001", "source": "Salary", "amount": 50000.0, "amount_paise": 5000000, "date": "2026-10-01", "user_id": "U001"}],
        # query_income_txs
        [],
        # query_accounts
        [{"account_id": "A001", "bank": "Test Bank", "balance": 50000.0, "balance_paise": 5000000, "user_id": "U001", "net_tx_paise": 0, "tx_count": 0}],
        # query_loans
        [],
        # query_goals
        [],
        # orphan queries (4x)
        MagicMock(single=MagicMock(return_value={"c": 0})),
        MagicMock(single=MagicMock(return_value={"c": 0})),
        MagicMock(single=MagicMock(return_value={"c": 0})),
        MagicMock(single=MagicMock(return_value={"c": 0})),
    ]

    report = check_graph_consistency(mock_service)
    assert report["summary"]["status"] == "HEALTHY"
    assert report["inconsistencies_found"] == 0
    assert report["warnings_found"] == 0

    text = format_report(report)
    assert "Status: HEALTHY" in text


def test_consistency_detects_category_conflict():
    mock_service = MagicMock()
    mock_session = MagicMock()
    mock_service.driver.session.return_value.__enter__.return_value = mock_session
    mock_service.database = "finance-ai-antigravity"

    mock_session.run.side_effect = [
        # Conflict: property says 'Food', but edge says 'Housing'
        [{"tx_id": "T001", "description": "Rent", "category_prop": "Food", "category_edge_name": "Housing", "category_edge_id": "C001"}],
        [],
        [],
        [{"account_id": "A001", "bank": "Test Bank", "balance": 1000.0, "balance_paise": 100000, "user_id": "U001", "net_tx_paise": 0, "tx_count": 0}],
        [],
        [],
        MagicMock(single=MagicMock(return_value={"c": 0})),
        MagicMock(single=MagicMock(return_value={"c": 0})),
        MagicMock(single=MagicMock(return_value={"c": 0})),
        MagicMock(single=MagicMock(return_value={"c": 0})),
    ]

    report = check_graph_consistency(mock_service)
    assert report["summary"]["status"] == "INCONSISTENT"
    assert report["inconsistencies_found"] == 1
    assert report["category_checks"]["issues"][0]["type"] == "CONFLICT"


def test_consistency_detects_currency_mismatch():
    mock_service = MagicMock()
    mock_session = MagicMock()
    mock_service.driver.session.return_value.__enter__.return_value = mock_session
    mock_service.database = "finance-ai-antigravity"

    mock_session.run.side_effect = [
        [],
        [],
        [],
        # balance 500.0 (50000 paise) != balance_paise 40000
        [{"account_id": "A001", "bank": "Test Bank", "balance": 500.0, "balance_paise": 40000, "user_id": "U001", "net_tx_paise": 0, "tx_count": 0}],
        [],
        [],
        MagicMock(single=MagicMock(return_value={"c": 0})),
        MagicMock(single=MagicMock(return_value={"c": 0})),
        MagicMock(single=MagicMock(return_value={"c": 0})),
        MagicMock(single=MagicMock(return_value={"c": 0})),
    ]

    report = check_graph_consistency(mock_service)
    assert report["summary"]["status"] == "INCONSISTENT"
    assert report["inconsistencies_found"] == 1
    assert any(i["type"] == "CURRENCY_SYNC_MISMATCH" for i in report["balance_checks"]["issues"])
