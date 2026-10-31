"""
Script to generate engine_baseline.json by executing public functions
in financial_engine.py and financial_planner.py with fixed, hard-coded fixtures.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

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
from backend.app.services.financial_planner import generate_financial_plan

# Fixed dates ensure baseline does not drift across calendar months
FIXED_DATE = "2026-10-15"
PREV_MONTH = "2026-09"
CURR_MONTH = "2026-10"

FIXTURE_1_DEMO = {
    "accounts": [{"id": "A001", "bank": "Demo Bank", "account_type": "Savings", "balance": 45000.0}],
    "transactions": [
        {"id": "T001", "description": "Monthly Rent", "amount": 12000.0, "type": "EXPENSE", "category": "Housing", "date": f"{CURR_MONTH}-05"},
        {"id": "T002", "description": "Grocery Shopping", "amount": 4000.0, "type": "EXPENSE", "category": "Food", "date": f"{CURR_MONTH}-07"},
        {"id": "T003", "description": "Bus/Auto Travel", "amount": 2000.0, "type": "EXPENSE", "category": "Transport", "date": f"{CURR_MONTH}-08"},
        {"id": "T004", "description": "Electricity Bill", "amount": 3000.0, "type": "EXPENSE", "category": "Utilities", "date": f"{CURR_MONTH}-09"},
    ],
    "incomes": [
        {"id": "I001", "source": "Salary", "amount": 60000.0, "date": f"{CURR_MONTH}-01"},
    ],
    "loans": [
        {
            "id": "L001",
            "name": "Personal Loan",
            "principal": 200000.0,
            "outstanding": 150000.0,
            "emi": 10000.0,
            "due_date": f"{CURR_MONTH}-10",
            "status": "PENDING",
        }
    ],
    "goals": [
        {
            "id": "G001",
            "name": "Emergency Fund",
            "target_amount": 100000.0,
            "current_amount": 30000.0,
            "target_date": "2027-03-01",
            "current": 30000.0,
            "target": 100000.0,
        }
    ],
    "purchase_amount": 15000.0,
}

FIXTURE_2_UGLY_CENTS = {
    "accounts": [{"id": "A002", "bank": "Test Bank", "account_type": "Savings", "balance": 12345.67}],
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
            "outstanding": 87654.32,
            "emi": 4321.09,
            "due_date": f"{CURR_MONTH}-12",
            "status": "PENDING",
        }
    ],
    "goals": [
        {
            "id": "G201",
            "name": "Emergency Fund",
            "target_amount": 50000.0,
            "current_amount": 1234.56,
            "target_date": "2027-01-01",
            "current": 1234.56,
            "target": 50000.0,
        }
    ],
    "purchase_amount": 1234.56,
}

FIXTURE_3_EDGE_CASES = {
    "accounts": [{"id": "A003", "bank": "Overdraft Bank", "account_type": "Current", "balance": -5000.0}],
    "transactions": [],
    "incomes": [],
    "loans": [],
    "goals": [],
    "purchase_amount": 1000.0,
}

FIXTURES = {
    "fixture_1_demo": FIXTURE_1_DEMO,
    "fixture_2_ugly_cents": FIXTURE_2_UGLY_CENTS,
    "fixture_3_edge_cases": FIXTURE_3_EDGE_CASES,
}


def run_all_functions(fixture: dict[str, Any]) -> dict[str, Any]:
    context = {
        "accounts": fixture.get("accounts", []),
        "transactions": fixture.get("transactions", []),
        "incomes": fixture.get("incomes", []),
        "loans": fixture.get("loans", []),
        "goals": fixture.get("goals", []),
    }
    purchase_amt = fixture.get("purchase_amount", 1000.0)

    plan = asyncio.run(
        generate_financial_plan(
            context=context,
            user_id="U001",
            force_refresh=True,
            use_ai=False,
        )
    )
    # Normalize runtime wall-clock timestamp for reproducible golden comparisons
    if isinstance(plan, dict) and "generated_at" in plan:
        plan["generated_at"] = "2026-10-15T10:00:00.000000"

    return {
        "savings_rate": calculate_savings_rate(context, reporting_date=FIXED_DATE),
        "emergency_fund": calculate_emergency_fund(context, reporting_date=FIXED_DATE),
        "emergency_runway": calculate_emergency_runway(context, reporting_date=FIXED_DATE),
        "debt_burden": calculate_debt_burden(context, reporting_date=FIXED_DATE),
        "purchase_safety": check_purchase_safety(context, purchase_amount=purchase_amt, reporting_date=FIXED_DATE),
        "category_expenses": calculate_category_expenses(context, reporting_date=FIXED_DATE),
        "merchant_expenses_swiggy": calculate_merchant_expenses(context, merchant_name="Swiggy", reporting_date=FIXED_DATE),
        "top_transactions": calculate_top_transactions(context, limit=5, reporting_date=FIXED_DATE),
        "period_comparison": calculate_period_comparison(
            context,
            period_a_start=f"{PREV_MONTH}-01",
            period_a_end=f"{PREV_MONTH}-30",
            period_b_start=f"{CURR_MONTH}-01",
            period_b_end=f"{CURR_MONTH}-31",
            first_mentioned="Sep 2026",
            second_mentioned="Oct 2026",
        ),
        "spending_trends": calculate_spending_trends(context, num_months=6, end_date=FIXED_DATE),
        "comprehensive_health": calculate_comprehensive_health(context, reporting_date=FIXED_DATE),
        "financial_summary": generate_financial_summary(context, reporting_date=FIXED_DATE),
        "financial_plan": plan,
    }


def make_golden_baseline(output_path: Path | None = None) -> Path:
    if output_path is None:
        output_path = Path(__file__).resolve().parent / "engine_baseline.json"

    baseline: dict[str, Any] = {}
    for name, fixture in FIXTURES.items():
        baseline[name] = run_all_functions(fixture)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(baseline, f, indent=2, sort_keys=True)

    return output_path


if __name__ == "__main__":
    out = make_golden_baseline()
    print(f"Wrote golden baseline to {out}")
