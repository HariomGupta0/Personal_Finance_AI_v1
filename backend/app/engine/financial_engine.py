"""
Deterministic Financial Reasoning Engine.

Acts as the authoritative single source of truth for all mathematical calculations:
- Savings rate
- Emergency fund requirement & shortfall
- Emergency runway & burn-rate diagnostics
- Debt-to-income (DTI) ratio & EMI obligations
- Comprehensive financial health score (0-100)
- Purchase safety and risk classification

Edge case and audit guarantees:
1. Clamps health scores strictly to [0.0, 100.0] even under extreme negative savings or overdraft balances.
2. Explicitly distinguishes zero-income and insufficient-data scenarios from healthy baselines.
3. Does not equate zero recorded transactions with zero real living expenses.
4. Exposes reporting_period and reporting_date across all calculations.
5. Deduplicates pending EMIs to eliminate double-counting risks and handles negative purchase amounts safely.
6. Preserves existing dictionary keys and types for 100% backward compatibility.
"""
from datetime import date, datetime
from decimal import Decimal
import logging
import re
from typing import Any

from backend.app.core.money import div_paise, mul_paise, paise_to_float, ratio, to_paise

logger = logging.getLogger(__name__)


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



def _resolve_reporting_date(context, reporting_date=None):
    if reporting_date is not None:
        if isinstance(reporting_date, datetime):
            return reporting_date.date()
        if isinstance(reporting_date, str):
            try:
                return date.fromisoformat(reporting_date)
            except ValueError:
                pass
        return reporting_date

    today = date.today()
    if not isinstance(context, dict):
        return today

    all_dates = []
    for item in (context.get("transactions") or []) + (context.get("incomes") or []):
        if not isinstance(item, dict):
            continue
        val = item.get("date")
        if val:
            if isinstance(val, datetime):
                all_dates.append(val.date())
            elif isinstance(val, date):
                all_dates.append(val)
            elif isinstance(val, str):
                try:
                    all_dates.append(date.fromisoformat(val))
                except ValueError:
                    pass
    if not all_dates:
        return today
    if any((d.year, d.month) == (today.year, today.month) for d in all_dates):
        return today
    return max(all_dates)


def _is_in_reporting_month(record, target_date=None):
    """Return whether a dated income/transaction belongs to the target reporting month."""
    if not isinstance(record, dict):
        return False
    if target_date is None:
        target_date = date.today()
    value = record.get("date")
    if not value:
        return False
    if isinstance(value, datetime):
        record_date = value.date()
    elif isinstance(value, date):
        record_date = value
    else:
        try:
            record_date = date.fromisoformat(str(value))
        except ValueError:
            return False
    return (record_date.year, record_date.month) == (target_date.year, target_date.month)


def _monthly_transactions(context, reporting_date=None):
    if not isinstance(context, dict):
        return []
    target = _resolve_reporting_date(context, reporting_date)
    return [
        tx for tx in context.get("transactions", [])
        if isinstance(tx, dict) and _is_in_reporting_month(tx, target)
    ]


def _monthly_incomes(context, reporting_date=None):
    if not isinstance(context, dict):
        return []
    target = _resolve_reporting_date(context, reporting_date)
    return [
        income for income in context.get("incomes", [])
        if isinstance(income, dict) and _is_in_reporting_month(income, target)
    ]


def _get_deduplicated_pending_emis(context, target_date):
    """
    Extract and deduplicate pending EMIs for the target reporting month.
    Prevents duplicate entries caused by Cartesian joins across multiple accounts.
    """
    if not isinstance(context, dict):
        return []

    loans = context.get("loans", [])
    deduped = []
    seen = set()

    for idx, loan in enumerate(loans):
        if not isinstance(loan, dict):
            continue
        status = str(loan.get("status", "")).strip().upper()
        if status != "PENDING":
            continue

        due_date = loan.get("due_date")
        if due_date and not _is_in_reporting_month({"date": due_date}, target_date):
            continue

        emi_paise = _get_amount_paise(loan, "emi") or _get_amount_paise(loan, "amount")
        if emi_paise <= 0:
            continue

        dedup_key = (
            str(loan.get("id") or loan.get("loan") or loan.get("name") or f"loan_{idx}"),
            str(due_date or ""),
            emi_paise,
        )
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        deduped.append({"loan": loan, "amount": paise_to_float(emi_paise), "amount_paise": emi_paise})

    return deduped


def calculate_category_expenses(context, reporting_date=None):
    """
    Computes category-wise expense breakdown, proportions, and largest spending category.
    """
    target = _resolve_reporting_date(context, reporting_date)
    reporting_period = f"{target.year}-{target.month:02d}"

    category_totals = {}
    total_expenses_paise = 0

    for tx in _monthly_transactions(context, target):
        if tx.get("type") == "EXPENSE":
            cat = tx.get("category") or "Uncategorized"
            amt_paise = _get_amount_paise(tx)
            if amt_paise > 0:
                category_totals[cat] = category_totals.get(cat, 0) + amt_paise
                total_expenses_paise += amt_paise

    breakdown = []
    for cat, amt_paise in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
        r = ratio(amt_paise, total_expenses_paise)
        percentage = round(r * 100.0, 2) if r is not None else 0.0
        breakdown.append({
            "category": cat,
            "amount": paise_to_float(amt_paise),
            "percentage": percentage,
        })

    top_category = breakdown[0]["category"] if breakdown else "None"
    top_amount = breakdown[0]["amount"] if breakdown else 0.0

    return {
        "total_expenses": paise_to_float(total_expenses_paise),
        "categories": breakdown,
        "top_category": top_category,
        "top_amount": top_amount,
        "reporting_period": reporting_period,
    }


def calculate_emergency_fund(context, reporting_date=None):
    """
    Calculates 3-month recommended emergency fund and current shortfall.
    """
    target = _resolve_reporting_date(context, reporting_date)
    reporting_period = f"{target.year}-{target.month:02d}"

    monthly_txs = _monthly_transactions(context, target)
    monthly_expenses_paise = sum(
        _get_amount_paise(transaction)
        for transaction in monthly_txs
        if transaction.get("type") == "EXPENSE"
    )

    recommended_fund_paise = mul_paise(monthly_expenses_paise, 3)

    goals = context.get("goals", []) if isinstance(context, dict) else []
    emergency_goal = next(
        (
            goal for goal in goals
            if (goal.get("name") or goal.get("goal") or "").strip().lower() == "emergency fund"
        ),
        None,
    )
    if emergency_goal:
        current_fund_paise = (
            _get_amount_paise(emergency_goal, "current_amount")
            or _get_amount_paise(emergency_goal, "current")
        )
    else:
        current_fund_paise = 0
    current_fund_paise = max(0, current_fund_paise)

    shortfall_paise = max(0, recommended_fund_paise - current_fund_paise)

    return {
        "monthly_expenses": paise_to_float(monthly_expenses_paise),
        "recommended_fund": paise_to_float(recommended_fund_paise),
        "current_fund": paise_to_float(current_fund_paise),
        "shortfall": paise_to_float(shortfall_paise),
        "is_sufficient_data": monthly_expenses_paise > 0,
        "reporting_period": reporting_period,
    }


def calculate_emergency_runway(context, reporting_date=None):
    """
    Calculates available emergency runway in months based on liquid balance and monthly expenses.
    Explicitly flags zero-expense periods where actual expenses are unrecorded.
    """
    target = _resolve_reporting_date(context, reporting_date)
    reporting_period = f"{target.year}-{target.month:02d}"

    accounts = context.get("accounts", []) if isinstance(context, dict) else []
    balance_paise = sum(
        _get_amount_paise(account, "balance", allow_negative=True)
        for account in accounts
        if isinstance(account, dict)
    )

    expense_txs = [
        tx for tx in _monthly_transactions(context, target)
        if tx.get("type") == "EXPENSE"
    ]
    monthly_expenses_paise = sum(_get_amount_paise(tx) for tx in expense_txs)

    if monthly_expenses_paise == 0:
        # Zero recorded expenses: do not assume real living expenses are zero.
        # Preserve runway_months = 12.0 for contract compatibility when balance > 0,
        # but explicitly flag insufficient data.
        if balance_paise <= 0:
            runway_months = 0.0
            status = "CRITICAL"
        else:
            runway_months = 12.0
            status = "STRONG"
        is_sufficient_data = False
        data_note = "Zero recorded expenses in period; runway is capped nominally but actual expenses are unrecorded."
    else:
        if balance_paise <= 0:
            runway_months = 0.0
        else:
            r = ratio(balance_paise, monthly_expenses_paise)
            runway_months = round(r, 2) if r is not None else 0.0
        is_sufficient_data = True
        data_note = None

    if balance_paise < 0:
        status = "CRITICAL"
    elif runway_months >= 6.0:
        status = "STRONG"
    elif runway_months >= 3.0:
        status = "HEALTHY"
    elif runway_months >= 1.0:
        status = "INSUFFICIENT"
    else:
        status = "CRITICAL"

    return {
        "current_balance": paise_to_float(balance_paise),
        "monthly_expenses": paise_to_float(monthly_expenses_paise),
        "runway_months": runway_months,
        "status": status,
        "target_runway_months": 3.0,
        "is_sufficient_data": is_sufficient_data,
        "data_note": data_note,
        "reporting_period": reporting_period,
    }


def calculate_savings_rate(context, reporting_date=None):
    """
    Calculates total income, expenses, net savings, and savings rate percentage.
    """
    target = _resolve_reporting_date(context, reporting_date)
    reporting_period = f"{target.year}-{target.month:02d}"

    monthly_incomes = _monthly_incomes(context, target)
    monthly_txs = _monthly_transactions(context, target)

    total_income_paise = sum(
        _get_amount_paise(income)
        for income in monthly_incomes
    )

    total_expenses_paise = sum(
        _get_amount_paise(transaction)
        for transaction in monthly_txs
        if transaction.get("type") == "EXPENSE"
    )

    savings_paise = total_income_paise - total_expenses_paise

    if total_income_paise == 0:
        savings_rate = 0.0
        has_income = False
        is_sufficient_data = bool(monthly_txs or monthly_incomes)
    else:
        r = ratio(savings_paise, total_income_paise)
        savings_rate = round(r * 100.0, 2) if r is not None else 0.0
        has_income = True
        is_sufficient_data = True

    return {
        "total_income": paise_to_float(total_income_paise),
        "total_expenses": paise_to_float(total_expenses_paise),
        "savings": paise_to_float(savings_paise),
        "savings_rate": savings_rate,
        "has_income": has_income,
        "is_sufficient_data": is_sufficient_data,
        "reporting_period": reporting_period,
    }


def calculate_debt_burden(context, reporting_date=None):
    """
    Calculates total outstanding debt, monthly EMI obligations, and Debt-to-Income (DTI) ratio.
    Deduplicates pending EMIs and explicitly handles zero-income edge cases.
    """
    target = _resolve_reporting_date(context, reporting_date)
    reporting_period = f"{target.year}-{target.month:02d}"

    total_income_paise = sum(
        _get_amount_paise(income)
        for income in _monthly_incomes(context, target)
    )

    loans = context.get("loans", []) if isinstance(context, dict) else []
    total_outstanding_paise = sum(
        _get_amount_paise(l, "outstanding")
        for l in loans
        if isinstance(l, dict)
    )

    # Deduplicated pending EMIs due in the target reporting month
    deduped_emis = _get_deduplicated_pending_emis(context, target)
    monthly_emi_paise = sum(item["amount_paise"] for item in deduped_emis)

    if total_income_paise > 0:
        r = ratio(monthly_emi_paise, total_income_paise)
        dti_ratio = round(r * 100.0, 2) if r is not None else 0.0
        has_income = True
        is_sufficient_data = True
        if dti_ratio <= 20.0:
            risk = "LOW"
            assessment = "Healthy debt level (under 20% of income)."
        elif dti_ratio <= 35.0:
            risk = "MODERATE"
            assessment = "Manageable debt obligations."
        elif dti_ratio <= 50.0:
            risk = "HIGH"
            assessment = "Elevated debt burden requiring caution."
        else:
            risk = "CRITICAL"
            assessment = "Critical debt burden exceeding 50% of monthly income."
    else:
        dti_ratio = 0.0
        has_income = False
        if monthly_emi_paise > 0:
            risk = "CRITICAL"
            assessment = "Critical debt risk: Active monthly EMI obligations with zero recorded income."
            is_sufficient_data = True
        else:
            risk = "LOW"
            assessment = "No recorded debt obligations or income."
            is_sufficient_data = False

    return {
        "total_outstanding_debt": paise_to_float(total_outstanding_paise),
        "monthly_emi": paise_to_float(monthly_emi_paise),
        "dti_ratio": dti_ratio,
        "risk_level": risk,
        "assessment": assessment,
        "has_income": has_income,
        "is_sufficient_data": is_sufficient_data,
        "reporting_period": reporting_period,
    }


def calculate_comprehensive_health(context, reporting_date=None):
    """
    Evaluates complete financial health score strictly bounded in [0.0, 100.0].
    Safeguards against negative savings rate degradation and zero-income artifacts.
    """
    target = _resolve_reporting_date(context, reporting_date)
    reporting_period = f"{target.year}-{target.month:02d}"

    savings = calculate_savings_rate(context, target)
    runway = calculate_emergency_runway(context, target)
    debt = calculate_debt_burden(context, target)
    emergency = calculate_emergency_fund(context, target)

    # 1. Savings score (max 35 pts) - 20% savings gives full score.
    # Non-negative clamping: negative savings rate yields 0.0 pts.
    savings_score = max(0.0, min(35.0, (savings["savings_rate"] / 20.0) * 35.0))

    # 2. Emergency Runway score (max 35 pts) - 3 months gives full score.
    # Non-negative clamping: overdraft / zero runway yields 0.0 pts.
    runway_score = max(0.0, min(35.0, (runway["runway_months"] / 3.0) * 35.0))

    # 3. Debt score (max 30 pts) - DTI < 20% gives 30 pts, > 50% gives 0 pts.
    # Active EMIs with zero income represents critical debt risk (0.0 pts).
    if debt.get("monthly_emi", 0) > 0 and savings.get("total_income", 0) <= 0:
        debt_score = 0.0
    elif debt["dti_ratio"] <= 20.0:
        debt_score = 30.0
    elif debt["dti_ratio"] >= 50.0:
        debt_score = 0.0
    else:
        debt_score = max(0.0, min(30.0, 30.0 - ((debt["dti_ratio"] - 20.0) / 30.0 * 30.0)))

    # Strictly clamp final score to documented [0.0, 100.0] range
    total_score = max(0.0, min(100.0, round(savings_score + runway_score + debt_score, 1)))

    if total_score >= 85.0:
        grade = "A"
        summary = "Excellent financial health with strong reserves and manageable debt."
    elif total_score >= 70.0:
        grade = "B"
        summary = "Good financial standing with minor areas for savings or emergency reserve optimization."
    elif total_score >= 50.0:
        grade = "C"
        summary = "Fair financial position; recommended to increase emergency reserves."
    else:
        grade = "D"
        summary = "Vulnerable financial health; urgent focus required on debt reduction and emergency savings."

    return {
        "health_score": total_score,
        "grade": grade,
        "summary": summary,
        "savings_rate": savings["savings_rate"],
        "runway_months": runway["runway_months"],
        "dti_ratio": debt["dti_ratio"],
        "emergency_shortfall": emergency["shortfall"],
        "reporting_period": reporting_period,
        "is_sufficient_data": savings["is_sufficient_data"] and emergency["is_sufficient_data"],
    }


def check_purchase_safety(context, purchase_amount, reporting_date=None):
    """
    Evaluates whether a purchase is financially safe.
    Safely deduplicates pending EMIs, clamps negative purchase amounts,
    and flags cases where monthly expense data is unverified.
    """
    target = _resolve_reporting_date(context, reporting_date)
    reporting_period = f"{target.year}-{target.month:02d}"

    accounts = context.get("accounts", []) if isinstance(context, dict) else []
    balance_paise = sum(
        _get_amount_paise(account, "balance", allow_negative=True)
        for account in accounts
        if isinstance(account, dict)
    )

    # Deduplicate pending EMIs to eliminate double-counting
    deduped_emis = _get_deduplicated_pending_emis(context, target)
    pending_emi_paise = sum(item["amount_paise"] for item in deduped_emis)

    monthly_txs = _monthly_transactions(context, target)
    monthly_expenses_paise = sum(
        _get_amount_paise(transaction)
        for transaction in monthly_txs
        if transaction.get("type") == "EXPENSE"
    )

    emergency_requirement_paise = mul_paise(monthly_expenses_paise, 3)

    # Sanitize purchase amount: prevent negative values from artificially inflating balance
    sanitized_purchase_paise = max(0, _parse_paise(purchase_amount))

    balance_after_purchase_paise = (
        balance_paise - pending_emi_paise - sanitized_purchase_paise
    )

    is_safe = balance_after_purchase_paise >= emergency_requirement_paise

    if balance_after_purchase_paise >= emergency_requirement_paise:
        risk_level = "LOW"
    elif balance_after_purchase_paise >= monthly_expenses_paise:
        risk_level = "MEDIUM"
    elif balance_after_purchase_paise > 0:
        risk_level = "HIGH"
    else:
        risk_level = "VERY_HIGH"

    balance_after_purchase = paise_to_float(balance_after_purchase_paise)
    emergency_requirement = paise_to_float(emergency_requirement_paise)

    if is_safe:
        reason = (
            f"The purchase is financially safe. "
            f"After the pending EMI and purchase, "
            f"₹{balance_after_purchase:,.0f} would remain, "
            f"which is above the recommended emergency "
            f"reserve of ₹{emergency_requirement:,.0f}."
        )
    else:
        reason = (
            f"The purchase is not financially safe. "
            f"After the pending EMI and purchase, "
            f"only ₹{balance_after_purchase:,.0f} would remain, "
            f"which is below the recommended emergency "
            f"reserve of ₹{emergency_requirement:,.0f}."
        )

    if monthly_expenses_paise == 0:
        reason += " (Note: Zero monthly expenses recorded; baseline living reserve could not be verified.)"

    return {
        "decision": "SAFE" if is_safe else "NOT_SAFE",
        "risk_level": risk_level,
        "evidence": {
            "current_balance": paise_to_float(balance_paise),
            "pending_emi": paise_to_float(pending_emi_paise),
            "monthly_expenses": paise_to_float(monthly_expenses_paise),
            "purchase_amount": paise_to_float(sanitized_purchase_paise),
            "emergency_requirement": emergency_requirement,
            "balance_after_purchase": balance_after_purchase,
        },
        "reason": reason,
        "reporting_period": reporting_period,
        "is_sufficient_data": monthly_expenses_paise > 0,
    }


def generate_financial_summary(context, reporting_date=None):
    """
    Assembles comprehensive financial snapshot combining all reasoning components.
    """
    target = _resolve_reporting_date(context, reporting_date)
    savings = calculate_savings_rate(context, target)
    emergency = calculate_emergency_fund(context, target)
    health = calculate_comprehensive_health(context, target)
    categories = calculate_category_expenses(context, target)
    debt = calculate_debt_burden(context, target)

    reporting_period = f"{target.year}-{target.month:02d}"

    return {
        "monthly_income": savings["total_income"],
        "income": savings["total_income"],
        "total_expenses": savings["total_expenses"],
        "expenses": savings["total_expenses"],
        "net_savings": savings["savings"],
        "savings": savings["savings"],
        "savings_rate_pct": savings["savings_rate"],
        "savings_rate": savings["savings_rate"],
        "monthly_expenses": emergency["monthly_expenses"],
        "current_emergency_fund": emergency["current_fund"],
        "recommended_3mo_emergency_fund": emergency["recommended_fund"],
        "recommended_emergency_fund": emergency["recommended_fund"],
        "emergency_fund_shortfall": emergency["shortfall"],
        "financial_health_score": health["health_score"],
        "health_score": health["health_score"],
        "financial_health_grade": health["grade"],
        "health_grade": health["grade"],
        "top_expense_category": categories["top_category"],
        "debt_to_income_dti_pct": debt["dti_ratio"],
        "dti_ratio": debt["dti_ratio"],
        "reporting_period": reporting_period,
        "reporting_date": target.isoformat(),
        "is_sufficient_data": savings["is_sufficient_data"] and emergency["is_sufficient_data"],
        "accounts": context.get("accounts", []) if isinstance(context, dict) else [],
        "goals": context.get("goals", []) if isinstance(context, dict) else [],
    }


def calculate_merchant_expenses(context: dict, merchant_name: str, reporting_date=None) -> dict:
    """
    Computes deterministic expenditure totals for a specific merchant.
    Normalizes case and whitespace, matches against transaction description and merchant fields,
    and distinguishes 'no matching merchant found' from 'confirmed zero spending'.
    Excludes transfers and non-expense records (strictly evaluates t.type == 'EXPENSE').
    """
    m_clean = str(merchant_name or "").strip()
    if not m_clean:
        return {
            "merchant": "",
            "total_spent": 0.0,
            "transaction_count": 0,
            "average_spend": 0.0,
            "transactions": [],
            "reporting_period": "All Time",
            "is_found": False,
            "historical_count": 0,
        }

    m_lower = m_clean.lower()
    pattern = re.compile(rf"\b{re.escape(m_lower)}\b", re.IGNORECASE)

    def matches_merchant(tx: dict) -> bool:
        if not isinstance(tx, dict):
            return False
        desc = str(tx.get("description") or "").strip()
        merch = str(tx.get("merchant") or "").strip()
        if pattern.search(desc) or pattern.search(merch):
            return True
        if len(m_lower) >= 4 and (m_lower in desc.lower() or m_lower in merch.lower()):
            return True
        return False

    all_txs = context.get("transactions", []) if isinstance(context, dict) else []

    # Historical matches across all time for this merchant
    if isinstance(context, dict) and context.get("historical_match_count") is not None:
        historical_count = int(context["historical_match_count"])
    else:
        historical_count = sum(
            1 for tx in all_txs
            if isinstance(tx, dict) and tx.get("type") == "EXPENSE" and matches_merchant(tx)
        )
    is_found = historical_count > 0

    # Date-filtering
    if reporting_date is not None:
        target = _resolve_reporting_date(context, reporting_date)
        reporting_period = f"{target.year}-{target.month:02d}"
        period_txs = [tx for tx in all_txs if _is_in_reporting_month(tx, target)]
    else:
        reporting_period = "All Time"
        period_txs = all_txs

    matching_txs = [
        tx for tx in period_txs
        if isinstance(tx, dict) and tx.get("type") == "EXPENSE" and matches_merchant(tx)
    ]

    total_spent_paise = 0
    for tx in matching_txs:
        amt_p = _get_amount_paise(tx)
        if amt_p > 0:
            total_spent_paise += amt_p

    count = len(matching_txs)
    avg_spend_paise = div_paise(total_spent_paise, count) if count > 0 else 0

    formatted_txs = []
    for tx in sorted(matching_txs, key=lambda x: str(x.get("date", "")), reverse=True):
        formatted_txs.append({
            "id": tx.get("id"),
            "description": tx.get("description"),
            "amount": paise_to_float(_get_amount_paise(tx)),
            "date": str(tx.get("date"))[:10] if tx.get("date") else None,
            "category": tx.get("category"),
            "bank": tx.get("bank"),
            "merchant": tx.get("merchant") or m_clean,
        })

    return {
        "merchant": m_clean,
        "total_spent": paise_to_float(total_spent_paise),
        "transaction_count": count,
        "average_spend": paise_to_float(avg_spend_paise),
        "transactions": formatted_txs,
        "reporting_period": reporting_period,
        "is_found": is_found,
        "historical_count": historical_count,
    }


def calculate_top_transactions(
    context: dict,
    limit: int | None = 5,
    amount_min: float | None = None,
    amount_max: float | None = None,
    reporting_date=None,
) -> dict:
    """
    Computes top-N transactions ranked by amount in descending order,
    supporting optional minimum/maximum amount thresholds and date filters.
    Strictly excludes internal transfers and non-expense records (t.type == 'EXPENSE').
    """
    all_txs = context.get("transactions", []) if isinstance(context, dict) else []

    if reporting_date is not None:
        target = _resolve_reporting_date(context, reporting_date)
        reporting_period = f"{target.year}-{target.month:02d}"
        candidate_txs = [tx for tx in all_txs if _is_in_reporting_month(tx, target)]
    else:
        reporting_period = "All Time"
        candidate_txs = all_txs

    amount_min_paise = _parse_paise(amount_min) if amount_min is not None else None
    amount_max_paise = _parse_paise(amount_max) if amount_max is not None else None

    filtered_txs = []
    for tx in candidate_txs:
        if not isinstance(tx, dict) or tx.get("type") != "EXPENSE":
            continue
        amt_paise = _get_amount_paise(tx)

        if amt_paise <= 0:
            continue
        if amount_min_paise is not None and amt_paise < amount_min_paise:
            continue
        if amount_max_paise is not None and amt_paise > amount_max_paise:
            continue
        filtered_txs.append((tx, amt_paise))

    # Sort descending by numeric amount in paise
    sorted_txs = sorted(filtered_txs, key=lambda x: x[1], reverse=True)

    # Apply limit
    if limit is not None and limit > 0:
        sliced_txs = sorted_txs[:limit]
    else:
        sliced_txs = sorted_txs

    total_selected_paise = sum(item[1] for item in sliced_txs)

    formatted_txs = []
    for tx, amt_paise in sliced_txs:
        formatted_txs.append({
            "id": tx.get("id"),
            "description": tx.get("description"),
            "amount": paise_to_float(amt_paise),
            "date": str(tx.get("date"))[:10] if tx.get("date") else None,
            "category": tx.get("category"),
            "bank": tx.get("bank"),
            "merchant": tx.get("merchant"),
        })

    return {
        "transactions": formatted_txs,
        "total_selected_amount": paise_to_float(total_selected_paise),
        "count": len(formatted_txs),
        "total_matching_count": len(sorted_txs),
        "limit_applied": limit,
        "amount_min": amount_min,
        "amount_max": amount_max,
        "reporting_period": reporting_period,
    }


def calculate_period_comparison(
    context: dict,
    period_a_start=None,
    period_a_end=None,
    period_b_start=None,
    period_b_end=None,
    category: str | None = None,
    merchant: str | None = None,
    first_mentioned: str | None = None,
    second_mentioned: str | None = None,
) -> dict:
    """
    Deterministic comparative expenditure analytics across two explicit date periods.
    Supports:
    - Overall comparison or filtered by category or merchant
    - Identical transaction eligibility and refund/transfer exclusion across both periods
    - Absolute change = period B total minus period A total
    - Percentage change relative to period A when period A is non-zero
    - Safe handling when baseline is zero ("percentage change unavailable because the baseline is zero")
    - Category-wise variance attribution ranking with supporting transactions
    - Auditable date ranges, transaction counts, and source transaction IDs
    """
    today = date.today()

    # 1. Resolve date boundaries
    if period_a_start is None:
        lm_year = today.year if today.month > 1 else today.year - 1
        lm_month = today.month - 1 if today.month > 1 else 12
        period_a_start = date(lm_year, lm_month, 1)
    elif isinstance(period_a_start, str):
        period_a_start = date.fromisoformat(period_a_start[:10])
    elif isinstance(period_a_start, datetime):
        period_a_start = period_a_start.date()

    if period_a_end is None:
        import calendar
        last_day = calendar.monthrange(period_a_start.year, period_a_start.month)[1]
        period_a_end = date(period_a_start.year, period_a_start.month, last_day)
    elif isinstance(period_a_end, str):
        period_a_end = date.fromisoformat(period_a_end[:10])
    elif isinstance(period_a_end, datetime):
        period_a_end = period_a_end.date()

    if period_b_start is None:
        period_b_start = date(today.year, today.month, 1)
    elif isinstance(period_b_start, str):
        period_b_start = date.fromisoformat(period_b_start[:10])
    elif isinstance(period_b_start, datetime):
        period_b_start = period_b_start.date()

    if period_b_end is None:
        import calendar
        last_day = calendar.monthrange(period_b_start.year, period_b_start.month)[1]
        period_b_end = date(period_b_start.year, period_b_start.month, last_day)
    elif isinstance(period_b_end, str):
        period_b_end = date.fromisoformat(period_b_end[:10])
    elif isinstance(period_b_end, datetime):
        period_b_end = period_b_end.date()

    period_a_name = period_a_start.strftime("%B %Y")
    period_b_name = period_b_start.strftime("%B %Y")

    # 2. Setup merchant and category filters
    m_pattern = None
    if merchant:
        m_clean = str(merchant).strip().lower()
        m_pattern = re.compile(rf"\b{re.escape(m_clean)}\b", re.IGNORECASE)

    def _matches_merchant(tx: dict) -> bool:
        if not m_pattern:
            return True
        desc = str(tx.get("description") or "").strip()
        merch = str(tx.get("merchant") or "").strip()
        if m_pattern.search(desc) or m_pattern.search(merch):
            return True
        if len(merchant) >= 4 and (merchant.lower() in desc.lower() or merchant.lower() in merch.lower()):
            return True
        return False

    def _is_eligible_expense(tx: dict, cat_filter: str | None = None) -> bool:
        if not isinstance(tx, dict):
            return False
        if tx.get("type") != "EXPENSE":
            return False
        amt_p = _get_amount_paise(tx)
        if amt_p <= 0:
            return False

        desc = str(tx.get("description") or "").lower()
        c = str(tx.get("category") or "").lower()

        # Strict exclusion of internal transfers
        if c == "transfer" or any(kw in desc for kw in [
            "transfer to", "transfer from", "to a/c", "from a/c",
            "funds transfer", "internal transfer", "neft transfer", "self transfer"
        ]):
            return False

        # Strict exclusion of refunds / credit reversals
        if any(kw in desc for kw in ["refund", "reversal", "cashback"]):
            return False

        if cat_filter and c != cat_filter.strip().lower():
            return False

        if merchant and not _matches_merchant(tx):
            return False

        return True

    def _parse_tx_date(val) -> date | None:
        if not val:
            return None
        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, date):
            return val
        try:
            return date.fromisoformat(str(val)[:10])
        except (ValueError, TypeError):
            return None

    all_txs = context.get("transactions", []) if isinstance(context, dict) else []

    # Filter transactions for both periods using the exact same rules
    period_a_txs = []
    period_b_txs = []
    for tx in all_txs:
        if not _is_eligible_expense(tx, cat_filter=category):
            continue
        d = _parse_tx_date(tx.get("date"))
        if not d:
            continue
        if period_a_start <= d <= period_a_end:
            period_a_txs.append(tx)
        if period_b_start <= d <= period_b_end:
            period_b_txs.append(tx)

    # 3. Deterministic Totals & Variance Calculations
    period_a_total_paise = sum(_get_amount_paise(t) for t in period_a_txs)
    period_b_total_paise = sum(_get_amount_paise(t) for t in period_b_txs)
    period_a_count = len(period_a_txs)
    period_b_count = len(period_b_txs)

    absolute_change_paise = period_b_total_paise - period_a_total_paise
    net_difference_paise = abs(absolute_change_paise)

    if period_a_total_paise > 0:
        r = ratio(absolute_change_paise, period_a_total_paise)
        percentage_change = round(r * 100.0, 2) if r is not None else 0.0
        percentage_change_status = "VALID"
        percentage_change_display = f"{'+' if percentage_change > 0 else ''}{percentage_change:.2f}%"
    else:
        percentage_change = None
        percentage_change_status = "BASELINE_ZERO"
        percentage_change_display = "percentage change unavailable because the baseline is zero"

    if period_b_total_paise > period_a_total_paise:
        higher_period = period_b_name
        comparison_outcome = f"Higher spending in {period_b_name}"
    elif period_a_total_paise > period_b_total_paise:
        higher_period = period_a_name
        comparison_outcome = f"Higher spending in {period_a_name}"
    else:
        higher_period = "EQUAL"
        comparison_outcome = "Equal spending in both periods"

    # 4. Category-Wise Variance Attribution (Part C)
    # Collect eligible transactions across all categories (unfiltered by category to attribute variance)
    var_a_txs = []
    var_b_txs = []
    for tx in all_txs:
        if not _is_eligible_expense(tx, cat_filter=None):
            continue
        d = _parse_tx_date(tx.get("date"))
        if not d:
            continue
        if period_a_start <= d <= period_a_end:
            var_a_txs.append(tx)
        if period_b_start <= d <= period_b_end:
            var_b_txs.append(tx)

    all_categories = sorted(list(set(
        str(t.get("category") or "Uncategorized").title()
        for t in (var_a_txs + var_b_txs)
    )))

    category_variances = []
    for cat in all_categories:
        c_lower = cat.lower()
        cat_a_txs = [t for t in var_a_txs if str(t.get("category") or "Uncategorized").lower() == c_lower]
        cat_b_txs = [t for t in var_b_txs if str(t.get("category") or "Uncategorized").lower() == c_lower]
        spent_a_paise = sum(_get_amount_paise(t) for t in cat_a_txs)
        spent_b_paise = sum(_get_amount_paise(t) for t in cat_b_txs)
        diff_paise = spent_b_paise - spent_a_paise

        if spent_a_paise > 0:
            r_c = ratio(diff_paise, spent_a_paise)
            c_pct = round(r_c * 100.0, 2) if r_c is not None else 0.0
            c_pct_display = f"{'+' if c_pct > 0 else ''}{c_pct:.2f}%"
        else:
            c_pct = None
            c_pct_display = "N/A (baseline was ₹0)" if spent_b_paise > 0 else "0.00%"

        total_net_paise = net_difference_paise if category is None else abs(diff_paise)
        r_contrib = ratio(abs(diff_paise), total_net_paise) if total_net_paise > 0 else None
        contrib_pct = round(r_contrib * 100.0, 2) if r_contrib is not None else 0.0

        # Supporting transactions (largest purchases in that category)
        if diff_paise > 0:
            supp_candidates = sorted(cat_b_txs, key=lambda x: _get_amount_paise(x), reverse=True)[:3]
        elif diff_paise < 0:
            supp_candidates = sorted(cat_a_txs, key=lambda x: _get_amount_paise(x), reverse=True)[:3]
        else:
            supp_candidates = []

        supporting_txs = [
            {
                "id": tx.get("id"),
                "description": tx.get("description"),
                "amount": paise_to_float(_get_amount_paise(tx)),
                "date": str(tx.get("date"))[:10] if tx.get("date") else None,
            }
            for tx in supp_candidates
        ]

        spent_a = paise_to_float(spent_a_paise)
        spent_b = paise_to_float(spent_b_paise)
        diff = paise_to_float(diff_paise)

        category_variances.append({
            "category": cat,
            "period_a_spent": spent_a,
            "period_b_spent": spent_b,
            "absolute_difference": diff,
            "percentage_change": c_pct,
            "percentage_change_display": c_pct_display,
            "contribution_weight_pct": contrib_pct,
            "supporting_transactions": supporting_txs,
            "mathematical_contribution_note": (
                f"Category '{cat}' changed by ₹{abs(diff):,.2f} ({'+' if diff > 0 else ''}{diff:,.2f}), "
                f"accounting for {contrib_pct:.1f}% mathematical contribution to the total change."
            ),
        })

    # Sort variances by magnitude of difference
    category_variances.sort(key=lambda x: abs(x["absolute_difference"]), reverse=True)
    top_increases = sorted([c for c in category_variances if c["absolute_difference"] > 0], key=lambda x: x["absolute_difference"], reverse=True)
    top_decreases = sorted([c for c in category_variances if c["absolute_difference"] < 0], key=lambda x: x["absolute_difference"])

    # 5. Verbal explanation and caveats
    if category:
        subject = f"on {category}"
    elif merchant:
        subject = f"on {merchant}"
    else:
        subject = "overall"

    pct_phrase = f" ({percentage_change_display})" if percentage_change_status == "VALID" else f" ({percentage_change_display})"

    period_a_total = paise_to_float(period_a_total_paise)
    period_b_total = paise_to_float(period_b_total_paise)
    absolute_change = paise_to_float(absolute_change_paise)
    net_difference = paise_to_float(net_difference_paise)

    if absolute_change_paise > 0:
        verdict = f"Your spending {subject} increased by ₹{net_difference:,.2f}{pct_phrase} from {period_a_name} (₹{period_a_total:,.2f}) to {period_b_name} (₹{period_b_total:,.2f})."
    elif absolute_change_paise < 0:
        verdict = f"Your spending {subject} decreased by ₹{net_difference:,.2f}{pct_phrase} from {period_a_name} (₹{period_a_total:,.2f}) to {period_b_name} (₹{period_b_total:,.2f})."
    else:
        verdict = f"Your spending {subject} was equal across {period_a_name} and {period_b_name} at ₹{period_a_total:,.2f}."

    period_a_tx_ids = [str(tx["id"]) for tx in period_a_txs if tx.get("id")]
    period_b_tx_ids = [str(tx["id"]) for tx in period_b_txs if tx.get("id")]

    caveats = []
    if period_a_count == 0 and period_b_count == 0:
        caveats.append("No eligible expense transactions were found for either period.")
    elif period_a_count == 0:
        caveats.append(f"Baseline period {period_a_name} had ₹0 spending; percentage change is mathematically unavailable.")
    elif period_b_count == 0:
        caveats.append(f"Comparison period {period_b_name} had zero eligible transactions recorded.")

    return {
        "period_a": {
            "name": period_a_name,
            "start_date": str(period_a_start),
            "end_date": str(period_a_end),
            "total_spent": period_a_total,
            "transaction_count": period_a_count,
        },
        "period_b": {
            "name": period_b_name,
            "start_date": str(period_b_start),
            "end_date": str(period_b_end),
            "total_spent": period_b_total,
            "transaction_count": period_b_count,
        },
        "category": category,
        "merchant": merchant,
        "absolute_change": absolute_change,
        "net_difference": net_difference,
        "percentage_change": percentage_change,
        "percentage_change_status": percentage_change_status,
        "percentage_change_display": percentage_change_display,
        "higher_period": higher_period,
        "comparison_outcome": comparison_outcome,
        "comparison_verdict": verdict,
        "category_variances": category_variances,
        "top_increases": top_increases,
        "top_decreases": top_decreases,
        "period_a_tx_ids": period_a_tx_ids,
        "period_b_tx_ids": period_b_tx_ids,
        "caveats": caveats,
        "is_sufficient_data": (period_a_count > 0 or period_b_count > 0),
        "reporting_period": f"{period_a_name} vs {period_b_name}",
    }


def calculate_spending_trends(
    context: dict,
    num_months: int = 6,
    end_date=None,
) -> dict:
    """
    Computes chronological monthly spending totals and transaction counts.
    Distinguishes genuine confirmed zero spend from missing data or incomplete statement coverage.
    Never assumes an absent month means the user spent nothing.
    """
    import calendar
    today = date.today()

    if end_date is None:
        end_date = today
    elif isinstance(end_date, str):
        end_date = date.fromisoformat(end_date[:10])
    elif isinstance(end_date, datetime):
        end_date = end_date.date()

    num_months = max(1, min(36, int(num_months)))

    # Determine the target chronological list of month tuples [(year, month)]
    target_months = []
    curr_y = end_date.year
    curr_m = end_date.month
    for _ in range(num_months):
        target_months.append((curr_y, curr_m))
        if curr_m == 1:
            curr_y -= 1
            curr_m = 12
        else:
            curr_m -= 1
    target_months.reverse()  # Chronological order from oldest to newest

    def _is_eligible_expense(tx: dict) -> bool:
        if not isinstance(tx, dict):
            return False
        if tx.get("type") != "EXPENSE":
            return False
        amt_p = _get_amount_paise(tx)
        if amt_p <= 0:
            return False

        desc = str(tx.get("description") or "").lower()
        c = str(tx.get("category") or "").lower()

        if c == "transfer" or any(kw in desc for kw in [
            "transfer to", "transfer from", "to a/c", "from a/c",
            "funds transfer", "internal transfer", "neft transfer", "self transfer"
        ]):
            return False
        if any(kw in desc for kw in ["refund", "reversal", "cashback"]):
            return False
        return True

    def _parse_tx_date(val) -> date | None:
        if not val:
            return None
        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, date):
            return val
        try:
            return date.fromisoformat(str(val)[:10])
        except (ValueError, TypeError):
            return None

    all_txs = context.get("transactions", []) if isinstance(context, dict) else []
    all_dates = []
    for tx in all_txs:
        if _is_eligible_expense(tx):
            d = _parse_tx_date(tx.get("date"))
            if d:
                all_dates.append(d)

    dataset_start = min(all_dates) if all_dates else None
    dataset_end = max(all_dates) if all_dates else None

    points = []
    covered_spends_paise = []
    for y, m in target_months:
        last_day = calendar.monthrange(y, m)[1]
        m_start = date(y, m, 1)
        m_end = date(y, m, last_day)
        m_name = m_start.strftime("%B %Y")
        m_code = f"{y}-{m:02d}"

        # Coverage evaluation: Check if this month is covered by the user's dataset
        if dataset_start is None or dataset_end is None:
            is_covered = False
        else:
            # A month is covered if it falls within the span of known statement dates
            is_covered = (m_end >= dataset_start and m_start <= dataset_end)

        if not is_covered:
            status = "DATA_UNAVAILABLE"
            coverage_note = "No statement data available for this month"
            spent_paise = 0
            count = 0
            tx_ids = []
        else:
            m_txs = [
                tx for tx in all_txs
                if _is_eligible_expense(tx) and m_start <= _parse_tx_date(tx.get("date")) <= m_end
            ]
            spent_paise = sum(_get_amount_paise(tx) for tx in m_txs)
            count = len(m_txs)
            tx_ids = [str(tx.get("id")) for tx in m_txs if tx.get("id")]
            if count > 0:
                status = "CONFIRMED_SPEND"
                coverage_note = "Verified statement records present"
            else:
                status = "CONFIRMED_ZERO"
                coverage_note = "Statement period covered; confirmed zero expenditure"

            covered_spends_paise.append(spent_paise)

        points.append({
            "month": m_code,
            "month_name": m_name,
            "start_date": str(m_start),
            "end_date": str(m_end),
            "total_spent": paise_to_float(spent_paise),
            "transaction_count": count,
            "status": status,
            "is_covered": is_covered,
            "coverage_note": coverage_note,
            "transaction_ids": tx_ids[:10],
        })

    covered_points = [p for p in points if p["status"] != "DATA_UNAVAILABLE"]
    unavailable_points = [p for p in points if p["status"] == "DATA_UNAVAILABLE"]

    # Compute average spend exclusively over covered months to prevent falsified deflation
    if covered_spends_paise:
        total_covered_paise = sum(covered_spends_paise)
        average_spend_paise = div_paise(total_covered_paise, len(covered_spends_paise))
        average_spend = paise_to_float(average_spend_paise)
    else:
        average_spend = 0.0

    if len(covered_spends_paise) >= 2:
        first_val = covered_spends_paise[0]
        last_val = covered_spends_paise[-1]
        if last_val > first_val:
            trend_direction = "UPWARD"
        elif last_val < first_val:
            trend_direction = "DOWNWARD"
        else:
            trend_direction = "STABLE"
    else:
        trend_direction = "INSUFFICIENT_DATA"

    caveats = []
    if unavailable_points:
        un_names = [p["month_name"] for p in unavailable_points]
        caveats.append(
            f"Data is unavailable for {len(un_names)} of {len(points)} evaluated months ({', '.join(un_names)}). "
            "These periods are not assumed to have zero spend."
        )
    if not covered_points:
        caveats.append("No statement or transaction records were found for the requested period.")

    return {
        "trend_points": points,
        "total_months_evaluated": len(points),
        "available_months_count": len(covered_points),
        "missing_months_count": len(unavailable_points),
        "coverage_start": points[0]["month_name"],
        "coverage_end": points[-1]["month_name"],
        "average_monthly_spend": average_spend,
        "trend_direction": trend_direction,
        "caveats": caveats,
        "is_sufficient_data": len(covered_points) > 0,
        "reporting_period": f"{points[0]['month_name']} to {points[-1]['month_name']}",
    }



