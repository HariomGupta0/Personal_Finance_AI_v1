"""
Unit tests for backend/app/engine/financial_engine.py

These tests use pure Python dicts as mock context — NO Neo4j connection,
NO Groq API calls, NO network. Suitable for CI with zero live dependencies.

Run with:
    pytest backend/tests/unit/test_financial_engine.py -v
    pytest backend/tests/unit/ -v --cov=backend/app/engine --cov-report=term-missing
"""
from datetime import date
import pytest

from backend.app.engine.financial_engine import (
    calculate_savings_rate,
    calculate_emergency_fund,
    calculate_emergency_runway,
    calculate_debt_burden,
    calculate_comprehensive_health,
    calculate_category_expenses,
    check_purchase_safety,
    _resolve_reporting_date,
    _is_in_reporting_month,
)

# ─────────────────────────────────────────────────────────────────────────────
# Shared mock context — represents Rahul's seeded demo data
# All dates use the current month so _resolve_reporting_date works correctly
# without needing to override the system clock.
# ─────────────────────────────────────────────────────────────────────────────
_TODAY = date.today()
_YM = f"{_TODAY.year}-{_TODAY.month:02d}"

MOCK_CONTEXT = {
    "accounts": [{"id": "A001", "balance": 45000}],
    "transactions": [
        {"type": "EXPENSE", "amount": 12000, "category": "Housing",   "date": f"{_YM}-05"},
        {"type": "EXPENSE", "amount": 4000,  "category": "Food",      "date": f"{_YM}-07"},
        {"type": "EXPENSE", "amount": 2000,  "category": "Transport", "date": f"{_YM}-08"},
        {"type": "EXPENSE", "amount": 3000,  "category": "Utilities", "date": f"{_YM}-09"},
    ],
    "incomes": [
        {"amount": 60000, "source": "Salary", "date": f"{_YM}-01"},
    ],
    "loans": [
        {
            "id": "L001",
            "outstanding": 150000,
            "emi": 10000,
            "status": "PENDING",
            "due_date": f"{_YM}-10",
        }
    ],
    "goals": [
        {"name": "Emergency Fund", "current": 30000, "target": 100000},
    ],
}

ZERO_INCOME_CONTEXT = {**MOCK_CONTEXT, "incomes": []}
ZERO_EXPENSE_CONTEXT = {**MOCK_CONTEXT, "transactions": []}
ZERO_BALANCE_CONTEXT = {**MOCK_CONTEXT, "accounts": [{"balance": 0}]}
NO_LOANS_CONTEXT = {**MOCK_CONTEXT, "loans": []}
NO_GOALS_CONTEXT = {**MOCK_CONTEXT, "goals": []}


# ─────────────────────────────────────────────────────────────────────────────
# _resolve_reporting_date
# ─────────────────────────────────────────────────────────────────────────────
class TestResolveReportingDate:
    def test_explicit_date_is_returned_unchanged(self):
        fixed = date(2025, 6, 15)
        assert _resolve_reporting_date(MOCK_CONTEXT, fixed) == fixed

    def test_no_dates_in_context_returns_today(self):
        result = _resolve_reporting_date({"transactions": [], "incomes": []})
        assert result == date.today()

    def test_current_month_data_returns_today(self):
        result = _resolve_reporting_date(MOCK_CONTEXT)
        assert result == date.today()

    def test_non_dict_context_returns_today(self):
        assert _resolve_reporting_date(None) == date.today()
        assert _resolve_reporting_date([]) == date.today()


# ─────────────────────────────────────────────────────────────────────────────
# _is_in_reporting_month
# ─────────────────────────────────────────────────────────────────────────────
class TestIsInReportingMonth:
    def test_matching_month(self):
        assert _is_in_reporting_month({"date": f"{_YM}-15"}, _TODAY) is True

    def test_different_month(self):
        assert _is_in_reporting_month({"date": "2000-01-15"}, _TODAY) is False

    def test_missing_date_returns_false(self):
        assert _is_in_reporting_month({}) is False
        assert _is_in_reporting_month({"date": None}) is False

    def test_invalid_date_string_returns_false(self):
        assert _is_in_reporting_month({"date": "not-a-date"}) is False

    def test_date_object_works(self):
        assert _is_in_reporting_month({"date": _TODAY}, _TODAY) is True


# ─────────────────────────────────────────────────────────────────────────────
# calculate_savings_rate
# ─────────────────────────────────────────────────────────────────────────────
class TestCalculateSavingsRate:
    def test_correct_totals(self):
        r = calculate_savings_rate(MOCK_CONTEXT)
        assert r["total_income"] == 60000
        assert r["total_expenses"] == 21000
        assert r["savings"] == 39000

    def test_savings_rate_formula(self):
        r = calculate_savings_rate(MOCK_CONTEXT)
        # (39000 / 60000) * 100 = 65.0%
        assert r["savings_rate"] == pytest.approx(65.0, abs=0.01)

    def test_zero_income_returns_zero_rate(self):
        r = calculate_savings_rate(ZERO_INCOME_CONTEXT)
        assert r["total_income"] == 0
        assert r["savings_rate"] == 0.0

    def test_zero_expenses(self):
        r = calculate_savings_rate(ZERO_EXPENSE_CONTEXT)
        assert r["total_expenses"] == 0
        assert r["savings"] == r["total_income"]
        assert r["savings_rate"] == pytest.approx(100.0, abs=0.01)

    def test_result_has_required_keys(self):
        r = calculate_savings_rate(MOCK_CONTEXT)
        assert all(k in r for k in ("total_income", "total_expenses", "savings", "savings_rate"))


# ─────────────────────────────────────────────────────────────────────────────
# calculate_emergency_fund
# ─────────────────────────────────────────────────────────────────────────────
class TestCalculateEmergencyFund:
    def test_recommended_fund_is_3x_monthly_expenses(self):
        r = calculate_emergency_fund(MOCK_CONTEXT)
        assert r["recommended_fund"] == r["monthly_expenses"] * 3

    def test_shortfall_is_non_negative(self):
        r = calculate_emergency_fund(MOCK_CONTEXT)
        assert r["shortfall"] >= 0

    def test_correct_shortfall(self):
        r = calculate_emergency_fund(MOCK_CONTEXT)
        # monthly_expenses=21000, recommended=63000, current_fund=30000, shortfall=33000
        assert r["monthly_expenses"] == 21000
        assert r["recommended_fund"] == 63000
        assert r["current_fund"] == 30000
        assert r["shortfall"] == 33000

    def test_no_goals_gives_zero_current_fund(self):
        r = calculate_emergency_fund(NO_GOALS_CONTEXT)
        assert r["current_fund"] == 0
        assert r["shortfall"] == r["recommended_fund"]

    def test_zero_expenses_gives_zero_shortfall(self):
        r = calculate_emergency_fund(ZERO_EXPENSE_CONTEXT)
        assert r["monthly_expenses"] == 0
        assert r["recommended_fund"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# calculate_emergency_runway
# ─────────────────────────────────────────────────────────────────────────────
class TestCalculateEmergencyRunway:
    def test_runway_calculation(self):
        r = calculate_emergency_runway(MOCK_CONTEXT)
        # balance=45000, monthly_expenses=21000 → 45000/21000 ≈ 2.14
        assert r["runway_months"] == pytest.approx(2.14, abs=0.01)

    def test_runway_status_insufficient(self):
        r = calculate_emergency_runway(MOCK_CONTEXT)
        assert r["status"] == "INSUFFICIENT"

    def test_strong_runway(self):
        ctx = {**MOCK_CONTEXT, "accounts": [{"balance": 200000}]}
        r = calculate_emergency_runway(ctx)
        assert r["status"] == "STRONG"
        assert r["runway_months"] >= 6.0

    def test_healthy_runway(self):
        ctx = {**MOCK_CONTEXT, "accounts": [{"balance": 80000}]}
        r = calculate_emergency_runway(ctx)
        assert r["status"] == "HEALTHY"

    def test_critical_runway(self):
        ctx = {**MOCK_CONTEXT, "accounts": [{"balance": 5000}]}
        r = calculate_emergency_runway(ctx)
        assert r["status"] == "CRITICAL"

    def test_zero_expenses_returns_12_months(self):
        r = calculate_emergency_runway(ZERO_EXPENSE_CONTEXT)
        assert r["runway_months"] == 12.0
        assert r["status"] == "STRONG"

    def test_zero_balance_returns_critical(self):
        r = calculate_emergency_runway(ZERO_BALANCE_CONTEXT)
        assert r["status"] == "CRITICAL"
        assert r["runway_months"] == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# calculate_debt_burden
# ─────────────────────────────────────────────────────────────────────────────
class TestCalculateDebtBurden:
    def test_total_outstanding_debt(self):
        r = calculate_debt_burden(MOCK_CONTEXT)
        assert r["total_outstanding_debt"] == 150000

    def test_monthly_emi(self):
        r = calculate_debt_burden(MOCK_CONTEXT)
        assert r["monthly_emi"] == 10000

    def test_dti_ratio(self):
        r = calculate_debt_burden(MOCK_CONTEXT)
        # (10000 / 60000) * 100 = 16.67%
        assert r["dti_ratio"] == pytest.approx(16.67, abs=0.01)

    def test_low_risk_classification(self):
        r = calculate_debt_burden(MOCK_CONTEXT)
        assert r["risk_level"] == "LOW"

    def test_high_dti_gives_high_risk(self):
        # EMI = 25000 on income 60000 → DTI ≈ 41.67% → HIGH
        ctx = {
            **MOCK_CONTEXT,
            "loans": [{"outstanding": 500000, "emi": 25000, "status": "PENDING", "due_date": f"{_YM}-10"}],
        }
        r = calculate_debt_burden(ctx)
        assert r["risk_level"] == "HIGH"

    def test_critical_dti(self):
        # EMI = 40000 on income 60000 → DTI ≈ 66.7% → CRITICAL
        ctx = {
            **MOCK_CONTEXT,
            "loans": [{"outstanding": 800000, "emi": 40000, "status": "PENDING", "due_date": f"{_YM}-10"}],
        }
        r = calculate_debt_burden(ctx)
        assert r["risk_level"] == "CRITICAL"

    def test_no_loans_gives_zero_dti(self):
        r = calculate_debt_burden(NO_LOANS_CONTEXT)
        assert r["dti_ratio"] == 0.0
        assert r["monthly_emi"] == 0
        assert r["risk_level"] == "LOW"

    def test_zero_income_gives_zero_dti(self):
        r = calculate_debt_burden(ZERO_INCOME_CONTEXT)
        assert r["dti_ratio"] == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# check_purchase_safety
# ─────────────────────────────────────────────────────────────────────────────
class TestCheckPurchaseSafety:
    def test_large_purchase_is_not_safe(self):
        # Spending ₹50,000: balance=45000, pending_emi=10000, purchase=50000
        # balance_after = 45000 - 10000 - 50000 = -15000 → NOT_SAFE
        r = check_purchase_safety(MOCK_CONTEXT, purchase_amount=50000)
        assert r["decision"] == "NOT_SAFE"

    def test_not_safe_has_very_high_risk(self):
        r = check_purchase_safety(MOCK_CONTEXT, purchase_amount=50000)
        assert r["risk_level"] == "VERY_HIGH"

    def test_tiny_purchase_is_safe(self):
        # balance=45000, emi=10000, purchase=100
        # balance_after = 34900; emergency_req = 21000*3 = 63000 → NOT_SAFE
        # (balance_after < emergency_req, so still not safe in this demo context)
        # Use a context with high balance to test SAFE path
        rich_ctx = {**MOCK_CONTEXT, "accounts": [{"balance": 200000}]}
        r = check_purchase_safety(rich_ctx, purchase_amount=100)
        assert r["decision"] == "SAFE"
        assert r["risk_level"] == "LOW"

    def test_evidence_contains_required_keys(self):
        r = check_purchase_safety(MOCK_CONTEXT, purchase_amount=1000)
        ev = r["evidence"]
        for key in ("current_balance", "pending_emi", "monthly_expenses",
                    "purchase_amount", "emergency_requirement", "balance_after_purchase"):
            assert key in ev

    def test_balance_after_purchase_math(self):
        r = check_purchase_safety(MOCK_CONTEXT, purchase_amount=5000)
        ev = r["evidence"]
        expected = ev["current_balance"] - ev["pending_emi"] - ev["purchase_amount"]
        assert ev["balance_after_purchase"] == pytest.approx(expected, abs=0.01)

    def test_zero_purchase_amount(self):
        r = check_purchase_safety(MOCK_CONTEXT, purchase_amount=0)
        assert r["decision"] in ("SAFE", "NOT_SAFE")  # Structurally valid

    def test_risk_level_is_valid_enum(self):
        for amount in [100, 5000, 20000, 80000]:
            r = check_purchase_safety(MOCK_CONTEXT, purchase_amount=amount)
            assert r["risk_level"] in ("LOW", "MEDIUM", "HIGH", "VERY_HIGH")


# ─────────────────────────────────────────────────────────────────────────────
# calculate_category_expenses
# ─────────────────────────────────────────────────────────────────────────────
class TestCalculateCategoryExpenses:
    def test_top_category_is_housing(self):
        r = calculate_category_expenses(MOCK_CONTEXT)
        assert r["top_category"] == "Housing"

    def test_total_expenses_sum(self):
        r = calculate_category_expenses(MOCK_CONTEXT)
        assert r["total_expenses"] == pytest.approx(21000, abs=0.01)

    def test_categories_sorted_descending(self):
        r = calculate_category_expenses(MOCK_CONTEXT)
        amounts = [c["amount"] for c in r["categories"]]
        assert amounts == sorted(amounts, reverse=True)

    def test_percentage_sums_to_100(self):
        r = calculate_category_expenses(MOCK_CONTEXT)
        total_pct = sum(c["percentage"] for c in r["categories"])
        assert total_pct == pytest.approx(100.0, abs=0.1)

    def test_no_transactions_returns_empty(self):
        r = calculate_category_expenses(ZERO_EXPENSE_CONTEXT)
        assert r["total_expenses"] == 0
        assert r["categories"] == []
        assert r["top_category"] == "None"


# ─────────────────────────────────────────────────────────────────────────────
# calculate_comprehensive_health
# ─────────────────────────────────────────────────────────────────────────────
class TestCalculateComprehensiveHealth:
    def test_score_is_in_valid_range(self):
        r = calculate_comprehensive_health(MOCK_CONTEXT)
        assert 0.0 <= r["health_score"] <= 100.0

    def test_grade_is_valid(self):
        r = calculate_comprehensive_health(MOCK_CONTEXT)
        assert r["grade"] in ("A", "B", "C", "D")

    def test_required_keys_present(self):
        r = calculate_comprehensive_health(MOCK_CONTEXT)
        for k in ("health_score", "grade", "summary", "savings_rate", "runway_months", "dti_ratio"):
            assert k in r

    def test_excellent_finances_give_high_score(self):
        ctx = {
            **MOCK_CONTEXT,
            "accounts": [{"balance": 500000}],
            "loans": [],
        }
        r = calculate_comprehensive_health(ctx)
        assert r["health_score"] >= 85.0
        assert r["grade"] == "A"

    def test_zero_income_zero_balance_gives_low_score(self):
        ctx = {**ZERO_INCOME_CONTEXT, "accounts": [{"balance": 0}]}
        r = calculate_comprehensive_health(ctx)
        assert r["grade"] in ("C", "D")
