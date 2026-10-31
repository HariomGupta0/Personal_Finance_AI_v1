"""
Unit tests for AI-Powered Personalized Financial Planning Engine.

Tests:
  - Complete plan generation with verified figures
  - Missing income / zero-income graceful limitation handling
  - Insufficient transaction history flagging
  - Discretionary category budgeting and potential savings
  - Savings targets and emergency fund timeline calculation
  - Recurring bill & EMI commitment detection
  - LLM response parsing and deterministic rule fallback on error
  - FastAPI /api/finance/plan endpoint integration with dependency overrides
"""

import asyncio
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.app.services.financial_planner import (
    generate_financial_plan,
    _is_discretionary_category,
    _detect_recurring_commitments,
    _calculate_budget_limits,
    _calculate_savings_and_emergency_targets,
)
from backend.tests.unit.test_financial_engine import (
    MOCK_CONTEXT,
    ZERO_INCOME_CONTEXT,
    ZERO_EXPENSE_CONTEXT,
    _YM,
)


def test_is_discretionary_category():
    assert _is_discretionary_category("Food") is True
    assert _is_discretionary_category("Dining") is True
    assert _is_discretionary_category("Shopping") is True
    assert _is_discretionary_category("Entertainment") is True
    assert _is_discretionary_category("Housing") is False
    assert _is_discretionary_category("Rent") is False
    assert _is_discretionary_category("Utilities") is False
    assert _is_discretionary_category("Healthcare") is False


def test_detect_recurring_commitments():
    ctx = {
        "loans": [
            {"id": "L001", "loan": "Car Loan", "emi": 7500.0, "status": "PENDING"}
        ],
        "transactions": [
            {"type": "EXPENSE", "amount": 649.0, "description": "Netflix Subscription", "date": f"{_YM}-10"},
            {"type": "EXPENSE", "amount": 1200.0, "description": "Airtel Broadband Wifi", "date": f"{_YM}-12"},
            {"type": "EXPENSE", "amount": 500.0, "description": "Swiggy Order", "date": f"{_YM}-15"},
        ],
    }
    recurring = _detect_recurring_commitments(ctx)
    names = [r["name"] for r in recurring]
    assert any("Car Loan" in n for n in names)
    assert any("Netflix" in n for n in names)
    assert any("Wifi" in n or "Airtel" in n for n in names)
    assert not any("Swiggy" in n for n in names)


def test_calculate_budget_limits():
    breakdown = [
        {"category": "Housing", "amount": 15000.0, "percentage": 50.0},
        {"category": "Food", "amount": 9000.0, "percentage": 30.0},
        {"category": "Shopping", "amount": 6000.0, "percentage": 20.0},
    ]
    budget = _calculate_budget_limits(
        total_income=40000.0,
        total_expenses=30000.0,
        category_breakdown=breakdown,
        savings_rate=25.0,
    )
    assert budget["current_total_expenses"] == 30000.0
    assert budget["total_potential_savings"] > 0
    assert budget["recommended_total_budget"] < 30000.0

    # Housing (essential) should not be cut
    housing_item = next(c for c in budget["categories"] if c["category"] == "Housing")
    assert housing_item["potential_savings"] == 0.0
    assert housing_item["recommended_limit"] == 15000.0

    # Food and Shopping (discretionary) should have recommended savings
    food_item = next(c for c in budget["categories"] if c["category"] == "Food")
    assert food_item["potential_savings"] > 0.0
    assert food_item["status"] == "OVER_BUDGET"


def test_calculate_savings_and_emergency_targets():
    ef_data = {
        "monthly_expenses": 20000.0,
        "recommended_fund": 60000.0,
        "current_fund": 10000.0,
        "shortfall": 50000.0,
    }
    accounts = [{"id": "A1", "balance": 15000.0}]
    targets = _calculate_savings_and_emergency_targets(
        total_income=50000.0,
        total_expenses=20000.0,
        current_savings=30000.0,
        potential_budget_savings=3000.0,
        emergency_fund_data=ef_data,
        accounts=accounts,
    )
    assert targets["emergency_fund_3mo_target"] == 60000.0
    assert targets["recommended_monthly_savings"] > 0
    # effective cushion is max(10000, 15000) = 15000, shortfall is 45000
    assert targets["emergency_fund_shortfall"] == 45000.0
    assert targets["estimated_months_to_target"] is not None
    assert targets["estimated_months_to_target"] > 0


def test_generate_financial_plan_deterministic():
    async def _test():
        plan = await generate_financial_plan(
            context=MOCK_CONTEXT,
            user_id="U001",
            use_ai=False,
        )
        assert plan["status"] == "SUCCESS"
        assert plan["user_id"] == "U001"
        assert "financial_summary" in plan
        assert plan["financial_summary"]["monthly_income"] == 60000.0
        assert plan["financial_summary"]["monthly_expenses"] == 21000.0
        assert plan["financial_summary"]["net_savings"] == 39000.0

        # Budget plan
        assert "budget_plan" in plan
        assert len(plan["budget_plan"]["categories"]) == 4

        # Savings plan
        assert "savings_plan" in plan
        assert plan["savings_plan"]["emergency_fund_3mo_target"] == 63000.0

        # Actions: 3 to 5 prioritized actions
        assert len(plan["prioritized_actions"]) >= 3
        for act in plan["prioritized_actions"]:
            assert act["priority"] in ("HIGH", "MEDIUM", "LOW")
            assert len(act["title"]) > 0
            assert len(act["action"]) > 0
            assert len(act["expected_impact"]) > 0
            assert len(act["rationale"]) > 0

        assert plan["ai_metadata"]["source"] == "deterministic_rules"

    asyncio.run(_test())


def test_generate_financial_plan_zero_income():
    async def _test():
        plan = await generate_financial_plan(
            context=ZERO_INCOME_CONTEXT,
            user_id="U001",
            use_ai=False,
        )
        assert plan["status"] == "SUCCESS"
        assert plan["financial_summary"]["monthly_income"] == 0.0
        assert len(plan["data_limitations"]) > 0
        assert any("No monthly income" in lim for lim in plan["data_limitations"])

        # Ensure actions include prompt to record income
        action_titles = [a["title"] for a in plan["prioritized_actions"]]
        assert any("Income" in t or "Profile" in t or "Financial Profile" in t for t in action_titles)

    asyncio.run(_test())


def test_generate_financial_plan_insufficient_history():
    async def _test():
        single_tx_context = {
            "accounts": [{"balance": 5000}],
            "transactions": [{"amount": 250, "type": "EXPENSE", "category": "Food", "date": f"{_YM}-01"}],
            "incomes": [],
            "loans": [],
            "goals": [],
        }
        plan = await generate_financial_plan(
            context=single_tx_context,
            user_id="U001",
            use_ai=False,
        )
        assert plan["status"] == "SUCCESS"
        assert any("Limited statement history" in lim for lim in plan["data_limitations"])

    asyncio.run(_test())


def test_generate_financial_plan_with_llm_success():
    async def _test():
        mock_llm_json = """{
            "executive_summary": "You have a solid financial profile with a 65% savings rate.",
            "spending_insights": [
                {"topic": "Dominant Expense", "text": "Housing is your top expense.", "category": "Housing"}
            ],
            "action_plan": [
                {
                    "priority": "HIGH",
                    "title": "Build Emergency Fund",
                    "category": "Savings",
                    "action": "Deposit ₹10,000 monthly.",
                    "expected_impact": "Full safety net in 2 months",
                    "rationale": "Shortfall of ₹18,000"
                },
                {
                    "priority": "MEDIUM",
                    "title": "Optimize Dining",
                    "category": "Food",
                    "action": "Cap dining at ₹3,200.",
                    "expected_impact": "Save ₹800/month",
                    "rationale": "Food was ₹4,000"
                }
            ]
        }"""
        with patch(
            "backend.app.services.financial_planner.ask_llm_async",
            new_callable=AsyncMock,
            return_value={"content": mock_llm_json, "model": "mock-groq-70b", "error": None},
        ):
            plan = await generate_financial_plan(
                context=MOCK_CONTEXT,
                user_id="U001",
                use_ai=True,
            )
            assert plan["ai_metadata"]["source"] == "groq_llm"
            assert "solid financial profile" in plan["executive_summary"]
            assert len(plan["prioritized_actions"]) == 2
            assert plan["prioritized_actions"][0]["title"] == "Build Emergency Fund"

    asyncio.run(_test())


def test_generate_financial_plan_llm_fallback_on_error():
    async def _test():
        with patch(
            "backend.app.services.financial_planner.ask_llm_async",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Groq API rate limit or key error"),
        ):
            plan = await generate_financial_plan(
                context=MOCK_CONTEXT,
                user_id="U001",
                use_ai=True,
            )
            # Should gracefully fall back to deterministic rules without crashing
            assert plan["status"] == "SUCCESS"
            assert plan["ai_metadata"]["source"] == "deterministic_rules"
            assert len(plan["prioritized_actions"]) >= 3

    asyncio.run(_test())



def test_api_plan_endpoint():
    from unittest.mock import MagicMock
    from backend.main import app
    from backend.app.api.deps import get_current_user_id, get_neo4j_service

    client = TestClient(app)
    mock_db = MagicMock()
    mock_db.get_financial_context.return_value = MOCK_CONTEXT

    app.dependency_overrides[get_current_user_id] = lambda: "U001"
    app.dependency_overrides[get_neo4j_service] = lambda: mock_db

    try:
        resp = client.get("/api/finance/plan")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert "financial_summary" in data
        assert "budget_plan" in data
        assert "savings_plan" in data
        assert "prioritized_actions" in data
    finally:
        app.dependency_overrides.clear()
