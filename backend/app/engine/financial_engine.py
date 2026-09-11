from datetime import date, datetime


def _is_in_reporting_month(record, reporting_date=None):
    """Return whether a dated income/transaction belongs to the reporting month."""
    value = record.get("date")
    if not value:
        return False
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        record_date = value
    else:
        try:
            record_date = date.fromisoformat(str(value))
        except ValueError:
            return False
    reporting_date = reporting_date or date.today()
    return (record_date.year, record_date.month) == (reporting_date.year, reporting_date.month)


def _monthly_transactions(context, reporting_date=None):
    return [
        tx for tx in context.get("transactions", [])
        if _is_in_reporting_month(tx, reporting_date)
    ]


def _monthly_incomes(context, reporting_date=None):
    return [
        income for income in context.get("incomes", [])
        if _is_in_reporting_month(income, reporting_date)
    ]


def calculate_category_expenses(context, reporting_date=None):
    """
    Computes category-wise expense breakdown, proportions, and largest spending category.
    """
    category_totals = {}
    total_expenses = 0.0

    for tx in _monthly_transactions(context, reporting_date):
        if tx.get("type") == "EXPENSE":
            cat = tx.get("category") or "Uncategorized"
            amount = float(tx.get("amount", 0))
            category_totals[cat] = category_totals.get(cat, 0.0) + amount
            total_expenses += amount

    breakdown = []
    for cat, amount in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
        percentage = round((amount / total_expenses * 100), 2) if total_expenses > 0 else 0.0
        breakdown.append({
            "category": cat,
            "amount": amount,
            "percentage": percentage
        })

    top_category = breakdown[0]["category"] if breakdown else "None"
    top_amount = breakdown[0]["amount"] if breakdown else 0.0

    return {
        "total_expenses": total_expenses,
        "categories": breakdown,
        "top_category": top_category,
        "top_amount": top_amount
    }

def calculate_emergency_fund(context, reporting_date=None):
    monthly_expenses = sum(
        transaction["amount"]
        for transaction in _monthly_transactions(context, reporting_date)
        if transaction.get("type") == "EXPENSE"
    )

    recommended_fund = monthly_expenses * 3

    emergency_goal = next(
        (goal for goal in context.get("goals", []) if (goal.get("name") or goal.get("goal") or "").lower() == "emergency fund"),
        None,
    )
    current_fund = emergency_goal.get("current", 0) if emergency_goal else 0

    shortfall = max(0, recommended_fund - current_fund)

    return {
        "monthly_expenses": monthly_expenses,
        "recommended_fund": recommended_fund,
        "current_fund": current_fund,
        "shortfall": shortfall
    }

def calculate_emergency_runway(context, reporting_date=None):
    """
    Calculates available emergency runway in months based on current balance and monthly expenses.
    """
    accounts = context.get("accounts", [])
    balance = sum(float(account.get("balance", 0)) for account in accounts)
    
    monthly_expenses = sum(
        tx["amount"]
        for tx in _monthly_transactions(context, reporting_date)
        if tx.get("type") == "EXPENSE"
    )

    if monthly_expenses == 0:
        runway_months = 12.0
    else:
        runway_months = round(balance / monthly_expenses, 2)

    if runway_months >= 6.0:
        status = "STRONG"
    elif runway_months >= 3.0:
        status = "HEALTHY"
    elif runway_months >= 1.0:
        status = "INSUFFICIENT"
    else:
        status = "CRITICAL"

    return {
        "current_balance": balance,
        "monthly_expenses": monthly_expenses,
        "runway_months": runway_months,
        "status": status,
        "target_runway_months": 3.0
    }

def calculate_savings_rate(context, reporting_date=None):
    total_income = sum(
        income["amount"]
        for income in _monthly_incomes(context, reporting_date)
    )

    total_expenses = sum(
        transaction["amount"]
        for transaction in _monthly_transactions(context, reporting_date)
        if transaction.get("type") == "EXPENSE"
    )

    savings = total_income - total_expenses

    if total_income == 0:
        savings_rate = 0.0
    else:
        savings_rate = (savings / total_income) * 100

    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "savings": savings,
        "savings_rate": round(savings_rate, 2)
    }

def calculate_debt_burden(context, reporting_date=None):
    """
    Calculates total outstanding debt, monthly EMI obligations, and Debt-to-Income (DTI) ratio.
    """
    total_income = sum(
        income["amount"]
        for income in _monthly_incomes(context, reporting_date)
    )

    loans = context.get("loans", [])
    total_outstanding = sum(float(l.get("outstanding", 0)) for l in loans)
    monthly_emi = sum(
        float(loan.get("emi", 0))
        for loan in loans
        if loan.get("status") == "PENDING" and (
            not loan.get("due_date") or _is_in_reporting_month({"date": loan["due_date"]}, reporting_date)
        )
    )

    dti_ratio = round((monthly_emi / total_income * 100), 2) if total_income > 0 else 0.0

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

    return {
        "total_outstanding_debt": total_outstanding,
        "monthly_emi": monthly_emi,
        "dti_ratio": dti_ratio,
        "risk_level": risk,
        "assessment": assessment
    }

def calculate_comprehensive_health(context, reporting_date=None):
    """
    Evaluates complete financial health score (0-100) combining savings, emergency reserve, and debt metrics.
    """
    savings = calculate_savings_rate(context, reporting_date)
    runway = calculate_emergency_runway(context, reporting_date)
    debt = calculate_debt_burden(context, reporting_date)
    emergency = calculate_emergency_fund(context, reporting_date)

    # 1. Savings score (max 35 pts) - 20% savings gives full score
    savings_score = min(35.0, (savings["savings_rate"] / 20.0) * 35.0)

    # 2. Emergency Runway score (max 35 pts) - 3 months gives full score
    runway_score = min(35.0, (runway["runway_months"] / 3.0) * 35.0)

    # 3. Debt score (max 30 pts) - DTI < 20% gives 30 pts, > 50% gives 0 pts
    if debt["dti_ratio"] <= 20.0:
        debt_score = 30.0
    elif debt["dti_ratio"] >= 50.0:
        debt_score = 0.0
    else:
        debt_score = 30.0 - ((debt["dti_ratio"] - 20.0) / 30.0 * 30.0)

    total_score = round(savings_score + runway_score + debt_score, 1)

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
        "emergency_shortfall": emergency["shortfall"]
    }

def check_purchase_safety(context, purchase_amount, reporting_date=None):
    accounts = context.get("accounts", [])
    balance = sum(float(account.get("balance", 0)) for account in accounts)

    pending_emi = sum(
        loan["emi"]
        for loan in context.get("loans", [])
        if loan.get("status") == "PENDING" and (
            not loan.get("due_date") or _is_in_reporting_month({"date": loan["due_date"]}, reporting_date)
        )
    )

    monthly_expenses = sum(
        transaction["amount"]
        for transaction in _monthly_transactions(context, reporting_date)
        if transaction.get("type") == "EXPENSE"
    )

    emergency_requirement = monthly_expenses * 3

    balance_after_purchase = (
        balance
        - pending_emi
        - purchase_amount
    )

    is_safe = balance_after_purchase >= emergency_requirement

    if balance_after_purchase >= emergency_requirement:
        risk_level = "LOW"
    elif balance_after_purchase >= monthly_expenses:
        risk_level = "MEDIUM"
    elif balance_after_purchase > 0:
        risk_level = "HIGH"
    else:
        risk_level = "VERY_HIGH"

    if is_safe:
        reason = (
            f"The purchase is financially safe. "
            f"After the pending EMI and purchase, "
            f"₹{balance_after_purchase:,} would remain, "
            f"which is above the recommended emergency "
            f"reserve of ₹{emergency_requirement:,}."
        )
    else:
        reason = (
            f"The purchase is not financially safe. "
            f"After the pending EMI and purchase, "
            f"only ₹{balance_after_purchase:,} would remain, "
            f"which is below the recommended emergency "
            f"reserve of ₹{emergency_requirement:,}."
        )

    return {
        "decision": "SAFE" if is_safe else "NOT_SAFE",
        "risk_level": risk_level,
        "evidence": {
            "current_balance": balance,
            "pending_emi": pending_emi,
            "monthly_expenses": monthly_expenses,
            "purchase_amount": purchase_amount,
            "emergency_requirement": emergency_requirement,
            "balance_after_purchase": balance_after_purchase
        },
        "reason": reason
    }

def generate_financial_summary(context, reporting_date=None):
    savings = calculate_savings_rate(context, reporting_date)
    emergency = calculate_emergency_fund(context, reporting_date)
    health = calculate_comprehensive_health(context, reporting_date)
    categories = calculate_category_expenses(context, reporting_date)
    debt = calculate_debt_burden(context, reporting_date)

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
        "accounts": context.get("accounts", []),
        "goals": context.get("goals", []),
    }
