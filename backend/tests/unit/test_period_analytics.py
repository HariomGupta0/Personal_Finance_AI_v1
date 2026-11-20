"""
Unit and Integration Test Suite for Phase 2.3:
Period Comparison, Category-Wise Variance Attribution, and Multi-Month Spending Trends.

Tests:
1. Parsing of comparison periods (explicit months, years, relative terms, ISO formats).
2. Query plan preservation of both comparison date ranges, category, and merchant filters.
3. Deterministic calculation of Period A vs Period B totals and absolute/percentage change.
4. Zero-baseline safe handling (percentage change unavailable when baseline is zero).
5. Category-wise variance attribution, ranking, and supporting transactions.
6. Multi-month spending trends chronological ordering and coverage differentiation.
7. Distinguishing missing months (DATA_UNAVAILABLE) from confirmed zero spend (CONFIRMED_ZERO).
8. Strict exclusion of internal transfers and refund reversals across both periods.
9. Inclusive date boundary adherence.
10. Cross-user data isolation.
11. End-to-end GraphRAG period analytics pipeline.
"""
from datetime import date
from unittest.mock import MagicMock, patch
import pytest

from backend.app.nlu.question_parser import parse_question, parse_question_rules
from backend.app.nlu.query_plan import OperationType
from backend.app.engine.financial_engine import (
    calculate_period_comparison,
    calculate_spending_trends,
)
from backend.app.rag.graph_rag import GraphRAG
from backend.app.database.neo4j_service import Neo4jService


# ==============================================================================
# Part B: Parsing & Query Plan Preservation of Both Comparison Periods
# ==============================================================================

def test_parse_explicit_month_comparison():
    """
    Question: 'Did I spend more in September than October?'
    Validates:
    - Operation resolved as PERIOD_COMPARISON
    - Both periods parsed without dropping October
    - date_range = September (baseline), comparison_date_range = October
    """
    res = parse_question("Did I spend more in September than October?")
    assert res["intent"] == "PERIOD_COMPARISON"
    assert res.get("query_plan") is not None
    plan = res["query_plan"]
    assert plan.operation == OperationType.PERIOD_COMPARISON

    # Verify both periods preserved
    assert plan.date_range.start_date.month == 9
    assert plan.date_range.start_date.day == 1
    assert plan.date_range.end_date.month == 9
    assert plan.date_range.end_date.day == 30

    assert plan.comparison_date_range is not None
    assert plan.comparison_date_range.start_date.month == 10
    assert plan.comparison_date_range.start_date.day == 1
    assert plan.comparison_date_range.end_date.month == 10
    assert plan.comparison_date_range.end_date.day == 31


def test_parse_explicit_year_and_iso_comparison():
    """
    Tests explicit year pairs ('August and September 2026') and ISO format ('2026-08 and 2026-09').
    """
    res1 = parse_question("Compare my expenses in August and September 2026.")
    assert res1["intent"] == "PERIOD_COMPARISON"
    plan1 = res1["query_plan"]
    assert plan1.date_range.start_date == date(2026, 8, 1)
    assert plan1.date_range.end_date == date(2026, 8, 31)
    assert plan1.comparison_date_range.start_date == date(2026, 9, 1)
    assert plan1.comparison_date_range.end_date == date(2026, 9, 30)

    res2 = parse_question("Compare 2026-08 vs 2026-09")
    assert res2["intent"] == "PERIOD_COMPARISON"
    plan2 = res2["query_plan"]
    assert plan2.date_range.start_date == date(2026, 8, 1)
    assert plan2.comparison_date_range.start_date == date(2026, 9, 1)


def test_parse_relative_comparison_with_category():
    """
    Question: 'How much more did I spend on Food this month compared with last month?'
    Validates:
    - Operation is PERIOD_COMPARISON
    - Category 'Food' is preserved
    - Both 'last month' (baseline) and 'this month' (comparison) are resolved
    """
    res = parse_question("How much more did I spend on Food this month compared with last month?")
    assert res["intent"] == "PERIOD_COMPARISON"
    assert res["category"] == "Food"
    plan = res["query_plan"]
    assert plan.category == "Food"
    assert plan.date_range.start_date is not None
    assert plan.comparison_date_range is not None


def test_parse_period_comparison_with_merchant():
    """
    Question: 'Did I spend more on Uber in September or October?'
    Validates:
    - Operation is PERIOD_COMPARISON
    - Merchant 'Uber' is preserved across both periods
    - Category is not hijacked
    """
    res = parse_question("Did I spend more on Uber in September or October?")
    assert res["intent"] == "PERIOD_COMPARISON"
    assert res["merchant"] == "Uber"
    assert res["category"] is None
    plan = res["query_plan"]
    assert plan.merchant == "Uber"
    assert plan.date_range.start_date.month == 9
    assert plan.comparison_date_range.start_date.month == 10


def test_period_comparison_ambiguity_and_clarification():
    """
    Validates clarification triggers when:
    1. Only 1 period is mentioned in comparative query ('Did I spend more in September?')
    2. A period is compared against itself ('Compare September 2026 with September 2026')
    """
    # Case 1: Incomplete comparison
    res1 = parse_question("Did I spend more in September?")
    assert res1["needs_clarification"] is True
    assert res1["clarification_type"] == "AMBIGUOUS_PERIOD"
    assert "compare" in res1["clarification_message"].lower()

    # Case 2: Identical periods
    res2 = parse_question("Compare September 2026 with September 2026")
    assert res2["needs_clarification"] is True
    assert res2["clarification_type"] == "AMBIGUOUS_PERIOD"
    assert "distinct" in res2["clarification_message"].lower()


# ==============================================================================
# Part B: Deterministic Mathematical Calculation & Baselines
# ==============================================================================

def test_period_comparison_positive_and_negative_change():
    """
    Tests deterministic calculation of Period A vs Period B:
    1. Positive change (+₹15,000, +50.0%)
    2. Negative change (-₹15,000, -30.0%)
    """
    # Scenario 1: Spending increased
    context_increase = {
        "transactions": [
            # September (Period A): ₹30,000
            {"id": "T1", "amount": 20000.0, "type": "EXPENSE", "category": "Food", "date": "2026-09-10"},
            {"id": "T2", "amount": 10000.0, "type": "EXPENSE", "category": "Travel", "date": "2026-09-20"},
            # October (Period B): ₹45,000
            {"id": "T3", "amount": 25000.0, "type": "EXPENSE", "category": "Food", "date": "2026-10-05"},
            {"id": "T4", "amount": 20000.0, "type": "EXPENSE", "category": "Travel", "date": "2026-10-15"},
        ]
    }

    res_inc = calculate_period_comparison(
        context_increase,
        period_a_start=date(2026, 9, 1),
        period_a_end=date(2026, 9, 30),
        period_b_start=date(2026, 10, 1),
        period_b_end=date(2026, 10, 31),
    )
    assert res_inc["period_a"]["total_spent"] == 30000.0
    assert res_inc["period_b"]["total_spent"] == 45000.0
    assert res_inc["absolute_change"] == 15000.0
    assert res_inc["percentage_change"] == 50.0
    assert res_inc["percentage_change_status"] == "VALID"
    assert res_inc["higher_period"] == "October 2026"
    assert "increased" in res_inc["comparison_verdict"]

    # Scenario 2: Spending decreased
    context_decrease = {
        "transactions": [
            # August (Period A): ₹50,000
            {"id": "T1", "amount": 50000.0, "type": "EXPENSE", "category": "Shopping", "date": "2026-08-15"},
            # September (Period B): ₹35,000
            {"id": "T2", "amount": 35000.0, "type": "EXPENSE", "category": "Shopping", "date": "2026-09-15"},
        ]
    }
    res_dec = calculate_period_comparison(
        context_decrease,
        period_a_start=date(2026, 8, 1),
        period_a_end=date(2026, 8, 31),
        period_b_start=date(2026, 9, 1),
        period_b_end=date(2026, 9, 30),
    )
    assert res_dec["period_a"]["total_spent"] == 50000.0
    assert res_dec["period_b"]["total_spent"] == 35000.0
    assert res_dec["absolute_change"] == -15000.0
    assert res_dec["percentage_change"] == -30.0
    assert res_dec["percentage_change_status"] == "VALID"
    assert res_dec["higher_period"] == "August 2026"
    assert "decreased" in res_dec["comparison_verdict"]


def test_period_comparison_zero_baseline_division_safety():
    """
    Requirement 8:
    If period A is zero, return 'percentage change unavailable because the baseline is zero'.
    Never divide by zero or fabricate a percentage.
    """
    context_zero_baseline = {
        "transactions": [
            # Period A (August): 0 transactions
            # Period B (September): ₹25,000
            {"id": "T1", "amount": 25000.0, "type": "EXPENSE", "category": "Housing", "date": "2026-09-01"},
        ]
    }
    res = calculate_period_comparison(
        context_zero_baseline,
        period_a_start=date(2026, 8, 1),
        period_a_end=date(2026, 8, 31),
        period_b_start=date(2026, 9, 1),
        period_b_end=date(2026, 9, 30),
    )
    assert res["period_a"]["total_spent"] == 0.0
    assert res["period_b"]["total_spent"] == 25000.0
    assert res["absolute_change"] == 25000.0
    assert res["percentage_change"] is None
    assert res["percentage_change_status"] == "BASELINE_ZERO"
    assert "unavailable because the baseline is zero" in res["percentage_change_display"]
    assert any("baseline" in cav.lower() for cav in res["caveats"])


def test_period_comparison_refund_and_transfer_exclusion():
    """
    Validates that internal account transfers and refund reversals are strictly excluded
    consistently across both comparison periods.
    """
    context = {
        "transactions": [
            # Period A
            {"id": "T1", "amount": 5000.0, "type": "EXPENSE", "category": "Food", "date": "2026-09-05"},
            {"id": "T_TR1", "amount": 50000.0, "type": "EXPENSE", "description": "Transfer to Savings", "category": "Transfer", "date": "2026-09-06"},
            {"id": "T_REF1", "amount": 1000.0, "type": "EXPENSE", "description": "Refund reversal", "category": "Food", "date": "2026-09-07"},
            # Period B
            {"id": "T2", "amount": 7000.0, "type": "EXPENSE", "category": "Food", "date": "2026-10-05"},
            {"id": "T_TR2", "amount": 30000.0, "type": "EXPENSE", "description": "NEFT transfer to a/c 1234", "category": "General", "date": "2026-10-06"},
        ]
    }
    res = calculate_period_comparison(
        context,
        period_a_start=date(2026, 9, 1),
        period_a_end=date(2026, 9, 30),
        period_b_start=date(2026, 10, 1),
        period_b_end=date(2026, 10, 31),
    )
    # T1 = 5000, T_TR1 & T_REF1 excluded
    assert res["period_a"]["total_spent"] == 5000.0
    assert res["period_a"]["transaction_count"] == 1
    # T2 = 7000, T_TR2 excluded
    assert res["period_b"]["total_spent"] == 7000.0
    assert res["period_b"]["transaction_count"] == 1
    assert res["absolute_change"] == 2000.0


def test_period_comparison_date_boundaries():
    """
    Verifies that date boundaries are inclusive of start and end dates,
    and exclude transactions occurring even 1 day outside the boundary.
    """
    context = {
        "transactions": [
            {"id": "T_EARLY", "amount": 100.0, "type": "EXPENSE", "date": "2026-08-31"},
            {"id": "T_START", "amount": 200.0, "type": "EXPENSE", "date": "2026-09-01"},
            {"id": "T_END", "amount": 300.0, "type": "EXPENSE", "date": "2026-09-30"},
            {"id": "T_LATE", "amount": 400.0, "type": "EXPENSE", "date": "2026-10-01"},
        ]
    }
    res = calculate_period_comparison(
        context,
        period_a_start=date(2026, 9, 1),
        period_a_end=date(2026, 9, 30),
        period_b_start=date(2026, 10, 1),
        period_b_end=date(2026, 10, 31),
    )
    # Period A: T_START (200) + T_END (300) = 500 (T_EARLY excluded)
    assert res["period_a"]["total_spent"] == 500.0
    assert res["period_a"]["transaction_count"] == 2
    # Period B: T_LATE (400) = 400
    assert res["period_b"]["total_spent"] == 400.0
    assert res["period_b"]["transaction_count"] == 1


# ==============================================================================
# Part C: Category-Wise Variance Attribution
# ==============================================================================

def test_category_variance_attribution_ranking():
    """
    Part C:
    Verifies:
    1. Category-wise computation: Period A spent, Period B spent, absolute diff, % change.
    2. Ranking by contribution magnitude.
    3. Supporting transactions returned for largest differences.
    4. Distinction of mathematical contribution from causal claims.
    """
    context = {
        "transactions": [
            # September
            {"id": "T1", "amount": 10000.0, "type": "EXPENSE", "category": "Food", "description": "Grocery run", "date": "2026-09-05"},
            {"id": "T2", "amount": 5000.0, "type": "EXPENSE", "category": "Transport", "description": "Fuel", "date": "2026-09-10"},
            {"id": "T3", "amount": 8000.0, "type": "EXPENSE", "category": "Entertainment", "description": "Concert", "date": "2026-09-12"},
            # October
            {"id": "T4", "amount": 25000.0, "type": "EXPENSE", "category": "Food", "description": "Dining out & party", "date": "2026-10-05"},
            {"id": "T5", "amount": 6000.0, "type": "EXPENSE", "category": "Transport", "description": "Uber rides", "date": "2026-10-10"},
            {"id": "T6", "amount": 2000.0, "type": "EXPENSE", "category": "Entertainment", "description": "Movie", "date": "2026-10-15"},
        ]
    }
    res = calculate_period_comparison(
        context,
        period_a_start=date(2026, 9, 1),
        period_a_end=date(2026, 9, 30),
        period_b_start=date(2026, 10, 1),
        period_b_end=date(2026, 10, 31),
    )
    # Total A = 23000, Total B = 33000, Diff = +10000
    assert res["absolute_change"] == 10000.0

    variances = res["category_variances"]
    assert len(variances) == 3

    # Food changed by +15,000 (largest absolute difference) -> Rank 1
    assert variances[0]["category"] == "Food"
    assert variances[0]["period_a_spent"] == 10000.0
    assert variances[0]["period_b_spent"] == 25000.0
    assert variances[0]["absolute_difference"] == 15000.0
    assert variances[0]["percentage_change"] == 150.0
    assert len(variances[0]["supporting_transactions"]) > 0
    assert variances[0]["supporting_transactions"][0]["description"] == "Dining out & party"
    assert "mathematical contribution" in variances[0]["mathematical_contribution_note"]

    # Entertainment changed by -6,000 -> Rank 2
    assert variances[1]["category"] == "Entertainment"
    assert variances[1]["absolute_difference"] == -6000.0
    assert variances[1]["percentage_change"] == -75.0

    # Transport changed by +1,000 -> Rank 3
    assert variances[2]["category"] == "Transport"
    assert variances[2]["absolute_difference"] == 1000.0

    assert len(res["top_increases"]) == 2  # Food, Transport
    assert len(res["top_decreases"]) == 1  # Entertainment


def test_variance_attribution_query_parsing():
    """
    Questions such as:
    - 'Which categories increased the most?'
    - 'Why did my expenses increase?'
    - 'What caused the difference between September and October?'
    are correctly routed to PERIOD_COMPARISON with variance attribution enabled.
    """
    res1 = parse_question("Which categories increased the most?")
    assert res1["intent"] == "PERIOD_COMPARISON"

    res2 = parse_question("Why did my expenses increase?")
    assert res2["intent"] == "PERIOD_COMPARISON"

    res3 = parse_question("What caused the difference between September and October?")
    assert res3["intent"] == "PERIOD_COMPARISON"
    plan3 = res3["query_plan"]
    assert plan3.date_range.start_date.month == 9
    assert plan3.comparison_date_range.start_date.month == 10


# ==============================================================================
# Part D: Multi-Month Spending Trends & Missing Data Handling
# ==============================================================================

def test_multi_month_trends_chronological_ordering():
    """
    Part D:
    Questions: 'Show my spending trend over the last six months.'
    Verifies:
    1. Returns chronological monthly totals and transaction counts.
    2. Proper chronological month ordering (oldest to newest).
    """
    context = {
        "transactions": [
            {"id": "T1", "amount": 10000.0, "type": "EXPENSE", "date": "2026-05-15"},
            {"id": "T2", "amount": 12000.0, "type": "EXPENSE", "date": "2026-06-15"},
            {"id": "T3", "amount": 11000.0, "type": "EXPENSE", "date": "2026-07-15"},
            {"id": "T4", "amount": 14000.0, "type": "EXPENSE", "date": "2026-08-15"},
            {"id": "T5", "amount": 13000.0, "type": "EXPENSE", "date": "2026-09-15"},
            {"id": "T6", "amount": 15000.0, "type": "EXPENSE", "date": "2026-10-15"},
        ]
    }
    res = calculate_spending_trends(context, num_months=6, end_date=date(2026, 10, 19))
    points = res["trend_points"]
    assert len(points) == 6

    # Verify chronological ordering
    months = [p["month"] for p in points]
    assert months == ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"]

    assert points[0]["total_spent"] == 10000.0
    assert points[-1]["total_spent"] == 15000.0
    assert res["average_monthly_spend"] == 12500.0
    assert res["trend_direction"] == "UPWARD"


def test_missing_months_versus_confirmed_zero_spend():
    """
    Part D requirement:
    Distinguish a genuine zero from a period for which data is unavailable or incomplete.
    Do not assume that an absent month means the user spent nothing.
    """
    # Statement covers August, September, October 2026.
    # In September 2026, the user had 0 transactions (confirmed zero spend).
    # Prior to August (May, June, July), no statements were ever imported (DATA_UNAVAILABLE).
    context = {
        "transactions": [
            {"id": "T1", "amount": 20000.0, "type": "EXPENSE", "date": "2026-08-10"},
            # September 2026: 0 transactions
            {"id": "T2", "amount": 30000.0, "type": "EXPENSE", "date": "2026-10-10"},
        ]
    }
    res = calculate_spending_trends(context, num_months=6, end_date=date(2026, 10, 19))
    points = {p["month"]: p for p in res["trend_points"]}

    # May, June, July are outside statement coverage -> DATA_UNAVAILABLE
    assert points["2026-05"]["status"] == "DATA_UNAVAILABLE"
    assert points["2026-05"]["is_covered"] is False
    assert points["2026-06"]["status"] == "DATA_UNAVAILABLE"
    assert points["2026-07"]["status"] == "DATA_UNAVAILABLE"

    # August has verified spend -> CONFIRMED_SPEND
    assert points["2026-08"]["status"] == "CONFIRMED_SPEND"
    assert points["2026-08"]["total_spent"] == 20000.0

    # September is within statement coverage but has 0 transactions -> CONFIRMED_ZERO
    assert points["2026-09"]["status"] == "CONFIRMED_ZERO"
    assert points["2026-09"]["total_spent"] == 0.0
    assert points["2026-09"]["is_covered"] is True

    # October has verified spend -> CONFIRMED_SPEND
    assert points["2026-10"]["status"] == "CONFIRMED_SPEND"
    assert points["2026-10"]["total_spent"] == 30000.0

    # Average monthly spend should be calculated over COVERED months only (August, September, October = (20000+0+30000)/3 = 16,666.67)
    # NOT deflated by dividing by 6!
    assert res["available_months_count"] == 3
    assert res["missing_months_count"] == 3
    assert res["average_monthly_spend"] == round(50000.0 / 3, 2)
    assert any("not assumed to have zero spend" in cav for cav in res["caveats"])


# ==============================================================================
# Part E: User Isolation & Grounded GraphRAG Pipeline
# ==============================================================================

def test_user_data_isolation_period_analytics():
    """
    Validates that user data is isolated: Alice cannot retrieve or calculate
    trends/comparisons on Bob's transactions.
    """
    mock_db = MagicMock(spec=Neo4jService)
    alice_context = {
        "transactions": [
            {"id": "TX_ALICE_1", "amount": 5000.0, "type": "EXPENSE", "date": "2026-09-10"},
            {"id": "TX_ALICE_2", "amount": 6000.0, "type": "EXPENSE", "date": "2026-10-10"},
        ]
    }
    mock_db.get_financial_context.side_effect = lambda uid: alice_context if uid == "U_ALICE" else {"transactions": []}

    rag = GraphRAG(db=mock_db)

    with patch("backend.app.rag.graph_rag.ask_llm") as mock_llm:
        mock_llm.return_value = {"content": "Comparison Explanation", "prompt_tokens": 10, "completion_tokens": 10, "tokens_used": 20}
        alice_res = rag.process_query("Did I spend more in September than October?", user_id="U_ALICE")
        bob_res = rag.process_query("Did I spend more in September than October?", user_id="U_BOB")

    assert alice_res["math_result"]["period_a"]["total_spent"] == 5000.0
    assert alice_res["math_result"]["period_b"]["total_spent"] == 6000.0
    assert bob_res["math_result"]["period_a"]["total_spent"] == 0.0
    assert bob_res["math_result"]["period_b"]["total_spent"] == 0.0


def test_graph_rag_period_comparison_evidence_pipeline():
    """
    Validates complete GraphRAG pipeline output for PERIOD_COMPARISON:
    - Verifiable facts linking to source transaction IDs
    - Auditability metadata (formula, caveats, exact date ranges)
    """
    mock_db = MagicMock(spec=Neo4jService)
    mock_db.get_financial_context.return_value = {
        "transactions": [
            {"id": "TX_1", "amount": 10000.0, "type": "EXPENSE", "category": "Food", "date": "2026-09-10"},
            {"id": "TX_2", "amount": 15000.0, "type": "EXPENSE", "category": "Food", "date": "2026-10-10"},
        ]
    }
    rag = GraphRAG(db=mock_db)

    with patch("backend.app.rag.graph_rag.ask_llm") as mock_llm:
        mock_llm.return_value = {"content": "Explanation", "prompt_tokens": 10, "completion_tokens": 10, "tokens_used": 20}
        res = rag.process_query("Compare my expenses in September and October 2026", user_id="U001")

    assert res["intent"] == "PERIOD_COMPARISON"
    evidence = res["evidence"]
    assert len(evidence) >= 4

    labels = [ev["label"] for ev in evidence]
    assert any("Baseline Total" in l for l in labels)
    assert any("Comparison Total" in l for l in labels)
    assert any("Absolute Change" in l for l in labels)
    assert any("Percentage Change" in l for l in labels)

    meta = res["evidence_metadata"]
    assert "September 2026 vs October 2026" in meta["reporting_period"]
    assert meta["methodology_formula"] is not None


def test_graph_rag_spending_trend_pipeline():
    """
    Validates complete GraphRAG pipeline output for SPENDING_TREND:
    - Average monthly spend
    - Chronological data points
    - Coverage range and caveats
    """
    mock_db = MagicMock(spec=Neo4jService)
    mock_db.get_financial_context.return_value = {
        "transactions": [
            {"id": "T1", "amount": 8000.0, "type": "EXPENSE", "date": "2026-08-01"},
            {"id": "T2", "amount": 9000.0, "type": "EXPENSE", "date": "2026-09-01"},
            {"id": "T3", "amount": 10000.0, "type": "EXPENSE", "date": "2026-10-01"},
        ]
    }
    rag = GraphRAG(db=mock_db)

    with patch("backend.app.rag.graph_rag.ask_llm") as mock_llm:
        mock_llm.return_value = {"content": "Trend Explanation", "prompt_tokens": 10, "completion_tokens": 10, "tokens_used": 20}
        res = rag.process_query("Show my spending trend over the last six months", user_id="U001")

    assert res["intent"] == "SPENDING_TREND"
    math_res = res["math_result"]
    assert math_res["total_months_evaluated"] == 6
    assert math_res["available_months_count"] == 3
    assert math_res["average_monthly_spend"] == 9000.0

    labels = [ev["label"] for ev in res["evidence"]]
    assert "Average Monthly Spend" in labels
    assert "Coverage Range" in labels
    assert "Data Completeness" in labels


def test_empty_dataset_handling():
    """
    Validates graceful handling when dataset is completely empty:
    Zero totals, no division by zero, appropriate caveats.
    """
    res_comp = calculate_period_comparison(
        {"transactions": []},
        period_a_start=date(2026, 9, 1),
        period_a_end=date(2026, 9, 30),
        period_b_start=date(2026, 10, 1),
        period_b_end=date(2026, 10, 31),
    )
    assert res_comp["period_a"]["total_spent"] == 0.0
    assert res_comp["period_b"]["total_spent"] == 0.0
    assert res_comp["absolute_change"] == 0.0
    assert res_comp["percentage_change"] is None
    assert len(res_comp["caveats"]) > 0

    res_trend = calculate_spending_trends({"transactions": []}, num_months=6)
    assert res_trend["available_months_count"] == 0
    assert res_trend["average_monthly_spend"] == 0.0
    assert len(res_trend["caveats"]) > 0
