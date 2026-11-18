"""
Unit tests for Deterministic Historical Runway Engine (Task 2 — Phase 2A).

Tests all 12+ scenarios from the approved Task 2 specification:
1. Hard gate: 0 complete months returns INSUFFICIENT_DATA
2. Hard gate: 1 complete month ceiling is LOW
3. Hard gate: 2 complete months ceiling is MEDIUM
4. HIGH confidence requires >= 3 months, low CV, high volume
5. Missing month gap does not dilute divisor (burn divisor is |H|, not N)
6. Incomplete current month is strictly excluded from historical baseline
7. Internal transfers excluded from expenses
8. Irregular essential not amortized into monthly burn, but reserved in emergency target
9. Ambiguous / unclassified expenses excluded from core essential burn
10. Zero / negative balance returns runway 0.0 and CRITICAL status
11. Legacy imports without coverage nodes evaluate as provisional data
12. Seed U001 benchmark Q4 runway calculation (runway_months ~ 2.14)
13. MTD gap detection (e.g. Nov 1-2 and Nov 4-5 produces PARTIAL_MTD_COVERAGE with Nov 2 reach)
14. Empty spending account set yields NO_SPENDING_ACCOUNTS (vacuous truth prevention)
15. Account lifecycle mid-month opening/closure disqualifies that month
"""
from datetime import date
import pytest

from backend.app.engine.historical_runway import (
    AccountLifecycle,
    ConfidenceTier,
    ExpenseTier,
    MonthEligibility,
    MTDCoverageStatus,
    RunwayStatus,
    StatementCoverageStatus,
    calculate_historical_runway,
    classify_expense,
    compute_continuous_interval_union,
    evaluate_mtd_coverage,
    get_account_month_lifecycle,
)


# ---------------------------------------------------------------------------
# Fixtures and Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def base_account():
    return {
        "id": "ACC001",
        "type": "SAVINGS",
        "balance": 100000,
        "balance_paise": 10000000,
        "opened_date": "2025-01-01",
        "status": "ACTIVE",
    }


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

class TestAccountLifecycleAndCoverage:
    def test_active_full_month(self, base_account):
        lifecycle = get_account_month_lifecycle(base_account, date(2026, 8, 1), date(2026, 8, 31))
        assert lifecycle == AccountLifecycle.ACTIVE_FULL_MONTH

    def test_mid_month_opening_disqualifies(self):
        acct = {
            "id": "ACC002",
            "type": "CHECKING",
            "opened_date": "2026-08-15",
            "status": "ACTIVE",
        }
        lifecycle = get_account_month_lifecycle(acct, date(2026, 8, 1), date(2026, 8, 31))
        assert lifecycle == AccountLifecycle.PARTIAL_LIFECYCLE

    def test_mid_month_closure_disqualifies(self):
        acct = {
            "id": "ACC003",
            "type": "CHECKING",
            "opened_date": "2025-01-01",
            "closed_date": "2026-08-20",
            "status": "ACTIVE",
        }
        lifecycle = get_account_month_lifecycle(acct, date(2026, 8, 1), date(2026, 8, 31))
        assert lifecycle == AccountLifecycle.PARTIAL_LIFECYCLE

    def test_unopened_account_is_not_active(self):
        acct = {
            "id": "ACC004",
            "type": "CHECKING",
            "opened_date": "2026-10-01",
            "status": "ACTIVE",
        }
        lifecycle = get_account_month_lifecycle(acct, date(2026, 8, 1), date(2026, 8, 31))
        assert lifecycle == AccountLifecycle.NOT_ACTIVE

    def test_unknown_lifecycle_when_opened_date_is_null_and_no_coverage(self):
        acct = {
            "id": "ACC005",
            "type": "CHECKING",
            "opened_date": None,
            "status": "ACTIVE",
        }
        lifecycle = get_account_month_lifecycle(acct, date(2026, 8, 1), date(2026, 8, 31))
        assert lifecycle == AccountLifecycle.UNKNOWN_LIFECYCLE


class TestMTDIntervalContinuity:
    def test_mtd_gap_detection_partial(self, base_account):
        # Statement 1: Nov 1 - Nov 2
        # Statement 2: Nov 4 - Nov 5 (Nov 3 missing)
        intervals = {
            "ACC001": [
                (date(2026, 11, 1), date(2026, 11, 2)),
                (date(2026, 11, 4), date(2026, 11, 5)),
            ]
        }
        res = evaluate_mtd_coverage([base_account], intervals, date(2026, 11, 5))
        assert res["status"] == MTDCoverageStatus.PARTIAL_MTD_COVERAGE
        assert res["effective_through_date"] == date(2026, 11, 2)
        assert res["is_complete_mtd"] is False

    def test_mtd_complete_coverage(self, base_account):
        intervals = {
            "ACC001": [
                (date(2026, 11, 1), date(2026, 11, 5)),
            ]
        }
        res = evaluate_mtd_coverage([base_account], intervals, date(2026, 11, 5))
        assert res["status"] == MTDCoverageStatus.VERIFIED_COMPLETE_MTD
        assert res["effective_through_date"] == date(2026, 11, 5)
        assert res["is_complete_mtd"] is True

    def test_mtd_empty_spending_accounts_prevents_vacuous_truth(self):
        res = evaluate_mtd_coverage([], {}, date(2026, 11, 5))
        assert res["status"] == MTDCoverageStatus.NO_SPENDING_ACCOUNTS
        assert res["is_complete_mtd"] is False
        assert res["effective_through_date"] is None


class TestExpenseClassification:
    def test_transfer_is_strictly_excluded(self):
        tx = {
            "type": "EXPENSE",
            "amount": 5000,
            "is_transfer": True,
            "category": "Rent",
        }
        assert classify_expense(tx) == ExpenseTier.TRANSFER_EXCLUDED

    def test_explicit_commute_metadata(self):
        tx = {
            "type": "EXPENSE",
            "amount": 2000,
            "category": "Transport",
            "essential_subtype": "COMMUTE",
            "narration": "Monthly Metro Commute Pass",
        }
        assert classify_expense(tx) == ExpenseTier.RECURRING_ESSENTIAL

    def test_ambiguous_transport_is_unclassified(self):
        tx = {
            "type": "EXPENSE",
            "amount": 1500,
            "category": "Transport",
            "narration": "Fuel station HPCL",
        }
        assert classify_expense(tx) == ExpenseTier.UNCLASSIFIED

    def test_irregular_essential_annual_insurance(self):
        tx = {
            "type": "EXPENSE",
            "amount": 36000,
            "category": "Insurance",
            "frequency": "ANNUAL",
            "narration": "HDFC Ergo Health Insurance",
        }
        assert classify_expense(tx) == ExpenseTier.IRREGULAR_ESSENTIAL

    def test_discretionary_spending(self):
        tx = {
            "type": "EXPENSE",
            "amount": 1800,
            "category": "Dining",
            "narration": "Dinner at Olive",
        }
        assert classify_expense(tx) == ExpenseTier.DISCRETIONARY


class TestHistoricalRunwayEngine:
    def test_hard_gate_zero_complete_months_returns_insufficient(self, base_account):
        # Zero statement coverage uploaded
        context = {
            "accounts": [base_account],
            "transactions": [],
            "statement_coverage": [],
        }
        res = calculate_historical_runway(context, reporting_date="2026-11-05")
        assert res["confidence"] == ConfidenceTier.INSUFFICIENT_DATA
        assert res["is_sufficient_data"] is False
        assert res["monthly_burn_rate"] == 0.0

    def test_hard_gate_one_month_ceiling_low(self, base_account):
        # 1 complete verified month (October 2026)
        context = {
            "accounts": [base_account],
            "statement_coverage": [
                {"account_id": "ACC001", "start_date": "2026-10-01", "end_date": "2026-10-31"}
            ],
            "transactions": [
                {"type": "EXPENSE", "amount": 20000, "category": "Rent", "date": "2026-10-05"},
                {"type": "EXPENSE", "amount": 10000, "category": "Groceries", "date": "2026-10-15"},
            ],
        }
        res = calculate_historical_runway(context, reporting_date="2026-11-05")
        assert len(res["eligible_historical_months"]) == 1
        assert res["confidence"] == ConfidenceTier.LOW
        assert res["monthly_burn_rate"] == 30000.0

    def test_hard_gate_two_months_ceiling_medium(self, base_account):
        # 2 complete verified months (Sept and Oct 2026)
        context = {
            "accounts": [base_account],
            "statement_coverage": [
                {"account_id": "ACC001", "start_date": "2026-09-01", "end_date": "2026-10-31"}
            ],
            "transactions": [
                # Sep
                {"type": "EXPENSE", "amount": 25000, "category": "Rent", "date": "2026-09-05"},
                # Oct
                {"type": "EXPENSE", "amount": 25000, "category": "Rent", "date": "2026-10-05"},
            ],
        }
        res = calculate_historical_runway(context, reporting_date="2026-11-05")
        assert len(res["eligible_historical_months"]) == 2
        # Gate 3 requires |H| >= 3; so 2 months is capped at MEDIUM (or LOW if volume < 15)
        assert res["confidence"] in {ConfidenceTier.LOW, ConfidenceTier.MEDIUM}
        assert res["confidence"] != ConfidenceTier.HIGH

    def test_high_confidence_three_months(self, base_account):
        # 3 complete verified months (Aug, Sep, Oct 2026) with > 25 transactions and low CV
        txs = []
        for mo in [8, 9, 10]:
            for d in range(1, 11):  # 10 essential txs per month = 30 txs total
                txs.append({
                    "type": "EXPENSE",
                    "amount": 2500,
                    "category": "Groceries",
                    "date": f"2026-{mo:02d}-{d:02d}",
                })
        context = {
            "accounts": [base_account],
            "statement_coverage": [
                {"account_id": "ACC001", "start_date": "2026-08-01", "end_date": "2026-10-31"}
            ],
            "transactions": txs,
        }
        res = calculate_historical_runway(context, reporting_date="2026-11-05")
        assert len(res["eligible_historical_months"]) == 3
        assert res["monthly_burn_rate"] == 25000.0
        assert res["confidence"] == ConfidenceTier.HIGH

    def test_missing_month_gap_does_not_dilute_divisor(self, base_account):
        # Aug and Oct have statement coverage; Sep is missing
        context = {
            "accounts": [base_account],
            "statement_coverage": [
                {"account_id": "ACC001", "start_date": "2026-08-01", "end_date": "2026-08-31"},
                {"account_id": "ACC001", "start_date": "2026-10-01", "end_date": "2026-10-31"},
            ],
            "transactions": [
                {"type": "EXPENSE", "amount": 20000, "category": "Rent", "date": "2026-08-05"},
                {"type": "EXPENSE", "amount": 30000, "category": "Rent", "date": "2026-10-05"},
            ],
        }
        res = calculate_historical_runway(context, reporting_date="2026-11-05")
        # Divisor is |H| = 2, NOT 3! Average should be (20000 + 30000) / 2 = 25000
        assert len(res["eligible_historical_months"]) == 2
        assert res["monthly_burn_rate"] == 25000.0

    def test_incomplete_current_month_excluded_from_baseline(self, base_account):
        # Reporting date is Nov 5. Statement exists up to Nov 5.
        # Nov spending must NOT be in historical baseline burn rate!
        context = {
            "accounts": [base_account],
            "statement_coverage": [
                {"account_id": "ACC001", "start_date": "2026-10-01", "end_date": "2026-11-05"}
            ],
            "transactions": [
                {"type": "EXPENSE", "amount": 25000, "category": "Rent", "date": "2026-10-05"},
                {"type": "EXPENSE", "amount": 4000, "category": "Groceries", "date": "2026-11-03"},
            ],
        }
        res = calculate_historical_runway(context, reporting_date="2026-11-05")
        # Only October is eligible
        assert res["eligible_historical_months"] == ["2026-10"]
        assert res["monthly_burn_rate"] == 25000.0
        # Nov spending reported separately in MTD
        assert res["mtd_recorded_cash_outflow"] == 4000.0

    def test_irregular_essential_not_amortized_but_reserved(self, base_account):
        context = {
            "accounts": [base_account],
            "statement_coverage": [
                {"account_id": "ACC001", "start_date": "2026-10-01", "end_date": "2026-10-31"}
            ],
            "transactions": [
                {"type": "EXPENSE", "amount": 20000, "category": "Rent", "date": "2026-10-05"},
                {"type": "EXPENSE", "amount": 36000, "category": "Insurance", "frequency": "ANNUAL", "date": "2026-10-10"},
            ],
        }
        res = calculate_historical_runway(context, reporting_date="2026-11-05")
        # Monthly survival burn excludes the annual insurance
        assert res["monthly_burn_rate"] == 20000.0
        # But emergency target reserves (3 * 20000) + 36000 = 96000
        assert res["irregular_essential_reserve"] == 36000.0
        assert res["emergency_fund_target"] == 96000.0

    def test_zero_balance_critical_status(self):
        acct = {
            "id": "ACC001",
            "type": "CHECKING",
            "balance": 0,
            "balance_paise": 0,
            "opened_date": "2025-01-01",
            "status": "ACTIVE",
        }
        context = {
            "accounts": [acct],
            "statement_coverage": [
                {"account_id": "ACC001", "start_date": "2026-10-01", "end_date": "2026-10-31"}
            ],
            "transactions": [
                {"type": "EXPENSE", "amount": 20000, "category": "Rent", "date": "2026-10-05"},
            ],
        }
        res = calculate_historical_runway(context, reporting_date="2026-11-05")
        assert res["runway_months"] == 0.0
        assert res["status"] == RunwayStatus.CRITICAL

    def test_u001_seed_benchmark_q4_accurate(self):
        # User U001: 45,000 liquid balance, 21,000 core monthly essential burn
        # Runway = 45000 / 21000 = 2.14 months
        u001_account = {
            "id": "ACC_U001",
            "type": "SAVINGS",
            "balance": 45000,
            "balance_paise": 4500000,
            "opened_date": "2025-01-01",
            "status": "ACTIVE",
        }
        # 3 trailing verified months (Aug, Sep, Oct 2026)
        txs = []
        for mo in [8, 9, 10]:
            txs.extend([
                {"type": "EXPENSE", "amount": 12000, "category": "Rent", "date": f"2026-{mo:02d}-02"},
                {"type": "EXPENSE", "amount": 5000, "category": "Groceries", "date": f"2026-{mo:02d}-04"},
                {"type": "EXPENSE", "amount": 2000, "category": "Transport", "essential_subtype": "COMMUTE", "date": f"2026-{mo:02d}-03"},
                {"type": "EXPENSE", "amount": 2000, "category": "Utilities", "date": f"2026-{mo:02d}-05"},
            ])
        context = {
            "accounts": [u001_account],
            "statement_coverage": [
                {"account_id": "ACC_U001", "start_date": "2026-08-01", "end_date": "2026-10-31"}
            ],
            "transactions": txs,
        }
        res = calculate_historical_runway(context, reporting_date="2026-11-05")
        assert res["monthly_burn_rate"] == 21000.0
        assert res["runway_months"] == pytest.approx(2.14, abs=0.01)
        # N_rec = 12 (< 15), so Gate 2 assigns LOW (Provisional) confidence honestly
        assert res["confidence"] == ConfidenceTier.LOW
        assert res["status"] == RunwayStatus.INSUFFICIENT

