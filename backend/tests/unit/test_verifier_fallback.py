"""
Unit tests asserting that build_deterministic_fallback's output passes
verify_explanation for EVERY intent on both seeded data and ugly-cents edge cases.

Protects the fail-closed path: if an LLM explanation is rejected or unavailable,
the deterministic fallback MUST always verify with 0 blocking violations.
"""

from decimal import Decimal
import pytest

from backend.app.rag.graph_rag import GraphRAG
from backend.app.services.response_generator import build_deterministic_fallback
from backend.app.services.verifier import verify_explanation


@pytest.fixture(scope="module")
def rag():
    return GraphRAG()


INTENTS = [
    ("PURCHASE_SAFETY", {"amount": 15000.0}),
    ("SAVINGS_ANALYSIS", {}),
    ("EMERGENCY_FUND_ANALYSIS", {}),
    ("EMERGENCY_RUNWAY_ANALYSIS", {}),
    ("DEBT_ANALYSIS", {}),
    ("FINANCIAL_HEALTH", {}),
    ("CATEGORY_EXPENSE", {"category": "Food"}),
    ("MERCHANT_EXPENSE", {"merchant": "Swiggy"}),
    ("TOP_TRANSACTIONS", {"limit": 5}),
    ("PERIOD_COMPARISON", {}),
    ("SPENDING_TREND", {}),
]


@pytest.mark.parametrize("intent,entities", INTENTS)
def test_deterministic_fallback_passes_verifier_on_seeded_data(rag, intent, entities):
    """Assert fallback output on real seeded database subgraphs passes verifier."""
    parsed = {"intent": intent, **entities}
    ctx = rag.retrieve_subgraph("U001", intent, entities=parsed)
    math_res = rag.execute_reasoning(intent, ctx, entities=parsed)

    fallback_text = build_deterministic_fallback(math_res)
    res = verify_explanation(fallback_text, math_res, intent=intent)

    assert res.verified is True, f"Fallback failed verifier for {intent}: {res.get('violations')}"
    assert len(res["violations"]) == 0


UGLY_CENTS_CASES = [
    (
        "PURCHASE_SAFETY",
        {
            "decision": "NOT_SAFE",
            "risk_level": "HIGH",
            "evidence": {
                "current_balance": 45123.45,
                "pending_emi": 10000.55,
                "monthly_expenses": 21000.12,
                "purchase_amount": 15000.99,
                "emergency_requirement": 63000.36,
                "balance_after_purchase": 20121.91,
            },
            "reason": "The purchase is not financially safe with ugly cents.",
            "reporting_period": "2026-11",
            "is_sufficient_data": True,
        },
    ),
    (
        "SAVINGS_ANALYSIS",
        {
            "savings_rate": 65.43,
            "savings_status": "EXCELLENT",
            "income": 60123.45,
            "expenses": 20789.12,
            "savings": 39334.33,
            "evidence": {
                "income": 60123.45,
                "expenses": 20789.12,
                "savings": 39334.33,
            },
            "reporting_period": "2026-11",
            "is_sufficient_data": True,
        },
    ),
    (
        "EMERGENCY_RUNWAY_ANALYSIS",
        {
            "runway_months": 2.17,
            "status": "HEALTHY",
            "current_balance": 45123.45,
            "monthly_expenses": 20789.12,
            "evidence": {
                "current_balance": 45123.45,
                "monthly_expenses": 20789.12,
            },
            "reporting_period": "2026-11",
            "is_sufficient_data": True,
        },
    ),
    (
        "DEBT_ANALYSIS",
        {
            "dti_ratio": 16.64,
            "risk_level": "LOW",
            "total_outstanding_debt": 150123.45,
            "monthly_emi": 10000.55,
            "evidence": {
                "total_outstanding_debt": 150123.45,
                "monthly_emi": 10000.55,
            },
            "reporting_period": "2026-11",
            "is_sufficient_data": True,
        },
    ),
    (
        "FINANCIAL_HEALTH",
        {
            "health_score": 88.5,
            "grade": "B",
            "savings_rate": 65.4,
            "runway_months": 2.17,
            "dti_ratio": 16.64,
            "emergency_shortfall": 33123.45,
            "evidence": {
                "emergency_shortfall": 33123.45,
            },
            "reporting_period": "2026-11",
            "is_sufficient_data": True,
        },
    ),
]


@pytest.mark.parametrize("intent,math_res", UGLY_CENTS_CASES)
def test_deterministic_fallback_passes_verifier_on_ugly_cents(intent, math_res):
    """Assert fallback output formats cents correctly and passes numeric verification."""
    fallback_text = build_deterministic_fallback(math_res)
    res = verify_explanation(fallback_text, math_res, intent=intent)

    assert res.verified is True, f"Ugly cents fallback failed verifier for {intent}: {res.get('violations')}"
    assert len(res["violations"]) == 0
