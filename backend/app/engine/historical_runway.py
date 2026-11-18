"""
Deterministic Historical Runway Engine (Task 2 — Phase 2A).

Implements reliable emergency fund runway calculations using verified historical
expense data, authoritative hard eligibility gates, explicit account-month lifecycle
evaluations, day-1 continuous MTD interval anchoring, and four-tier expense classification.

Edge Case & Calculation Guarantees:
1. Strict integer-paise arithmetic using backend.app.core.money throughout.
2. Incomplete current months are strictly excluded from the historical baseline burn
   and reported separately as month-to-date (MTD) observations.
3. Liquid balance reflects accessible positive cash assets only (max(0, balance)).
   Short-term liabilities (credit card balances, overdrafts) are reported separately.
4. Confirmed internal transfers (is_transfer=True) are strictly excluded from all
   burn and expense aggregations.
5. Account lifecycle status (ACTIVE_FULL_MONTH, PARTIAL_LIFECYCLE, NOT_ACTIVE, UNKNOWN_LIFECYCLE)
   prevents truncated account history from distorting monthly spending.
6. Exhaustive 3-gate confidence hierarchy guarantees deterministic mapping to
   INSUFFICIENT_DATA, LOW, MEDIUM, or HIGH confidence tiers.
7. Does not modify or overwrite existing financial_engine.py functions.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, datetime
import math
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from backend.app.core.money import (
    div_paise,
    mul_paise,
    paise_to_float,
    ratio,
    to_paise,
)
from backend.app.engine.engine_config import DEFAULT_ENGINE_CONFIG, EngineConfig


# ---------------------------------------------------------------------------
# Constants and Taxonomy
# ---------------------------------------------------------------------------

class AccountLifecycle:
    ACTIVE_FULL_MONTH = "ACTIVE_FULL_MONTH"
    PARTIAL_LIFECYCLE = "PARTIAL_LIFECYCLE"
    NOT_ACTIVE = "NOT_ACTIVE"
    UNKNOWN_LIFECYCLE = "UNKNOWN_LIFECYCLE"


class MonthEligibility:
    ELIGIBLE = "ELIGIBLE"
    DISQUALIFIED_PARTIAL_ACCOUNT_LIFECYCLE = "DISQUALIFIED_PARTIAL_ACCOUNT_LIFECYCLE"
    DISQUALIFIED_UNKNOWN_ACCOUNT_LIFECYCLE = "DISQUALIFIED_UNKNOWN_ACCOUNT_LIFECYCLE"
    DISQUALIFIED_INCOMPLETE_COVERAGE = "DISQUALIFIED_INCOMPLETE_COVERAGE"
    DISQUALIFIED_CALENDAR_INCOMPLETE = "DISQUALIFIED_CALENDAR_INCOMPLETE"
    DISQUALIFIED_NO_SPENDING_ACCOUNTS = "DISQUALIFIED_NO_SPENDING_ACCOUNTS"


class StatementCoverageStatus:
    FULL = "FULL"
    PARTIAL = "PARTIAL"
    NONE = "NONE"


class MTDCoverageStatus:
    VERIFIED_COMPLETE_MTD = "VERIFIED_COMPLETE_MTD"
    PARTIAL_MTD_COVERAGE = "PARTIAL_MTD_COVERAGE"
    NO_COVERAGE_MTD = "NO_COVERAGE_MTD"
    NO_SPENDING_ACCOUNTS = "NO_SPENDING_ACCOUNTS"


class ExpenseTier:
    RECURRING_ESSENTIAL = "RECURRING_ESSENTIAL"
    IRREGULAR_ESSENTIAL = "IRREGULAR_ESSENTIAL"
    DISCRETIONARY = "DISCRETIONARY"
    UNCLASSIFIED = "UNCLASSIFIED"
    TRANSFER_EXCLUDED = "TRANSFER_EXCLUDED"


class ConfidenceTier:
    CRITICAL = "CRITICAL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RunwayStatus:
    CRITICAL = "CRITICAL"
    INSUFFICIENT = "INSUFFICIENT"
    HEALTHY = "HEALTHY"
    STRONG = "STRONG"


# Core recurring categories known to represent nondiscretionary monthly living expenses
DEFAULT_CORE_ESSENTIAL_CATEGORIES: Set[str] = {
    "rent",
    "housing",
    "utilities",
    "electricity",
    "water",
    "gas",
    "groceries",
    "food & groceries",
    "health",
    "medical",
    "healthcare",
    "internet",
    "wifi",
    "broadband",
}

DEFAULT_DISCRETIONARY_CATEGORIES: Set[str] = {
    "dining",
    "dining out",
    "restaurants",
    "entertainment",
    "shopping",
    "leisure",
    "vacation",
    "travel",
    "hobbies",
    "subscriptions",
    "electronics",
    "personal care",
}

NON_SPENDING_ACCOUNT_TYPES: Set[str] = {
    "loan",
    "fixed_deposit",
    "fd",
    "ppf",
    "epf",
    "recurring_deposit",
    "rd",
    "investment",
    "mortgage",
    "demat",
}


# ---------------------------------------------------------------------------
# Parsing and Date Arithmetic Helpers
# ---------------------------------------------------------------------------

def _parse_paise(val: Any, allow_negative: bool = False) -> int:
    """Safely convert a rupee value (int, float, str, Decimal) to integer paise."""
    if val is None or isinstance(val, bool):
        return 0
    try:
        p = to_paise(val)
        if not allow_negative and p < 0:
            return 0
        return p
    except (ValueError, TypeError):
        return 0


def _get_amount_paise(record: dict, key: str = "amount", allow_negative: bool = False) -> int:
    """Extract integer paise from a record, checking *_paise first, then falling back to rupee field."""
    if not isinstance(record, dict):
        return 0
    paise_key = f"{key}_paise"
    if paise_key in record:
        p_val = record[paise_key]
        if isinstance(p_val, int) and not isinstance(p_val, bool):
            return p_val if allow_negative else max(0, p_val)
    return _parse_paise(record.get(key, 0), allow_negative=allow_negative)


def _parse_date(val: Any) -> Optional[date]:
    """Parse a date from date, datetime, or ISO string."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        raw = val.strip()
        if not raw:
            return None
        try:
            return date.fromisoformat(raw[:10])
        except ValueError:
            return None
    return None


def _get_month_bounds(year: int, month: int) -> Tuple[date, date]:
    """Return (first_day, last_day) of a calendar month."""
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def _get_trailing_calendar_months(ref_date: date, count: int) -> List[Tuple[int, int]]:
    """
    Return the list of `count` complete calendar months strictly preceding `ref_date`.
    Ordered chronologically (oldest to newest): [T-count, ..., T-1].
    """
    months = []
    y, m = ref_date.year, ref_date.month
    for _ in range(count):
        m -= 1
        if m == 0:
            m = 12
            y -= 1
        months.append((y, m))
    months.reverse()
    return months


# ---------------------------------------------------------------------------
# Account Lifecycle & Statement Coverage Functions
# ---------------------------------------------------------------------------

def is_spending_account(account: dict) -> bool:
    """
    Determine if an account is an active transactional spending account.
    Excludes loans, fixed deposits, locked investments, and dormant accounts.
    """
    if not isinstance(account, dict):
        return False

    status = str(account.get("status", "")).strip().upper()
    if status == "DORMANT":
        return False

    acct_type = str(account.get("type", account.get("account_type", ""))).strip().lower()
    if acct_type in NON_SPENDING_ACCOUNT_TYPES:
        return False

    # True for CHECKING, SAVINGS, CREDIT_CARD, CURRENT, WALLET, or unspecified
    return True


def get_account_month_lifecycle(
    account: dict,
    month_start: date,
    month_end: date,
    account_has_coverage_for_month: bool = False,
) -> str:
    """
    Determine the 4-state lifecycle of a spending account for a specific calendar month [D1, DL]:
    1. ACTIVE_FULL_MONTH: Legally existed every day of [D1, DL] and was active.
    2. PARTIAL_LIFECYCLE: Opened or closed mid-month. Disqualifies month M.
    3. NOT_ACTIVE: Legally unopened, closed before D1, or dormant. Excluded with zero penalty.
    4. UNKNOWN_LIFECYCLE: opened_date is null and no verified statement certifies coverage.
    """
    if not isinstance(account, dict):
        return AccountLifecycle.NOT_ACTIVE

    status = str(account.get("status", "")).strip().upper()
    if status == "DORMANT":
        return AccountLifecycle.NOT_ACTIVE

    opened = _parse_date(account.get("opened_date", account.get("created_at")))
    closed = _parse_date(account.get("closed_date"))

    # Unknown opening date handling:
    # If opened_date is null, an account's existence prior to its earliest verified statement
    # is unknown. However, if verified statement coverage covers this month, existence is certified.
    if opened is None:
        if account_has_coverage_for_month:
            # Certified for this month by verified statement itself
            opened = month_start
        else:
            return AccountLifecycle.UNKNOWN_LIFECYCLE

    # Certified closed before month starts
    if closed is not None and closed < month_start:
        return AccountLifecycle.NOT_ACTIVE

    # Certified opened after month ends
    if opened > month_end:
        return AccountLifecycle.NOT_ACTIVE

    # Mid-month opening: opened during [D1 + 1, DL]
    if month_start < opened <= month_end:
        return AccountLifecycle.PARTIAL_LIFECYCLE

    # Mid-month closure: closed during [D1, DL - 1]
    if closed is not None and month_start <= closed < month_end:
        return AccountLifecycle.PARTIAL_LIFECYCLE

    # Account was active throughout every day of the month
    if opened <= month_start and (closed is None or closed >= month_end):
        return AccountLifecycle.ACTIVE_FULL_MONTH

    return AccountLifecycle.UNKNOWN_LIFECYCLE


def compute_continuous_interval_union(intervals: Sequence[Tuple[date, date]]) -> List[Tuple[date, date]]:
    """
    Normalize and merge overlapping or consecutive [start_date, end_date] intervals.
    Consecutive days (e.g. Nov 1-2 and Nov 3-5) are merged into Nov 1-5.
    """
    if not intervals:
        return []

    # Sort primarily by start_date, then end_date
    sorted_intervals = sorted(intervals, key=lambda x: (x[0], x[1]))
    merged: List[Tuple[date, date]] = []

    for start, end in sorted_intervals:
        if start > end:
            start, end = end, start

        if not merged:
            merged.append((start, end))
            continue

        prev_start, prev_end = merged[-1]
        # Check for overlap or immediate contiguity (prev_end + 1 day >= start)
        if (start - prev_end).days <= 1:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))

    return merged


def check_month_statement_coverage(
    month_start: date,
    month_end: date,
    account_intervals: Sequence[Tuple[date, date]],
) -> str:
    """
    Verify whether the merged intervals fully contain [month_start, month_end].
    """
    merged = compute_continuous_interval_union(account_intervals)
    for start, end in merged:
        if start <= month_start and end >= month_end:
            return StatementCoverageStatus.FULL

    # Check for partial coverage
    for start, end in merged:
        if max(start, month_start) <= min(end, month_end):
            return StatementCoverageStatus.PARTIAL

    return StatementCoverageStatus.NONE


# ---------------------------------------------------------------------------
# MTD (Month-To-Date) Continuity & Day-1 Anchoring
# ---------------------------------------------------------------------------

def evaluate_mtd_coverage(
    spending_accounts: Sequence[dict],
    coverage_by_account: Dict[str, Sequence[Tuple[date, date]]],
    reporting_date: date,
) -> Dict[str, Any]:
    """
    Evaluate MTD coverage starting strictly on Day 1 of reporting_date's month through reporting_date.
    Requires unbroken continuous coverage anchored at Day 1 (S <= Day 1 <= E).
    Guards against vacuous truth if spending_accounts is empty.
    """
    month_start = date(reporting_date.year, reporting_date.month, 1)

    if not spending_accounts:
        return {
            "status": MTDCoverageStatus.NO_SPENDING_ACCOUNTS,
            "effective_through_date": None,
            "is_complete_mtd": False,
            "account_effective_dates": {},
            "details": "No active spending accounts registered.",
        }

    account_effective: Dict[str, Optional[date]] = {}
    all_anchored = True

    for acct in spending_accounts:
        acct_id = str(acct.get("id") or acct.get("account_id", ""))
        intervals = coverage_by_account.get(acct_id, [])
        merged = compute_continuous_interval_union(intervals)

        # Look for the unique interval that anchors month_start: S <= Day 1 <= E
        anchoring_reach: Optional[date] = None
        for start, end in merged:
            if start <= month_start <= end:
                anchoring_reach = min(end, reporting_date)
                break

        account_effective[acct_id] = anchoring_reach
        if anchoring_reach is None:
            all_anchored = False

    if not all_anchored or not account_effective:
        return {
            "status": MTDCoverageStatus.NO_COVERAGE_MTD,
            "effective_through_date": None,
            "is_complete_mtd": False,
            "account_effective_dates": account_effective,
            "details": "One or more spending accounts have no statement coverage starting on Day 1.",
        }

    # Minimum continuous reach across all spending accounts
    min_reach = min(dt for dt in account_effective.values() if dt is not None)

    if min_reach >= reporting_date:
        status = MTDCoverageStatus.VERIFIED_COMPLETE_MTD
        is_complete = True
    else:
        status = MTDCoverageStatus.PARTIAL_MTD_COVERAGE
        is_complete = False

    return {
        "status": status,
        "effective_through_date": min_reach,
        "is_complete_mtd": is_complete,
        "account_effective_dates": account_effective,
        "details": f"Continuous MTD coverage anchored on Day 1 extends through {min_reach.isoformat()}.",
    }


# ---------------------------------------------------------------------------
# Expense Classification (Four Tiers)
# ---------------------------------------------------------------------------

def classify_expense(tx: dict, annual_threshold_paise: int = 1000000) -> str:
    """
    Classify an expense transaction into one of four distinct tiers:
    1. RECURRING_ESSENTIAL: Fixed/nondiscretionary survival expenses (rent, groceries, utilities, confirmed commute).
    2. IRREGULAR_ESSENTIAL: Mandatory, high-impact non-monthly expenses (annual insurance, major hospital bills).
    3. DISCRETIONARY: Lifestyle, dining, leisure, entertainment spending.
    4. UNCLASSIFIED: Ambiguous transactions or inferred commute candidates requiring user confirmation.
    5. TRANSFER_EXCLUDED: Confirmed internal transfers (strictly excluded from all expenses).
    """
    if not isinstance(tx, dict):
        return ExpenseTier.UNCLASSIFIED

    # Rule 0: Confirmed internal transfers are never expenses
    if tx.get("is_transfer") is True:
        return ExpenseTier.TRANSFER_EXCLUDED

    tx_type = str(tx.get("type", "")).strip().upper()
    if tx_type != "EXPENSE":
        return ExpenseTier.UNCLASSIFIED

    amt_paise = _get_amount_paise(tx)
    cat = str(tx.get("category", "")).strip().lower()
    subtype = str(tx.get("essential_subtype", "")).strip().upper()
    narration = str(tx.get("narration", tx.get("description", ""))).lower()

    # Rule 1: Transport & Commuting explicit evidence check
    if cat in {"transport", "transportation", "fuel", "commute", "travel"}:
        if subtype == "COMMUTE" or tx.get("is_commute_confirmed") is True:
            return ExpenseTier.RECURRING_ESSENTIAL
        # If user explicitly marked non-essential
        if tx.get("is_commute_confirmed") is False:
            return ExpenseTier.DISCRETIONARY
        # Narration explicit commute pass marker (e.g. seed T003)
        if "commute" in narration or "metro pass" in narration or "bus pass" in narration:
            return ExpenseTier.RECURRING_ESSENTIAL
        # Ambiguous fuel, tolls, auto/cab without explicit confirmation -> UNCLASSIFIED candidate
        return ExpenseTier.UNCLASSIFIED

    # Rule 2: Explicit irregular essential flag
    if tx.get("is_irregular_essential") is True or subtype == "IRREGULAR_ESSENTIAL":
        return ExpenseTier.IRREGULAR_ESSENTIAL

    # Rule 3: Insurance & Hospital large expenses
    if "insurance" in cat or "insurance" in narration:
        freq = str(tx.get("frequency", "")).strip().upper()
        if freq == "ANNUAL" or amt_paise >= annual_threshold_paise:
            return ExpenseTier.IRREGULAR_ESSENTIAL
        return ExpenseTier.RECURRING_ESSENTIAL

    if "hospital" in cat or "hospital" in narration or "medical emergency" in cat:
        if amt_paise >= annual_threshold_paise or tx.get("is_one_time") is True:
            return ExpenseTier.IRREGULAR_ESSENTIAL
        return ExpenseTier.RECURRING_ESSENTIAL

    # Rule 4: Core Recurring Essentials
    if cat in DEFAULT_CORE_ESSENTIAL_CATEGORIES:
        return ExpenseTier.RECURRING_ESSENTIAL

    # Rule 5: Discretionary
    if cat in DEFAULT_DISCRETIONARY_CATEGORIES:
        return ExpenseTier.DISCRETIONARY

    return ExpenseTier.UNCLASSIFIED


# ---------------------------------------------------------------------------
# Historical Baseline & Confidence Scoring
# ---------------------------------------------------------------------------

def calculate_confidence_score(
    n_months: int,
    cv_burn: float,
    n_records: int,
) -> float:
    """
    Calculate the renormalized 3-factor confidence score:
    C_score = 0.50 * S_months + 0.30 * S_consistency + 0.20 * S_volume
    """
    # 1. S_months (weight 0.50)
    if n_months >= 6:
        s_months = 1.0
    elif n_months >= 4:
        s_months = 0.85
    elif n_months == 3:
        s_months = 0.70
    elif n_months == 2:
        s_months = 0.50
    elif n_months == 1:
        s_months = 0.25
    else:
        s_months = 0.0

    # 2. S_consistency (weight 0.30)
    if n_months <= 1:
        s_consistency = 0.30
    elif cv_burn <= 0.15:
        s_consistency = 1.0
    elif cv_burn <= 0.35:
        s_consistency = 0.75
    elif cv_burn <= 0.50:
        s_consistency = 0.40
    else:
        s_consistency = 0.15

    # 3. S_volume (weight 0.20)
    if n_records >= 45:
        s_volume = 1.0
    elif n_records >= 25:
        s_volume = 0.75
    elif n_records >= 15:
        s_volume = 0.50
    else:
        s_volume = min(1.0, round(n_records / 30.0, 3))

    score = (0.50 * s_months) + (0.30 * s_consistency) + (0.20 * s_volume)
    return round(score, 3)


def determine_confidence_tier(
    n_eligible_months: int,
    mean_burn_paise: int,
    n_records: int,
    cv_burn: float,
    confidence_score: float,
) -> str:
    """
    Evaluate the exhaustive, mutually exclusive 3-gate confidence hierarchy:
    Gate 1: |H| == 0 OR mean_burn == 0 -> INSUFFICIENT_DATA
    Gate 2: |H| == 1 OR N_records < 15 -> LOW (Provisional)
    Gate 3: |H| >= 3 AND N_records >= 25 AND CV <= 0.35 AND C_score >= 0.80 -> HIGH, else MEDIUM
    """
    if n_eligible_months == 0 or mean_burn_paise == 0:
        return ConfidenceTier.INSUFFICIENT_DATA

    if n_eligible_months == 1 or n_records < 15:
        return ConfidenceTier.LOW

    if (
        n_eligible_months >= 3
        and n_records >= 25
        and cv_burn <= 0.35
        and confidence_score >= 0.80
    ):
        return ConfidenceTier.HIGH

    return ConfidenceTier.MEDIUM


# ---------------------------------------------------------------------------
# Master Historical Runway Calculation
# ---------------------------------------------------------------------------

def calculate_historical_runway(
    context: dict,
    reporting_date: date | str | None = None,
    config: EngineConfig | None = None,
    window_months: int = 3,
) -> Dict[str, Any]:
    """
    Deterministic Historical Emergency Fund Runway and Burn-Rate Calculation.

    Evaluates eligible trailing complete calendar months [T-N ... T-1], checks
    100% full statement coverage across active spending accounts, classifies
    expenses into four tiers, and evaluates confidence via exhaustive hard gates.
    """
    cfg = config or DEFAULT_ENGINE_CONFIG

    # Resolve reporting date
    if reporting_date is None:
        rep_date = date.today()
    elif isinstance(reporting_date, str):
        try:
            rep_date = date.fromisoformat(reporting_date[:10])
        except ValueError:
            rep_date = date.today()
    elif isinstance(reporting_date, datetime):
        rep_date = reporting_date.date()
    else:
        rep_date = reporting_date

    # 1. Accounts & Positive Liquid Balance vs. Short-Term Liabilities
    accounts = context.get("accounts", []) if isinstance(context, dict) else []
    spending_accounts = [a for a in accounts if is_spending_account(a)]

    liquid_balance_paise = 0
    short_term_liabilities_paise = 0
    for acct in accounts:
        if not isinstance(acct, dict):
            continue
        bal_paise = _get_amount_paise(acct, "balance", allow_negative=True)
        acct_type = str(acct.get("type", acct.get("account_type", ""))).strip().lower()

        if acct_type in NON_SPENDING_ACCOUNT_TYPES:
            # Excluded from liquid balance
            continue
        elif acct_type == "credit_card":
            # Credit card balances represent liabilities
            if bal_paise > 0:
                short_term_liabilities_paise += bal_paise
        else:
            if bal_paise >= 0:
                liquid_balance_paise += bal_paise
            else:
                # Overdraft liability
                short_term_liabilities_paise += abs(bal_paise)

    # 2. Extract Coverage Intervals from Context (if present)
    # Supported context keys: statement_coverage, coverage_intervals, or statements
    coverage_by_account: Dict[str, List[Tuple[date, date]]] = {}
    coverage_nodes = context.get("statement_coverage", context.get("coverage_intervals", []))
    for node in coverage_nodes:
        if not isinstance(node, dict):
            continue
        a_id = str(node.get("account_id") or node.get("account", ""))
        s_date = _parse_date(node.get("start_date", node.get("statement_start")))
        e_date = _parse_date(node.get("end_date", node.get("statement_end")))
        if a_id and s_date and e_date:
            coverage_by_account.setdefault(a_id, []).append((s_date, e_date))

    # 3. Evaluate Trailing Calendar Months [T-N ... T-1]
    trailing_month_pairs = _get_trailing_calendar_months(rep_date, window_months)
    all_transactions = context.get("transactions", []) if isinstance(context, dict) else []

    month_evaluations: List[Dict[str, Any]] = []
    eligible_months: List[Tuple[int, int]] = []
    month_burns_paise: List[int] = []
    total_essential_records = 0
    total_irregular_reserve_paise = 0

    for yr, mo in trailing_month_pairs:
        m_start, m_end = _get_month_bounds(yr, mo)
        m_label = f"{yr}-{mo:02d}"

        # Calendar completeness: Must have strictly concluded before reporting_date
        if rep_date <= m_end:
            month_evaluations.append({
                "month": m_label,
                "eligibility": MonthEligibility.DISQUALIFIED_CALENDAR_INCOMPLETE,
                "reason": "Calendar month has not fully elapsed.",
            })
            continue

        # Account set and coverage evaluation
        if not spending_accounts:
            month_evaluations.append({
                "month": m_label,
                "eligibility": MonthEligibility.DISQUALIFIED_NO_SPENDING_ACCOUNTS,
                "reason": "No spending accounts registered.",
            })
            continue

        account_statuses = {}
        disqualified_reason = None

        for acct in spending_accounts:
            a_id = str(acct.get("id") or acct.get("account_id", ""))
            intervals = coverage_by_account.get(a_id, [])
            cov_status = check_month_statement_coverage(m_start, m_end, intervals)

            lifecycle = get_account_month_lifecycle(
                acct,
                m_start,
                m_end,
                account_has_coverage_for_month=(cov_status == StatementCoverageStatus.FULL),
            )
            account_statuses[a_id] = {"lifecycle": lifecycle, "coverage": cov_status}

            if lifecycle == AccountLifecycle.PARTIAL_LIFECYCLE:
                disqualified_reason = MonthEligibility.DISQUALIFIED_PARTIAL_ACCOUNT_LIFECYCLE
            elif lifecycle == AccountLifecycle.UNKNOWN_LIFECYCLE and disqualified_reason is None:
                disqualified_reason = MonthEligibility.DISQUALIFIED_UNKNOWN_ACCOUNT_LIFECYCLE
            elif lifecycle == AccountLifecycle.ACTIVE_FULL_MONTH:
                # If active full month, coverage MUST be FULL
                if cov_status != StatementCoverageStatus.FULL and disqualified_reason is None:
                    # Check legacy transaction fallback:
                    # If coverage nodes are absent system-wide, do legacy transactions exist?
                    if not coverage_nodes:
                        # Legacy transactions without coverage nodes
                        pass
                    else:
                        disqualified_reason = MonthEligibility.DISQUALIFIED_INCOMPLETE_COVERAGE

        if disqualified_reason is not None:
            month_evaluations.append({
                "month": m_label,
                "eligibility": disqualified_reason,
                "account_statuses": account_statuses,
            })
            continue

        # Month is eligible: aggregate classified expenses
        month_txs = []
        for tx in all_transactions:
            if not isinstance(tx, dict):
                continue
            tx_d = _parse_date(tx.get("date"))
            if tx_d and tx_d.year == yr and tx_d.month == mo:
                month_txs.append(tx)

        core_burn_month_paise = 0
        essential_records_month = 0

        for tx in month_txs:
            tier = classify_expense(tx)
            if tier == ExpenseTier.RECURRING_ESSENTIAL:
                amt = _get_amount_paise(tx)
                core_burn_month_paise += amt
                essential_records_month += 1
            elif tier == ExpenseTier.IRREGULAR_ESSENTIAL:
                total_irregular_reserve_paise += _get_amount_paise(tx)

        eligible_months.append((yr, mo))
        month_burns_paise.append(core_burn_month_paise)
        total_essential_records += essential_records_month

        month_evaluations.append({
            "month": m_label,
            "eligibility": MonthEligibility.ELIGIBLE,
            "core_essential_burn": paise_to_float(core_burn_month_paise),
            "essential_records": essential_records_month,
        })

    # 4. Handle Legacy Fallback When 0 Coverage Nodes Exist
    # If no coverage nodes exist at all, evaluate legacy provisional months based on transactions
    is_legacy_data = False
    if not coverage_nodes and not eligible_months:
        for yr, mo in trailing_month_pairs:
            m_start, m_end = _get_month_bounds(yr, mo)
            if rep_date <= m_end:
                continue
            m_txs = [
                tx for tx in all_transactions
                if isinstance(tx, dict)
                and _parse_date(tx.get("date"))
                and _parse_date(tx.get("date")).year == yr
                and _parse_date(tx.get("date")).month == mo
                and tx.get("type") == "EXPENSE"
                and tx.get("is_transfer") is not True
            ]
            if m_txs:
                is_legacy_data = True
                b_paise = sum(_get_amount_paise(tx) for tx in m_txs)
                eligible_months.append((yr, mo))
                month_burns_paise.append(b_paise)
                total_essential_records += len(m_txs)

    # 5. Core Recurring Essential Monthly Burn Calculation
    n_h = len(eligible_months)
    if n_h > 0:
        mean_burn_paise = div_paise(sum(month_burns_paise), n_h)
        # Coefficient of variation (CV)
        if n_h > 1 and mean_burn_paise > 0:
            burn_floats = [paise_to_float(b) for b in month_burns_paise]
            mean_f = sum(burn_floats) / n_h
            variance = sum((x - mean_f) ** 2 for x in burn_floats) / n_h
            std_dev = math.sqrt(variance)
            cv_burn = round(std_dev / mean_f, 3)
        else:
            cv_burn = 0.0
    else:
        mean_burn_paise = 0
        cv_burn = 0.0

    # 6. Confidence Scoring & Exhaustive Gating
    c_score = calculate_confidence_score(n_h, cv_burn, total_essential_records)
    confidence_tier = determine_confidence_tier(
        n_eligible_months=n_h,
        mean_burn_paise=mean_burn_paise,
        n_records=total_essential_records,
        cv_burn=cv_burn,
        confidence_score=c_score,
    )

    if is_legacy_data and confidence_tier != ConfidenceTier.INSUFFICIENT_DATA:
        confidence_tier = ConfidenceTier.LOW

    # 7. MTD Spending and Continuity (Strictly Isolated from Historical Baseline)
    mtd_coverage_info = evaluate_mtd_coverage(spending_accounts, coverage_by_account, rep_date)
    mtd_txs = [
        tx for tx in all_transactions
        if isinstance(tx, dict)
        and _parse_date(tx.get("date"))
        and _parse_date(tx.get("date")).year == rep_date.year
        and _parse_date(tx.get("date")).month == rep_date.month
        and _parse_date(tx.get("date")) <= rep_date
        and tx.get("type") == "EXPENSE"
        and tx.get("is_transfer") is not True
    ]
    mtd_cash_outflow_paise = sum(_get_amount_paise(tx) for tx in mtd_txs)

    # 8. Runway Duration & Solvency Status
    if liquid_balance_paise <= 0:
        runway_months = 0.0
        status = RunwayStatus.CRITICAL
    elif n_h == 0 or mean_burn_paise == 0:
        # Insufficient data
        runway_months = None
        status = RunwayStatus.CRITICAL if liquid_balance_paise <= 0 else RunwayStatus.INSUFFICIENT
    else:
        r = ratio(liquid_balance_paise, mean_burn_paise)
        runway_months = round(r, 2) if r is not None else 0.0

        if runway_months >= cfg.runway_bands.healthy_max:
            status = RunwayStatus.STRONG
        elif runway_months >= cfg.runway_bands.insufficient_max:
            status = RunwayStatus.HEALTHY
        elif runway_months >= cfg.runway_bands.critical_max:
            status = RunwayStatus.INSUFFICIENT
        else:
            status = RunwayStatus.CRITICAL

    # 9. Emergency Fund Target & Shortfall
    # Formula: (K * Burn_core) + ConfirmedUpcomingObligations
    k_mult = cfg.emergency_reserve_multiplier
    emergency_target_paise = mul_paise(mean_burn_paise, k_mult) + total_irregular_reserve_paise
    emergency_shortfall_paise = max(0, emergency_target_paise - liquid_balance_paise)

    return {
        "liquid_balance": paise_to_float(liquid_balance_paise),
        "short_term_liabilities": paise_to_float(short_term_liabilities_paise),
        "monthly_burn_rate": paise_to_float(mean_burn_paise),
        "runway_months": runway_months,
        "status": status,
        "confidence": confidence_tier,
        "confidence_score": c_score,
        "is_sufficient_data": (n_h > 0 and mean_burn_paise > 0),
        "eligible_historical_months": [f"{y}-{m:02d}" for y, m in eligible_months],
        "month_evaluations": month_evaluations,
        "irregular_essential_reserve": paise_to_float(total_irregular_reserve_paise),
        "emergency_fund_target": paise_to_float(emergency_target_paise),
        "emergency_fund_shortfall": paise_to_float(emergency_shortfall_paise),
        "mtd_recorded_cash_outflow": paise_to_float(mtd_cash_outflow_paise),
        "mtd_coverage": mtd_coverage_info,
        "reporting_date": rep_date.isoformat(),
        "is_legacy_data": is_legacy_data,
    }

