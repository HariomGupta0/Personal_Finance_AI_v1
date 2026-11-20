"""
Comprehensive unit test suite for Phase 2.2:
- Structured Query Plan integration
- Merchant expenditure queries (exact matching, normalization, ambiguity, zero-spend vs no-match)
- Top-N transactions and amount filters (sorting, limits, bounds, transfer/refund exclusion)
- Deterministic arithmetic guarantees and grounded evidence generation
- User-data isolation
"""
from datetime import date
from unittest.mock import MagicMock, patch
import pytest

from backend.app.nlu.query_plan import ExpenditureQueryPlan, OperationType, DateRange, create_query_plan_from_parsed
from backend.app.nlu.question_parser import parse_question, parse_question_rules, extract_merchant, extract_top_n_and_thresholds
from backend.app.engine.financial_engine import calculate_merchant_expenses, calculate_top_transactions
from backend.app.database.neo4j_service import Neo4jService
from backend.app.rag.graph_rag import GraphRAG


# ==============================================================================
# 1. Merchant Matching & Normalization Unit Tests
# ==============================================================================

def test_exact_merchant_match_parsing():
    """Verify exact merchant recognition in varied natural query structures."""
    q1 = parse_question_rules("How much did I spend on Uber?")
    assert q1["intent"] == "MERCHANT_EXPENSE"
    assert q1["merchant"] == "Uber"

    q2 = parse_question_rules("Show my Netflix payments")
    assert q2["intent"] == "MERCHANT_EXPENSE"
    assert q2["merchant"] == "Netflix"

    q3 = parse_question_rules("Which transactions belong to Swiggy?")
    assert q3["intent"] == "MERCHANT_EXPENSE"
    assert q3["merchant"] == "Swiggy"

    q4 = parse_question_rules("How much did I spend on Amazon in September 2025?")
    assert q4["intent"] == "MERCHANT_EXPENSE"
    assert q4["merchant"] == "Amazon"
    assert q4["reporting_date"] == date(2025, 9, 1)


def test_merchant_case_and_whitespace_normalization():
    """Verify that case variations and irregular whitespaces normalize to canonical merchant name."""
    res1 = parse_question_rules("   how much did I spend on    uBeR?   ")
    assert res1["intent"] == "MERCHANT_EXPENSE"
    assert res1["merchant"] == "Uber"

    res2 = parse_question_rules("Show NETFLIX expenses")
    assert res2["intent"] == "MERCHANT_EXPENSE"
    assert res2["merchant"] == "Netflix"

    res3 = parse_question_rules("my payments to sWiGgY this month")
    assert res3["intent"] == "MERCHANT_EXPENSE"
    assert res3["merchant"] == "Swiggy"


def test_ambiguous_multiple_merchants_clarification():
    """Verify that queries mentioning multiple distinct merchants request user clarification."""
    res = parse_question_rules("Did I spend more on Uber or Swiggy?")
    assert res is not None
    assert res["intent"] == "MERCHANT_EXPENSE"
    assert res["needs_clarification"] is True
    assert res["clarification_type"] == "AMBIGUOUS_MERCHANT"
    assert "Multiple merchants detected" in res["clarification_message"]
    assert "Uber" in res["clarification_message"]
    assert "Swiggy" in res["clarification_message"]


def test_merchant_does_not_hijack_category_query():
    """Verify that standard category queries are preserved and never confused with merchant queries."""
    res_food = parse_question_rules("How much did I spend on food?")
    assert res_food["intent"] == "CATEGORY_EXPENSE"
    assert res_food["category"] == "Food"
    assert res_food.get("merchant") is None

    res_transport = parse_question_rules("How much did I spend on transport?")
    assert res_transport["intent"] == "CATEGORY_EXPENSE"
    assert res_transport["category"] == "Transport"
    assert res_transport.get("merchant") is None

    res_rent = parse_question_rules("How much did I spend on rent?")
    assert res_rent["intent"] == "CATEGORY_EXPENSE"
    assert res_rent["category"] == "Housing"
    assert res_rent.get("merchant") is None


# ==============================================================================
# 2. Top-N and Threshold Parsing Tests
# ==============================================================================

def test_top_n_transaction_parsing():
    """Verify extraction of limit and sort direction for top-N transaction queries."""
    res_5 = parse_question_rules("What are my five biggest expenses?")
    assert res_5["intent"] == "TOP_TRANSACTIONS"
    assert res_5["limit"] == 5
    assert res_5["sort_by"] == "amount"
    assert res_5["sort_direction"] == "DESC"

    res_3 = parse_question_rules("Show my 3 largest purchases in September 2025")
    assert res_3["intent"] == "TOP_TRANSACTIONS"
    assert res_3["limit"] == 3
    assert res_3["reporting_date"] == date(2025, 9, 1)

    res_default = parse_question_rules("Show my biggest expenses")
    assert res_default["intent"] == "TOP_TRANSACTIONS"
    assert res_default["limit"] == 5  # default limit applied


def test_amount_threshold_parsing():
    """Verify extraction of minimum, maximum, and bounded transaction thresholds."""
    res_min = parse_question_rules("List expenses above ₹5,000")
    assert res_min["intent"] == "TOP_TRANSACTIONS"
    assert res_min["amount_min"] == 5000.0
    assert res_min["amount_max"] is None

    res_max = parse_question_rules("Show transactions under ₹2,000")
    assert res_max["intent"] == "TOP_TRANSACTIONS"
    assert res_max["amount_max"] == 2000.0
    assert res_max["amount_min"] is None

    res_between = parse_question_rules("Show transactions between ₹1,000 and ₹3,000")
    assert res_between["intent"] == "TOP_TRANSACTIONS"
    assert res_between["amount_min"] == 1000.0
    assert res_between["amount_max"] == 3000.0


# ==============================================================================
# 3. Deterministic Engine Tests (Synthetic Fixtures)
# ==============================================================================

@pytest.fixture
def synthetic_merchant_context():
    return {
        "accounts": [{"id": "ACC1", "bank": "HDFC", "balance": 75000.0}],
        "transactions": [
            {"id": "TX_U1", "description": "Uber India trip", "merchant": "Uber", "amount": 450.0, "type": "EXPENSE", "date": "2026-09-05", "category": "Transport"},
            {"id": "TX_U2", "description": "Uber ride office", "merchant": "Uber", "amount": 350.0, "type": "EXPENSE", "date": "2026-09-12", "category": "Transport"},
            {"id": "TX_U3", "description": "Uber airport drop", "merchant": "Uber", "amount": 800.0, "type": "EXPENSE", "date": "2026-10-02", "category": "Transport"},
            {"id": "TX_SW1", "description": "Swiggy order lunch", "merchant": "Swiggy", "amount": 320.0, "type": "EXPENSE", "date": "2026-09-06", "category": "Food"},
            {"id": "TX_REFUND", "description": "Uber refund for cancelled trip", "merchant": "Uber", "amount": 250.0, "type": "INCOME", "date": "2026-09-10", "category": "Refund"},
            {"id": "TX_TRANSFER", "description": "Internal transfer to wallet", "merchant": "Uber", "amount": 1000.0, "type": "TRANSFER", "date": "2026-09-08", "category": "Transfer"},
        ],
        "historical_match_count": 3,
    }


def test_merchant_calculation_and_refund_exclusion(synthetic_merchant_context):
    """Verify calculation sums only genuine EXPENSE records, strictly ignoring refunds and transfers."""
    res_sep = calculate_merchant_expenses(
        synthetic_merchant_context,
        merchant_name="Uber",
        reporting_date=date(2026, 9, 1),
    )
    assert res_sep["merchant"] == "Uber"
    assert res_sep["is_found"] is True
    # In Sept: TX_U1 (450) + TX_U2 (350) = 800. (TX_REFUND and TX_TRANSFER are excluded)
    assert res_sep["total_spent"] == 800.0
    assert res_sep["transaction_count"] == 2
    assert res_sep["average_spend"] == 400.0
    assert len(res_sep["transactions"]) == 2
    assert res_sep["reporting_period"] == "2026-09"


def test_no_match_versus_confirmed_zero_spend(synthetic_merchant_context):
    """
    Verify clean architectural distinction between:
    - Confirmed Zero Spending: Merchant exists historically, but 0 spend in target period.
    - No Matching Merchant Found: Merchant never appears anywhere in the user's graph history.
    """
    # 1. Confirmed Zero Spending (Uber exists in Sept & Oct, but 0 spend in August 2026)
    res_zero_period = calculate_merchant_expenses(
        synthetic_merchant_context,
        merchant_name="Uber",
        reporting_date=date(2026, 8, 1),
    )
    assert res_zero_period["is_found"] is True
    assert res_zero_period["transaction_count"] == 0
    assert res_zero_period["total_spent"] == 0.0

    # 2. No Matching Merchant Found (Starbucks has 0 records in graph)
    zero_history_context = dict(synthetic_merchant_context)
    zero_history_context["historical_match_count"] = 0
    res_unknown_merchant = calculate_merchant_expenses(
        zero_history_context,
        merchant_name="Starbucks",
        reporting_date=date(2026, 9, 1),
    )
    assert res_unknown_merchant["is_found"] is False
    assert res_unknown_merchant["transaction_count"] == 0
    assert res_unknown_merchant["total_spent"] == 0.0


@pytest.fixture
def synthetic_top_transactions_context():
    return {
        "accounts": [{"id": "ACC1", "bank": "HDFC", "balance": 100000.0}],
        "transactions": [
            {"id": "T1", "description": "Rent", "amount": 25000.0, "type": "EXPENSE", "date": "2026-09-01", "category": "Housing"},
            {"id": "T2", "description": "Flight Ticket", "amount": 12500.0, "type": "EXPENSE", "date": "2026-09-15", "category": "Transport"},
            {"id": "T3", "description": "Electronics", "amount": 8500.0, "type": "EXPENSE", "date": "2026-09-18", "category": "Shopping"},
            {"id": "T4", "description": "Grocery Haul", "amount": 4500.0, "type": "EXPENSE", "date": "2026-09-10", "category": "Food"},
            {"id": "T5", "description": "Restaurant Dinner", "amount": 2800.0, "type": "EXPENSE", "date": "2026-09-20", "category": "Food"},
            {"id": "T6", "description": "Utility Bill", "amount": 1800.0, "type": "EXPENSE", "date": "2026-09-08", "category": "Utilities"},
            {"id": "T7", "description": "Taxi ride", "amount": 450.0, "type": "EXPENSE", "date": "2026-09-22", "category": "Transport"},
            {"id": "T8", "description": "Salary Credited", "amount": 80000.0, "type": "INCOME", "date": "2026-09-01", "category": "Salary"},
            {"id": "T9", "description": "Inter-account sweep", "amount": 15000.0, "type": "TRANSFER", "date": "2026-09-02", "category": "Transfer"},
        ],
    }


def test_top_transactions_descending_sorting_and_limits(synthetic_top_transactions_context):
    """Verify strict descending numeric order and exact top-N limits."""
    # Top 3
    top3 = calculate_top_transactions(synthetic_top_transactions_context, limit=3, reporting_date=date(2026, 9, 1))
    assert top3["count"] == 3
    assert top3["total_matching_count"] == 7  # 7 total expenses in Sept (excluding income & transfer)
    amounts = [t["amount"] for t in top3["transactions"]]
    assert amounts == [25000.0, 12500.0, 8500.0]
    assert top3["total_selected_amount"] == 46000.0

    # Top 5
    top5 = calculate_top_transactions(synthetic_top_transactions_context, limit=5, reporting_date=date(2026, 9, 1))
    assert top5["count"] == 5
    amounts5 = [t["amount"] for t in top5["transactions"]]
    assert amounts5 == [25000.0, 12500.0, 8500.0, 4500.0, 2800.0]


def test_top_transactions_amount_threshold_bounds(synthetic_top_transactions_context):
    """Verify minimum and maximum amount threshold boundaries."""
    # Expenses above ₹5,000
    above_5k = calculate_top_transactions(
        synthetic_top_transactions_context,
        limit=10,
        amount_min=5000.0,
        reporting_date=date(2026, 9, 1),
    )
    assert above_5k["count"] == 3
    for t in above_5k["transactions"]:
        assert t["amount"] >= 5000.0

    # Expenses between ₹1,000 and ₹5,000
    between = calculate_top_transactions(
        synthetic_top_transactions_context,
        limit=10,
        amount_min=1000.0,
        amount_max=5000.0,
        reporting_date=date(2026, 9, 1),
    )
    assert between["count"] == 3  # 4500, 2800, 1800
    for t in between["transactions"]:
        assert 1000.0 <= t["amount"] <= 5000.0


# ==============================================================================
# 4. GraphRAG Pipeline Integration & Evidence Tests
# ==============================================================================

def test_graph_rag_merchant_expense_pipeline():
    """Verify end-to-end GraphRAG pipeline execution for merchant queries."""
    mock_db = MagicMock(spec=Neo4jService)
    mock_db.retrieve_grounded_subgraph.return_value = {
        "user_id": "U001",
        "intent": "MERCHANT_EXPENSE",
        "grounded_entities": {
            "accounts": [{"id": "ACC1", "balance": 50000.0}],
            "transactions": [
                {"id": "TX_U1", "description": "Uber Ride", "merchant": "Uber", "amount": 400.0, "type": "EXPENSE", "date": "2026-10-05"},
                {"id": "TX_U2", "description": "Uber Ride 2", "merchant": "Uber", "amount": 600.0, "type": "EXPENSE", "date": "2026-10-12"},
            ],
            "historical_match_count": 2,
        },
        "source_identifiers": ["Transaction:TX_U1", "Transaction:TX_U2"],
        "graph_paths": [],
        "context": {
            "transactions": [
                {"id": "TX_U1", "description": "Uber Ride", "merchant": "Uber", "amount": 400.0, "type": "EXPENSE", "date": "2026-10-05"},
                {"id": "TX_U2", "description": "Uber Ride 2", "merchant": "Uber", "amount": 600.0, "type": "EXPENSE", "date": "2026-10-12"},
            ],
            "historical_match_count": 2,
        },
    }

    rag = GraphRAG(db=mock_db)
    with patch("backend.app.rag.graph_rag.ask_llm") as mock_llm:
        mock_llm.return_value = {"content": "You spent ₹1,000 on Uber.", "prompt_tokens": 10, "completion_tokens": 10, "tokens_used": 20}
        result = rag.process_query("How much did I spend on Uber?", user_id="U001")

    assert result["intent"] == "MERCHANT_EXPENSE"
    assert result["math_result"]["total_spent"] == 1000.0
    assert result["math_result"]["transaction_count"] == 2
    # Verify evidence items
    evidence = result["evidence"]
    assert any("Spend on Uber" in item["label"] or "Total Spent on Uber" in item["label"] for item in evidence)
    assert any("₹1,000" in item["value"] for item in evidence)


def test_graph_rag_top_transactions_pipeline():
    """Verify end-to-end GraphRAG pipeline execution for top-N queries."""
    mock_db = MagicMock(spec=Neo4jService)
    mock_db.retrieve_grounded_subgraph.return_value = {
        "user_id": "U001",
        "intent": "TOP_TRANSACTIONS",
        "grounded_entities": {
            "accounts": [{"id": "ACC1", "balance": 50000.0}],
            "transactions": [
                {"id": "TX_BIG1", "description": "Flight Ticket", "amount": 15000.0, "type": "EXPENSE", "date": "2026-10-02", "category": "Transport"},
                {"id": "TX_BIG2", "description": "Smartphone EMI", "amount": 8000.0, "type": "EXPENSE", "date": "2026-10-05", "category": "Shopping"},
            ],
        },
        "source_identifiers": ["Transaction:TX_BIG1", "Transaction:TX_BIG2"],
        "graph_paths": [],
        "context": {
            "transactions": [
                {"id": "TX_BIG1", "description": "Flight Ticket", "amount": 15000.0, "type": "EXPENSE", "date": "2026-10-02", "category": "Transport"},
                {"id": "TX_BIG2", "description": "Smartphone EMI", "amount": 8000.0, "type": "EXPENSE", "date": "2026-10-05", "category": "Shopping"},
            ],
        },
    }

    rag = GraphRAG(db=mock_db)
    with patch("backend.app.rag.graph_rag.ask_llm") as mock_llm:
        mock_llm.return_value = {"content": "Your top expenses are Flight Ticket and Smartphone EMI.", "prompt_tokens": 10, "completion_tokens": 10, "tokens_used": 20}
        result = rag.process_query("What are my 2 biggest expenses?", user_id="U001")

    assert result["intent"] == "TOP_TRANSACTIONS"
    assert result["math_result"]["count"] == 2
    assert result["math_result"]["total_selected_amount"] == 23000.0
    evidence = result["evidence"]
    assert any("#1 Flight Ticket" in item["label"] for item in evidence)
    assert any("₹15,000" in item["value"] for item in evidence)


def test_user_data_isolation():
    """Verify that user_id is enforced and empty/None IDs are rejected."""
    service = Neo4jService.__new__(Neo4jService)
    with pytest.raises(ValueError):
        service.retrieve_grounded_subgraph("", "MERCHANT_EXPENSE")
    with pytest.raises(ValueError):
        service.retrieve_grounded_subgraph(None, "TOP_TRANSACTIONS")
