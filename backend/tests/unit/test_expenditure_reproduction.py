"""
Reproduction test suite for Expenditure Intelligence bugs identified in Phase 1 Audit.

Validates the exact failure modes before applying Phase 2 fixes:
1. Category percentage calculation bug (isolated category retrieval causes 100.0% report).
2. Merchant query misclassification (merchants like Uber treated as Category or ignored).
3. Top N transactions failure (routed to category aggregates rather than individual transactions).
4. Date handling in comparative questions (second period dropped).
"""
from datetime import date
from unittest.mock import MagicMock, patch
import pytest

from backend.app.nlu.question_parser import parse_question, extract_temporal_reporting_date, check_date_ambiguity
from backend.app.rag.graph_rag import GraphRAG
from backend.app.database.neo4j_service import Neo4jService
from backend.app.engine.financial_engine import calculate_category_expenses


# ==============================================================================
# Issue 1: Category Percentage Calculation
# ==============================================================================
def test_reproduce_category_percentage_isolation_bug():
    """
    REPRODUCTION TEST 1:
    When a user asks 'How much did I spend on Food?', the current architecture
    retrieves ONLY Food transactions in `retrieve_grounded_subgraph`.
    
    When `calculate_category_expenses` is executed on that isolated context,
    `total_expenses` equals `category_spent`, causing `percentage_of_total`
    to be 100.0%, despite the user having substantial non-food expenses in the same period.
    """
    isolated_food_context = {
        "accounts": [{"id": "ACC1", "balance": 50000.0}],
        "transactions": [
            {"id": "TX_F1", "amount": 3000.0, "type": "EXPENSE", "category": "Food", "date": "2026-10-05"},
            {"id": "TX_F2", "amount": 2000.0, "type": "EXPENSE", "category": "Food", "date": "2026-10-12"},
        ]
    }
    
    mock_db = MagicMock(spec=Neo4jService)
    mock_db.retrieve_grounded_subgraph.return_value = {
        "user_id": "U001",
        "intent": "CATEGORY_EXPENSE",
        "grounded_entities": isolated_food_context,
        "source_identifiers": ["Transaction:TX_F1", "Transaction:TX_F2"],
        "graph_paths": [],
        "context": isolated_food_context,
    }
    
    rag = GraphRAG(db=mock_db)
    
    with patch("backend.app.rag.graph_rag.ask_llm") as mock_llm:
        mock_llm.return_value = {"content": "Explanation", "prompt_tokens": 10, "completion_tokens": 10, "tokens_used": 20}
        result = rag.process_query("How much did I spend on Food?", user_id="U001")
    
    math_res = result["math_result"]
    assert math_res["requested_category"] == "Food"
    assert math_res["category_spent"] == 5000.0
    
    # In the existing buggy code, total_expenses is 5000.0 and percentage is 100.0%
    print(f"\n[REPRODUCED BUG 1] total_expenses={math_res['total_expenses']}, percentage={math_res['percentage_of_total']}%")
    assert math_res["percentage_of_total"] == 100.0, "Expected bug reproduced: isolated retrieval results in 100% calculation"


# ==============================================================================
# Issue 2: Merchant Matching Misclassification (Resolved in Phase 2.2)
# ==============================================================================
def test_reproduce_merchant_misclassification_bug():
    """
    ISSUE 2 VERIFICATION (Phase 2.2 Resolved):
    Asking 'How much did I spend on Uber?' is now accurately parsed as MERCHANT_EXPENSE
    with merchant='Uber' and attached query plan, rather than misclassified as CATEGORY_EXPENSE.
    """
    parsed = parse_question("How much did I spend on Uber?")
    print(f"\n[RESOLVED BUG 2] 'spend on Uber' parsed: intent={parsed['intent']}, merchant={parsed.get('merchant')}")
    assert parsed["intent"] == "MERCHANT_EXPENSE"
    assert parsed.get("merchant") == "Uber"
    assert parsed.get("query_plan") is not None


# ==============================================================================
# Issue 3: Top Transactions Ignores N and Transaction-Level Details (Resolved in Phase 2.2)
# ==============================================================================
def test_reproduce_top_transactions_aggregation_bug():
    """
    ISSUE 3 VERIFICATION (Phase 2.2 Resolved):
    Asking 'What are my 5 biggest expenses?' is now parsed as TOP_TRANSACTIONS
    with limit=5 and sort_by='amount' rather than routed to EXPENSE_BREAKDOWN.
    """
    parsed = parse_question("What are my 5 biggest expenses?")
    print(f"\n[RESOLVED BUG 3] '5 biggest expenses' parsed intent: {parsed['intent']}, limit={parsed.get('limit')}")
    assert parsed["intent"] == "TOP_TRANSACTIONS"
    assert parsed.get("limit") == 5
    assert parsed.get("query_plan") is not None



# ==============================================================================
# Issue 4: Comparative Date Handling Drops Second Period
# ==============================================================================
def test_reproduce_period_comparison_drops_second_month_bug():
    """
    REPRODUCTION TEST 4:
    Asking 'Did I spend more in September than October?' contains two months.
    `extract_temporal_reporting_date` matches the first month name ('September')
    and returns date(year, 9, 1). The second month ('October') is completely dropped.
    """
    extracted_date = extract_temporal_reporting_date("Did I spend more in September than October?")
    print(f"\n[REPRODUCED BUG 4] 'September than October' extracted_date: {extracted_date}")
    
    # Bug: Only September is extracted (month 9)
    assert extracted_date is not None
    assert extracted_date.month == 9
    # There is no function or return value to extract the second comparison month
