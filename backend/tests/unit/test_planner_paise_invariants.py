"""
Unit tests asserting mathematical invariants of financial_planner using integer paise precision.
Tested against 'ugly cents' monetary values to verify exact category additivity,
reconciliation without float drift, and deterministic behavior.
"""

import pytest

from backend.app.core.money import to_paise
from backend.app.services.financial_planner import generate_financial_plan

CURR_MONTH = "2026-10"
PREV_MONTH = "2026-09"

UGLY_CENTS_PLANNER_CONTEXT = {
    "accounts": [{"id": "A201", "bank": "Test Bank", "account_type": "Savings", "balance": 12345.67}],
    "transactions": [
        # Previous month (2026-09)
        {"id": "T201", "description": "Swiggy Order", "amount": 33.33, "type": "EXPENSE", "category": "Food", "date": f"{PREV_MONTH}-10", "merchant": "Swiggy"},
        {"id": "T202", "description": "Micro debit 1", "amount": 0.10, "type": "EXPENSE", "category": "Utilities", "date": f"{PREV_MONTH}-12"},
        {"id": "T203", "description": "App Purchase", "amount": 999.99, "type": "EXPENSE", "category": "Shopping", "date": f"{PREV_MONTH}-15"},
        {"id": "T204", "description": "Rent Sept", "amount": 19999.99, "type": "EXPENSE", "category": "Housing", "date": f"{PREV_MONTH}-20"},
        # Current month (2026-10)
        {"id": "T205", "description": "Swiggy Order 1", "amount": 33.33, "type": "EXPENSE", "category": "Food", "date": f"{CURR_MONTH}-02", "merchant": "Swiggy"},
        {"id": "T206", "description": "Swiggy Order 2", "amount": 33.33, "type": "EXPENSE", "category": "Food", "date": f"{CURR_MONTH}-03", "merchant": "Swiggy"},
        {"id": "T207", "description": "Swiggy Order 3", "amount": 33.33, "type": "EXPENSE", "category": "Food", "date": f"{CURR_MONTH}-04", "merchant": "Swiggy"},
        {"id": "T208", "description": "Micro debit 2", "amount": 0.20, "type": "EXPENSE", "category": "Utilities", "date": f"{CURR_MONTH}-05"},
        {"id": "T209", "description": "Grocery Mart", "amount": 1234.56, "type": "EXPENSE", "category": "Food", "date": f"{CURR_MONTH}-06"},
        {"id": "T210", "description": "Electronics Buy", "amount": 999.99, "type": "EXPENSE", "category": "Shopping", "date": f"{CURR_MONTH}-08"},
        {"id": "T211", "description": "Rent Oct", "amount": 19999.99, "type": "EXPENSE", "category": "Housing", "date": f"{CURR_MONTH}-10"},
        {"id": "T212", "description": "Netflix Subscription", "amount": 649.00, "type": "EXPENSE", "category": "Utilities", "date": f"{CURR_MONTH}-15"},
        {"id": "T213", "description": "Spotify Premium", "amount": 119.00, "type": "EXPENSE", "category": "Utilities", "date": f"{CURR_MONTH}-18"},
    ],
    "incomes": [
        {"id": "I201", "source": "Consulting Sept", "amount": 54321.09, "date": f"{PREV_MONTH}-01"},
        {"id": "I202", "source": "Consulting Oct", "amount": 54321.09, "date": f"{CURR_MONTH}-01"},
    ],
    "loans": [
        {
            "id": "L201",
            "name": "Education Loan",
            "principal": 98765.43,
            "outstanding": 54321.12,
            "emi": 4321.09,
            "due_date": f"{CURR_MONTH}-15",
            "status": "PENDING",
        }
    ],
    "goals": [
        {
            "id": "G201",
            "name": "Emergency Fund",
            "target_amount": 100000.0,
            "current_amount": 12345.67,
            "target_date": "2027-03-01",
            "current": 12345.67,
            "target": 100000.0,
        }
    ],
}


@pytest.mark.anyio
async def test_invariant_1_category_reconciliation_exact_paise():
    """Invariant 1: For each category, recommended_limit + potential_savings == current_spending exactly."""
    plan = await generate_financial_plan(UGLY_CENTS_PLANNER_CONTEXT, use_ai=False)
    categories = plan["budget_plan"]["categories"]

    for cat in categories:
        limit_p = to_paise(cat["recommended_limit"])
        pot_p = to_paise(cat["potential_savings"])
        spent_p = to_paise(cat["current_spending"])
        assert limit_p + pot_p == spent_p, (
            f"Category {cat['category']} failed reconciliation: {limit_p} + {pot_p} != {spent_p}"
        )


@pytest.mark.anyio
async def test_invariant_2_total_budget_equals_category_sum_exact_paise():
    """Invariant 2: recommended_total_budget equals the sum of category recommended limits exactly."""
    plan = await generate_financial_plan(UGLY_CENTS_PLANNER_CONTEXT, use_ai=False)
    bp = plan["budget_plan"]

    total_rec_p = to_paise(bp["recommended_total_budget"])
    sum_category_limits_p = sum(to_paise(c["recommended_limit"]) for c in bp["categories"])

    assert total_rec_p == sum_category_limits_p, (
        f"Recommended total budget mismatch: {total_rec_p} != {sum_category_limits_p}"
    )


@pytest.mark.anyio
async def test_invariant_3_total_potential_savings_reconciliation_exact_paise():
    """Invariant 3: total_potential_savings equals current_total_expenses minus recommended_total_budget."""
    plan = await generate_financial_plan(UGLY_CENTS_PLANNER_CONTEXT, use_ai=False)
    bp = plan["budget_plan"]

    pot_savings_p = to_paise(bp["total_potential_savings"])
    current_exp_p = to_paise(bp["current_total_expenses"])
    rec_budget_p = to_paise(bp["recommended_total_budget"])

    assert pot_savings_p == current_exp_p - rec_budget_p, (
        f"Potential savings mismatch: {pot_savings_p} != {current_exp_p} - {rec_budget_p}"
    )


@pytest.mark.anyio
async def test_invariant_4_recurring_commitments_exact_sum_paise():
    """Invariant 4: Recurring commitments total equals the sum of items exactly in paise."""
    plan = await generate_financial_plan(UGLY_CENTS_PLANNER_CONTEXT, use_ai=False)
    debt = plan["debt_and_commitments"]

    total_rec_p = to_paise(debt["total_recurring_monthly"])
    sum_items_p = sum(to_paise(r["amount"]) for r in debt["recurring_commitments"])

    assert total_rec_p == sum_items_p, (
        f"Recurring commitments total mismatch: {total_rec_p} != {sum_items_p}"
    )


@pytest.mark.anyio
async def test_invariant_5_plan_determinism():
    """Invariant 5: Same input run twice produces identical outputs across all calculated fields."""
    p1 = await generate_financial_plan(UGLY_CENTS_PLANNER_CONTEXT, use_ai=False)
    p2 = await generate_financial_plan(UGLY_CENTS_PLANNER_CONTEXT, use_ai=False)

    # Normalize volatile timestamp
    p1["generated_at"] = "FIXED"
    p2["generated_at"] = "FIXED"

    assert p1 == p2
