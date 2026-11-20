"""
Regression test suite for Category Percentage and Expenditure Relative Proportions.

Verifies:
1. Category spending is computed as a proportion of all eligible expenses in the period.
2. The percentage is NOT 100% when other category expenses exist.
3. Total expenses are preserved accurately alongside category-specific spending.
4. Edge cases: zero expenses (no ZeroDivisionError) and zero spend in requested category.
"""
from datetime import date
from unittest.mock import MagicMock, patch
import pytest

from backend.app.rag.graph_rag import GraphRAG
from backend.app.database.neo4j_service import Neo4jService


def test_category_percentage_relative_to_period_total():
    """
    Verifies that querying a specific category (e.g., Food = 10,000)
    against a period with multiple categories (Housing=20,000, Utilities=5,000; Total=35,000)
    computes percentage as 28.57%, NOT 100.0%.
    """
    mock_db = MagicMock(spec=Neo4jService)
    
    # Grounded subgraph context containing all monthly transactions across categories
    multi_cat_context = {
        "accounts": [{"id": "ACC1", "balance": 100000.0}],
        "transactions": [
            {"id": "T1", "amount": 20000.0, "type": "EXPENSE", "category": "Housing", "date": "2026-10-01"},
            {"id": "T2", "amount": 10000.0, "type": "EXPENSE", "category": "Food", "date": "2026-10-05"},
            {"id": "T3", "amount": 5000.0, "type": "EXPENSE", "category": "Utilities", "date": "2026-10-10"},
        ],
        "loans": [],
        "incomes": [],
        "goals": [],
    }

    mock_db.retrieve_grounded_subgraph.return_value = {
        "user_id": "U001",
        "intent": "CATEGORY_EXPENSE",
        "grounded_entities": multi_cat_context,
        "source_identifiers": ["Transaction:T2", "Category:Food"],
        "graph_paths": [],
        "context": multi_cat_context,
    }

    rag = GraphRAG(db=mock_db)

    with patch("backend.app.rag.graph_rag.ask_llm") as mock_llm:
        mock_llm.return_value = {"content": "Explanation", "prompt_tokens": 10, "completion_tokens": 10, "tokens_used": 20}
        result = rag.process_query("How much did I spend on Food?", user_id="U001")

    math_res = result["math_result"]
    
    # Assertions for mathematical correctness
    assert math_res["requested_category"] == "Food"
    assert math_res["category_spent"] == 10000.0
    assert math_res["total_expenses"] == 35000.0
    assert math_res["percentage_of_total"] == 28.57  # round(10000 / 35000 * 100, 2)
    assert math_res["percentage_of_total"] != 100.0, "Percentage must not be 100% when other expenses exist"
    assert len(math_res["all_categories"]) == 3


def test_category_percentage_with_explicit_total_in_context():
    """
    Verifies that if context carries precomputed total_expenses,
    it is honored as the denominator even if transactions are selectively filtered.
    """
    rag = GraphRAG(db=MagicMock())
    
    clean_context = {
        "total_expenses": 50000.0,
        "transactions": [
            {"id": "TF1", "amount": 5000.0, "type": "EXPENSE", "category": "Food", "date": "2026-10-02"}
        ]
    }
    
    res = rag.execute_reasoning("CATEGORY_EXPENSE", clean_context, entities={"category": "Food"})
    assert res["requested_category"] == "Food"
    assert res["category_spent"] == 5000.0
    assert res["total_expenses"] == 50000.0
    assert res["percentage_of_total"] == 10.0  # (5,000 / 50,000) * 100


def test_category_percentage_zero_expenses_edge_case():
    """
    Verifies edge case where the period has zero expense transactions.
    Must return 0.0% without ZeroDivisionError.
    """
    rag = GraphRAG(db=MagicMock())
    empty_context = {"transactions": []}
    
    res = rag.execute_reasoning("CATEGORY_EXPENSE", empty_context, entities={"category": "Food"})
    assert res["requested_category"] == "Food"
    assert res["category_spent"] == 0.0
    assert res["total_expenses"] == 0.0
    assert res["percentage_of_total"] == 0.0


def test_category_percentage_zero_spend_in_category():
    """
    Verifies query for a category with 0 spend when other categories exist.
    """
    rag = GraphRAG(db=MagicMock())
    context = {
        "transactions": [
            {"id": "T1", "amount": 25000.0, "type": "EXPENSE", "category": "Housing", "date": "2026-10-01"}
        ]
    }
    
    res = rag.execute_reasoning("CATEGORY_EXPENSE", context, entities={"category": "Food"})
    assert res["requested_category"] == "Food"
    assert res["category_spent"] == 0.0
    assert res["total_expenses"] == 25000.0
    assert res["percentage_of_total"] == 0.0
