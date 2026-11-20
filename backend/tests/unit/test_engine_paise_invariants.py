"""
Unit tests asserting mathematical invariants of financial_engine using integer paise precision.
Ensures zero balance drift, exact additivity, exact multi-operand arithmetic, and determinism.
"""

from decimal import Decimal
import pytest

from backend.app.core.money import to_paise
from backend.app.engine.financial_engine import (
    calculate_category_expenses,
    calculate_comprehensive_health,
    calculate_debt_burden,
    calculate_emergency_fund,
    calculate_emergency_runway,
    calculate_merchant_expenses,
    calculate_period_comparison,
    calculate_savings_rate,
    calculate_spending_trends,
    calculate_top_transactions,
    check_purchase_safety,
    generate_financial_summary,
)

CURR_MONTH = "2026-10"
PREV_MONTH = "2026-09"

UGLY_CENTS_CONTEXT = {
    "accounts": [{"id": "A001", "bank": "Test Bank", "balance": 12345.67}],
    "transactions": [
        {"id": "T001", "description": "Swiggy Order 1", "amount": 33.33, "type": "EXPENSE", "category": "Food", "date": f"{CURR_MONTH}-02", "merchant": "Swiggy"},
        {"id": "T002", "description": "Swiggy Order 2", "amount": 33.33, "type": "EXPENSE", "category": "Food", "date": f"{CURR_MONTH}-03", "merchant": "Swiggy"},
        {"id": "T003", "description": "Swiggy Order 3", "amount": 33.33, "type": "EXPENSE", "category": "Food", "date": f"{CURR_MONTH}-04", "merchant": "Swiggy"},
        {"id": "T004", "description": "Micro debit 2", "amount": 0.20, "type": "EXPENSE", "category": "Utilities", "date": f"{CURR_MONTH}-05"},
        {"id": "T005", "description": "Grocery Mart", "amount": 1234.56, "type": "EXPENSE", "category": "Food", "date": f"{CURR_MONTH}-06"},
        {"id": "T006", "description": "Electronics Buy", "amount": 999.99, "type": "EXPENSE", "category": "Shopping", "date": f"{CURR_MONTH}-08"},
        {"id": "T007", "description": "Rent Oct", "amount": 19999.99, "type": "EXPENSE", "category": "Housing", "date": f"{CURR_MONTH}-10"},
        {"id": "T008", "description": "App Sept", "amount": 999.99, "type": "EXPENSE", "category": "Shopping", "date": f"{PREV_MONTH}-15"},
    ],
    "incomes": [
        {"id": "I001", "source": "Consulting Oct", "amount": 54321.09, "date": f"{CURR_MONTH}-01"},
    ],
    "loans": [
        {
            "id": "L001",
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
            "id": "G001",
            "name": "Emergency Fund",
            "target_amount": 100000.0,
            "current_amount": 12345.67,
            "current": 12345.67,
        }
    ],
}


def test_invariant_1_category_expenses_sum_exact_paise():
    """Invariant 1: Category amounts sum exactly to total_expenses in integer paise."""
    res = calculate_category_expenses(UGLY_CENTS_CONTEXT, reporting_date=f"{CURR_MONTH}-15")
    total_paise = to_paise(res["total_expenses"])
    categories_sum_paise = sum(to_paise(c["amount"]) for c in res["categories"])
    assert total_paise == categories_sum_paise
    # 33.33 * 3 + 0.20 + 1234.56 + 999.99 + 19999.99 = 22334.73
    assert total_paise == 2233473


def test_invariant_2_savings_rate_exact_paise_balance():
    """Invariant 2: Net savings = income - expenses holds with exact paise precision."""
    res = calculate_savings_rate(UGLY_CENTS_CONTEXT, reporting_date=f"{CURR_MONTH}-15")
    income_paise = to_paise(res["total_income"])
    expenses_paise = to_paise(res["total_expenses"])
    savings_paise = to_paise(res["savings"])
    assert savings_paise == income_paise - expenses_paise
    # 54321.09 - 22334.73 = 31986.36
    assert income_paise == 5432109
    assert expenses_paise == 2233473
    assert savings_paise == 3198636


def test_invariant_3_emergency_fund_triple_exact():
    """Invariant 3: recommended_fund == 3 * monthly_expenses holds exactly in paise."""
    res = calculate_emergency_fund(UGLY_CENTS_CONTEXT, reporting_date=f"{CURR_MONTH}-15")
    expenses_paise = to_paise(res["monthly_expenses"])
    recommended_paise = to_paise(res["recommended_fund"])
    assert recommended_paise == expenses_paise * 3
    shortfall_paise = to_paise(res["shortfall"])
    current_paise = to_paise(res["current_fund"])
    assert shortfall_paise == max(0, recommended_paise - current_paise)


def test_invariant_4_purchase_safety_exact_deduction():
    """Invariant 4: balance_after_purchase == balance - pending_emi - purchase exactly."""
    purchase_amount = 1234.56
    res = check_purchase_safety(
        UGLY_CENTS_CONTEXT,
        purchase_amount=purchase_amount,
        reporting_date=f"{CURR_MONTH}-15",
    )
    ev = res["evidence"]
    bal_paise = to_paise(ev["current_balance"])
    emi_paise = to_paise(ev["pending_emi"])
    purch_paise = to_paise(ev["purchase_amount"])
    after_paise = to_paise(ev["balance_after_purchase"])
    assert after_paise == bal_paise - emi_paise - purch_paise
    # 12345.67 - 4321.09 - 1234.56 = 6790.02
    assert after_paise == 679002


def test_invariant_5_deterministic_executions():
    """Invariant 5: Same input run twice produces byte-identical dict outputs."""
    r1_summary = generate_financial_summary(UGLY_CENTS_CONTEXT, reporting_date=f"{CURR_MONTH}-15")
    r2_summary = generate_financial_summary(UGLY_CENTS_CONTEXT, reporting_date=f"{CURR_MONTH}-15")
    assert r1_summary == r2_summary

    r1_safety = check_purchase_safety(UGLY_CENTS_CONTEXT, 1234.56, reporting_date=f"{CURR_MONTH}-15")
    r2_safety = check_purchase_safety(UGLY_CENTS_CONTEXT, 1234.56, reporting_date=f"{CURR_MONTH}-15")
    assert r1_safety == r2_safety

    r1_period = calculate_period_comparison(UGLY_CENTS_CONTEXT)
    r2_period = calculate_period_comparison(UGLY_CENTS_CONTEXT)
    assert r1_period == r2_period

    r1_trend = calculate_spending_trends(UGLY_CENTS_CONTEXT, num_months=3)
    r2_trend = calculate_spending_trends(UGLY_CENTS_CONTEXT, num_months=3)
    assert r1_trend == r2_trend

