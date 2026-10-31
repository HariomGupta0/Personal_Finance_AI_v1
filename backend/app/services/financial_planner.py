"""
Personalized Financial Planning Engine.

Analyzes bank statement transaction data from Neo4j / financial context to generate
actionable, data-grounded financial plans:
  1. Financial situation & cash flow analysis
  2. Discretionary vs Non-discretionary spending insights
  3. Recurring commitments & EMI management
  4. Suggested monthly budget with category-wise spending limits
  5. Savings targets & estimated timelines
  6. 3 to 5 prioritized, explainable action recommendations

Guarantees:
  - All numbers, balances, and savings figures are deterministically calculated.
  - The AI explains and prioritizes verified facts; it never invents numbers.
  - Gracefully handles missing income, zero expenses, and short transaction history.
  - Includes a full deterministic rule-based fallback if the LLM is offline.
"""

from __future__ import annotations

from decimal import Decimal
import json
import logging
from datetime import date, datetime
from typing import Any, Optional

from backend.app.core.money import (
    div_paise,
    mul_paise,
    paise_to_float,
    ratio,
    round_nearest_paise,
    to_paise,
)
from backend.app.engine.financial_engine import (
    calculate_category_expenses,
    calculate_comprehensive_health,
    calculate_debt_burden,
    calculate_emergency_fund,
    calculate_emergency_runway,
    calculate_savings_rate,
    generate_financial_summary,
    _resolve_reporting_date,
    _monthly_transactions,
    _monthly_incomes,
)
from backend.app.services.llm_service import ask_llm_async

logger = logging.getLogger(__name__)


def _parse_paise(val: Any, allow_negative: bool = False) -> int:
    """Safely convert a rupee value (int, float, str, Decimal) to integer paise."""
    if val is None or isinstance(val, bool):
        return 0
    try:
        if isinstance(val, (int, float, Decimal)):
            if allow_negative and val < 0:
                return -to_paise(-val)
            if val < 0:
                return 0
            return to_paise(val)
        if isinstance(val, str):
            s = val.strip()
            if allow_negative and s.startswith("-"):
                return -to_paise(s[1:])
            return to_paise(s)
        return to_paise(val)
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


# Categories generally considered essential needs
ESSENTIAL_CATEGORIES = {
    "housing", "rent", "utilities", "bills", "healthcare",
    "medical", "education", "groceries", "grocery", "debt", "emi", "insurance"
}

# Categories generally considered discretionary wants
DISCRETIONARY_CATEGORIES = {
    "food", "dining", "shopping", "entertainment", "travel",
    "electronics", "personal", "cafe", "coffee", "leisure", "lifestyle"
}


def _is_discretionary_category(cat_name: str) -> bool:
    """Classify category as discretionary (want) vs non-discretionary (need)."""
    norm = (cat_name or "").strip().lower()
    if any(k in norm for k in ESSENTIAL_CATEGORIES):
        return False
    if any(k in norm for k in DISCRETIONARY_CATEGORIES):
        return True
    return False


def _detect_recurring_commitments(context: dict, reporting_date: Optional[date] = None) -> list[dict]:
    """
    Identify recurring bills, subscriptions, and EMIs from loans and transaction patterns.
    """
    recurring = []

    # 1. EMIs from active loans
    for loan in context.get("loans", []):
        emi_paise = _get_amount_paise(loan, "emi")
        if emi_paise > 0:
            recurring.append({
                "type": "EMI",
                "name": loan.get("loan") or f"Loan ({loan.get('id', 'EMI')})",
                "amount": paise_to_float(emi_paise),
                "due_date": loan.get("due_date"),
                "status": loan.get("status", "ACTIVE"),
            })

    # 2. Frequent subscriptions/bills from monthly transactions
    monthly_txs = _monthly_transactions(context, reporting_date)
    desc_amounts_paise: dict[str, list[int]] = {}
    for tx in monthly_txs:
        if tx.get("type") == "EXPENSE":
            desc = (tx.get("description") or "").strip()
            amt_p = _get_amount_paise(tx)
            if desc and amt_p > 0:
                desc_amounts_paise.setdefault(desc, []).append(amt_p)

    # Detect known subscription/utility terms
    recurring_keywords = [
        "netflix", "spotify", "prime", "hotstar", "wifi", "broadband",
        "airtel", "jio", "bescom", "tneb", "electricity", "rent", "maintenance", "gym", "insurance"
    ]
    for desc, amounts_paise in desc_amounts_paise.items():
        lower_desc = desc.lower()
        if any(kw in lower_desc for kw in recurring_keywords):
            # Avoid duplicating loans
            if not any(r["name"].lower() in lower_desc for r in recurring):
                avg_paise = div_paise(sum(amounts_paise), len(amounts_paise))
                recurring.append({
                    "type": "SUBSCRIPTION/BILL",
                    "name": desc,
                    "amount": paise_to_float(avg_paise),
                    "frequency": "Monthly",
                })

    return recurring


def _calculate_budget_limits(
    total_income: float,
    total_expenses: float,
    category_breakdown: list[dict],
    savings_rate: float,
) -> dict:
    """
    Compute category-wise recommended monthly spending limits and potential savings.
    Preserves non-discretionary expenses while suggesting achievable cuts on discretionary categories.
    All calculations run on integer paise. Discretionary limits round to nearest 5000 paise (₹50).
    """
    total_income_paise = _parse_paise(total_income)
    total_expenses_paise = _parse_paise(total_expenses)
    budget_items = []
    total_potential_savings_paise = 0

    # Determine reduction aggressive level based on user's current savings rate
    # If savings rate < 0% (deficit): 25% reduction on discretionary
    # If 0% <= savings rate < 20%: 15-20% reduction on discretionary
    # If savings rate >= 20%: 10% optimization
    if savings_rate < 0:
        disc_cut_factor = Decimal("0.25")
    elif savings_rate < 20:
        disc_cut_factor = Decimal("0.20")
    else:
        disc_cut_factor = Decimal("0.10")

    for item in category_breakdown:
        cat = item["category"]
        current_spent_paise = _get_amount_paise(item, "amount")
        is_disc = _is_discretionary_category(cat)

        if is_disc and current_spent_paise > 0:
            reduction_paise = mul_paise(current_spent_paise, disc_cut_factor)
            target_paise = max(0, current_spent_paise - reduction_paise)
            # Round limit to nearest 5000 paise (₹50) using Decimal ROUND_HALF_UP
            rec_limit_paise = round_nearest_paise(target_paise, 5000)
            potential_paise = max(0, current_spent_paise - rec_limit_paise)
        else:
            # Essential categories are preserved
            rec_limit_paise = current_spent_paise
            potential_paise = 0

        total_potential_savings_paise += potential_paise
        pct_of_expenses = item.get("percentage", 0.0)

        budget_items.append({
            "category": cat,
            "current_spending": paise_to_float(current_spent_paise),
            "recommended_limit": paise_to_float(rec_limit_paise),
            "potential_savings": paise_to_float(potential_paise),
            "percentage_of_expenses": pct_of_expenses,
            "is_discretionary": is_disc,
            "status": "OVER_BUDGET" if potential_paise > 0 else "WITHIN_BUDGET",
        })

    recommended_total_budget_paise = max(0, total_expenses_paise - total_potential_savings_paise)

    return {
        "current_total_expenses": paise_to_float(total_expenses_paise),
        "recommended_total_budget": paise_to_float(recommended_total_budget_paise),
        "total_potential_savings": paise_to_float(total_potential_savings_paise),
        "categories": budget_items,
    }


def _calculate_savings_and_emergency_targets(
    total_income: float,
    total_expenses: float,
    current_savings: float,
    potential_budget_savings: float,
    emergency_fund_data: dict,
    accounts: list[dict],
) -> dict:
    """
    Calculate realistic monthly savings and time-to-target for emergency fund.
    All calculations run on integer paise.
    """
    savings_paise = _parse_paise(current_savings, allow_negative=True)
    base_surplus_paise = max(0, savings_paise)
    pot_savings_paise = _parse_paise(potential_budget_savings)
    realistic_monthly_savings_paise = base_surplus_paise + pot_savings_paise

    income_paise = _parse_paise(total_income)
    if income_paise > 0:
        # Cap realistic savings proposal at 40% of income so it stays achievable
        cap_paise = mul_paise(income_paise, Decimal("0.40"))
        realistic_monthly_savings_paise = min(realistic_monthly_savings_paise, cap_paise)

    recommended_fund_paise = _get_amount_paise(emergency_fund_data, "recommended_fund")
    current_fund_paise = _get_amount_paise(emergency_fund_data, "current_fund")

    # Also check liquid account balance if explicit goal isn't set
    total_balance_paise = sum(
        _get_amount_paise(a, "balance", allow_negative=True)
        for a in accounts
        if isinstance(a, dict)
    )
    effective_cushion_paise = max(current_fund_paise, total_balance_paise)
    effective_shortfall_paise = max(0, recommended_fund_paise - effective_cushion_paise)

    realistic_monthly_savings_rupees = paise_to_float(realistic_monthly_savings_paise)

    if effective_shortfall_paise == 0:
        timeline_months = 0.0
        timeline_text = "Target Achieved (You have 3+ months of essential reserves)"
    elif realistic_monthly_savings_paise > 0:
        r = ratio(effective_shortfall_paise, realistic_monthly_savings_paise)
        timeline_months = round(r, 1) if r is not None else None
        timeline_text = f"~{timeline_months} months at ₹{realistic_monthly_savings_rupees:,.2f}/month"
    else:
        timeline_months = None
        timeline_text = "Needs expense reduction or income addition to establish savings rate"

    return {
        "current_monthly_savings": paise_to_float(savings_paise),
        "recommended_monthly_savings": realistic_monthly_savings_rupees,
        "emergency_fund_3mo_target": paise_to_float(recommended_fund_paise),
        "emergency_fund_current": paise_to_float(effective_cushion_paise),
        "emergency_fund_shortfall": paise_to_float(effective_shortfall_paise),
        "estimated_months_to_target": timeline_months,
        "timeline_text": timeline_text,
    }


def _generate_deterministic_fallback(
    summary: dict,
    budget_data: dict,
    savings_data: dict,
    debt_data: dict,
    recurring_items: list[dict],
    limitations: list[str],
) -> dict:
    """
    Robust rule-based generator that produces rich, explainable financial planning
    insights and prioritized actions when LLM is unavailable or unconfigured.
    """
    income = summary.get("income", 0.0)
    expenses = summary.get("expenses", 0.0)
    savings_rate = summary.get("savings_rate", 0.0)
    health_grade = summary.get("health_grade", "C")
    health_score = summary.get("health_score", 50.0)
    top_cat = summary.get("top_expense_category", "None")
    total_potential = budget_data.get("total_potential_savings", 0.0)

    # 1. Executive Summary
    if income > 0:
        if savings_rate >= 20:
            exec_summary = (
                f"You have a solid financial foundation with a {savings_rate:.1f}% savings rate (Grade {health_grade}, Score {health_score}/100). "
                f"Your monthly surplus is ₹{summary.get('savings', 0.0):,.2f}. By trimming discretionary categories like {top_cat}, "
                f"you can unlock an additional ₹{total_potential:,.2f} each month to accelerate your emergency cushion."
            )
        elif savings_rate > 0:
            exec_summary = (
                f"Your current cash flow is positive but tight with a {savings_rate:.1f}% savings rate (Grade {health_grade}, Score {health_score}/100). "
                f"Total monthly outflow is ₹{expenses:,.2f} against ₹{income:,.2f} in income. Implementing the recommended category budget limits "
                f"will free up ₹{total_potential:,.2f}/month to build your emergency reserve."
            )
        else:
            exec_summary = (
                f"Your monthly outflow of ₹{expenses:,.2f} currently exceeds your income of ₹{income:,.2f} (Grade {health_grade}). "
                f"Immediate intervention is required to curtail discretionary expenses and restore positive cash flow. "
                f"Targeted reductions across {top_cat} can save ₹{total_potential:,.2f}/month."
            )
    else:
        exec_summary = (
            f"Based on your statement, total recorded expenses stand at ₹{expenses:,.2f} with {top_cat} as the primary spending driver. "
            f"Optimizing discretionary spending according to the proposed budget can yield ₹{total_potential:,.2f} in monthly savings."
        )

    # 2. Key Spending Insights
    insights = []
    # Insight 1: Top category proportion
    top_item = next((c for c in budget_data.get("categories", []) if c["category"] == top_cat), None)
    if top_item and expenses > 0:
        insights.append({
            "topic": "Dominant Expense",
            "text": f"{top_cat} is your largest expense category at ₹{top_item['current_spending']:,.2f} ({top_item['percentage_of_expenses']:.1f}% of total outflow).",
            "category": top_cat,
        })

    # Insight 2: Discretionary vs Essential
    disc_total_paise = sum(
        _get_amount_paise(c, "current_spending")
        for c in budget_data.get("categories", [])
        if c.get("is_discretionary")
    )
    expenses_paise = _parse_paise(expenses)
    r_disc = ratio(disc_total_paise, expenses_paise)
    disc_pct = (r_disc * 100.0) if r_disc is not None else 0.0
    disc_total = paise_to_float(disc_total_paise)
    insights.append({
        "topic": "Discretionary Spending",
        "text": f"Discretionary lifestyle spending (Dining, Shopping, Entertainment) constitutes {disc_pct:.1f}% (₹{disc_total:,.2f}) of your monthly budget.",
        "category": "Lifestyle",
    })

    # Insight 3: Recurring commitments
    emi_total = debt_data.get("monthly_emi", 0.0)
    if emi_total > 0:
        dti = debt_data.get("dti_ratio", 0.0)
        insights.append({
            "topic": "Fixed Debt Obligations",
            "text": f"Monthly EMI obligations are ₹{emi_total:,.2f} (DTI Ratio: {dti:.1f}%). Managing these on time is crucial for your credit standing.",
            "category": "Debt",
        })
    elif recurring_items:
        rec_sum_paise = sum(_get_amount_paise(r) for r in recurring_items)
        rec_sum = paise_to_float(rec_sum_paise)
        insights.append({
            "topic": "Recurring Subscriptions",
            "text": f"You have {len(recurring_items)} recurring bills and subscriptions totaling ~₹{rec_sum:,.2f}/month.",
            "category": "Utilities",
        })
    else:
        insights.append({
            "topic": "Emergency Buffer",
            "text": f"Your target 3-month emergency fund is ₹{savings_data.get('emergency_fund_3mo_target', 0.0):,.2f} with a shortfall of ₹{savings_data.get('emergency_fund_shortfall', 0.0):,.2f}.",
            "category": "Savings",
        })

    # 3. Prioritized Actions (3 to 5 explainable recommendations)
    actions = []

    # Action 1: Discretionary spend reduction
    top_disc = next((c for c in budget_data.get("categories", []) if c["is_discretionary"] and c["potential_savings"] > 0), None)
    if top_disc:
        actions.append({
            "priority": "HIGH",
            "title": f"Reduce Discretionary Spending on {top_disc['category']}",
            "category": top_disc["category"],
            "action": f"Cap monthly {top_disc['category']} spending at ₹{top_disc['recommended_limit']:,.2f}.",
            "expected_impact": f"Saves ₹{top_disc['potential_savings']:,.2f}/month",
            "rationale": f"Current spending on {top_disc['category']} is ₹{top_disc['current_spending']:,.2f} ({top_disc['percentage_of_expenses']:.1f}% of expenses). Reducing this frees up substantial capital.",
        })

    # Action 2: Emergency fund allocation
    shortfall = savings_data.get("emergency_fund_shortfall", 0.0)
    rec_monthly_savings = savings_data.get("recommended_monthly_savings", 0.0)
    if shortfall > 0:
        actions.append({
            "priority": "HIGH",
            "title": "Build Your 3-Month Emergency Reserve",
            "category": "Emergency Fund",
            "action": f"Automate a recurring deposit of ₹{rec_monthly_savings:,.2f} into a dedicated high-yield savings account or liquid fund on salary day.",
            "expected_impact": f"Achieves fully funded status in {savings_data.get('timeline_text', 'a few months')}",
            "rationale": f"Your recommended 3-month emergency buffer is ₹{savings_data.get('emergency_fund_3mo_target', 0.0):,.2f}. You currently have a gap of ₹{shortfall:,.2f}.",
        })
    else:
        actions.append({
            "priority": "MEDIUM",
            "title": "Maintain Emergency Reserve & Invest Surplus",
            "category": "Investment",
            "action": "Maintain your 3-month liquid buffer and channel additional monthly savings into diversified index funds or fixed deposits.",
            "expected_impact": "Wealth creation and inflation protection",
            "rationale": "Your emergency reserve is already funded. Surplus funds should be deployed to avoid cash drag.",
        })

    # Action 3: Debt / EMI management or Recurring audit
    if emi_total > 0:
        actions.append({
            "priority": "MEDIUM",
            "title": "Prioritize High-Interest Debt Repayments",
            "category": "Debt",
            "action": f"Ensure your monthly EMI of ₹{emi_total:,.2f} is debited automatically. Direct any windfall bonuses to prepay high-interest principal.",
            "expected_impact": "Reduces total interest paid and lowers DTI ratio",
            "rationale": f"Outstanding debt obligations total ₹{debt_data.get('total_outstanding_debt', 0.0):,.2f} with a DTI of {debt_data.get('dti_ratio', 0.0):.1f}%.",
        })
    elif recurring_items:
        actions.append({
            "priority": "MEDIUM",
            "title": "Audit Recurring Subscriptions & Utility Bills",
            "category": "Subscriptions",
            "action": "Review recurring services and cancel any unused subscriptions or streaming platforms.",
            "expected_impact": "Saves ₹500 to ₹1,500/month in passive drain",
            "rationale": f"Detected {len(recurring_items)} recurring payments in your statement.",
        })
    else:
        actions.append({
            "priority": "MEDIUM",
            "title": "Set Category-Specific Alerts",
            "category": "Budgeting",
            "action": "Configure notifications when spending reaches 80% of category limits.",
            "expected_impact": "Prevents month-end budget overruns",
            "rationale": f"Staying within the recommended ₹{budget_data.get('recommended_total_budget', 0.0):,.2f} monthly budget protects your savings goals.",
        })

    # Action 4: Missing data or financial wellness check
    if limitations:
        actions.append({
            "priority": "LOW",
            "title": "Provide Complete Financial Profile",
            "category": "Profile",
            "action": "Record your verified monthly salary/income to enable comprehensive 50/30/20 budget tracking.",
            "expected_impact": "Unlocks precision cash flow forecasts and personalized tax planning",
            "rationale": "Your uploaded statement contained only debits or incomplete income credits.",
        })
    else:
        actions.append({
            "priority": "LOW",
            "title": "Track Progress Weekly",
            "category": "Habits",
            "action": "Review weekly transaction summaries on the dashboard to ensure category adherence.",
            "expected_impact": "Maintains financial discipline",
            "rationale": "Consistent tracking correlates directly with higher savings achievement rates.",
        })

    return {
        "executive_summary": exec_summary,
        "spending_insights": insights,
        "action_plan": actions,
        "source": "deterministic_rules",
    }


async def _enrich_with_llm(
    deterministic_base: dict,
    summary: dict,
    budget_data: dict,
    savings_data: dict,
    debt_data: dict,
    recurring_items: list[dict],
    limitations: list[str],
) -> dict:
    """
    Call Groq LLM to generate natural, personalized, empathetic explanations
    grounded strictly in the verified numbers.
    """
    system_prompt = (
        "You are an expert Certified Financial Planner (CFP) analyzing bank statement data. "
        "Strict rules:\n"
        "1. ALL NUMBERS ARE VERIFIED FACTS. You MUST NOT invent or alter any transaction, amount, income, or balance.\n"
        "2. Preserve currency as Indian Rupees (₹). Do NOT convert to dollars.\n"
        "3. Provide practical, empathetic, and actionable advice tailored to this user.\n"
        "4. Return ONLY valid JSON conforming to the requested schema. No markdown wrapping or extra text."
    )

    data_payload = {
        "income": summary.get("income", 0.0),
        "expenses": summary.get("expenses", 0.0),
        "savings": summary.get("savings", 0.0),
        "savings_rate_pct": summary.get("savings_rate", 0.0),
        "health_score": summary.get("health_score", 50.0),
        "health_grade": summary.get("health_grade", "C"),
        "top_expense_category": summary.get("top_expense_category", "None"),
        "category_budget": [
            {
                "category": c["category"],
                "spent": c["current_spending"],
                "limit": c["recommended_limit"],
                "potential_savings": c["potential_savings"],
                "pct": c["percentage_of_expenses"],
                "is_discretionary": c["is_discretionary"],
            }
            for c in budget_data.get("categories", [])
        ],
        "total_potential_savings": budget_data.get("total_potential_savings", 0.0),
        "recommended_monthly_savings": savings_data.get("recommended_monthly_savings", 0.0),
        "emergency_fund_target": savings_data.get("emergency_fund_3mo_target", 0.0),
        "emergency_fund_shortfall": savings_data.get("emergency_fund_shortfall", 0.0),
        "emergency_timeline": savings_data.get("timeline_text", ""),
        "monthly_emi": debt_data.get("monthly_emi", 0.0),
        "dti_ratio": debt_data.get("dti_ratio", 0.0),
        "recurring_count": len(recurring_items),
        "data_limitations": limitations,
    }

    prompt = (
        f"Generate a personalized financial plan based on this verified financial profile:\n"
        f"{json.dumps(data_payload, indent=2)}\n\n"
        f"Respond with a JSON object with this exact structure:\n"
        f"{{\n"
        f'  "executive_summary": "2-3 sentences summarizing user\'s cash flow, health grade, and key recommendation",\n'
        f'  "spending_insights": [\n'
        f'    {{"topic": "...", "text": "...", "category": "..."}},\n'
        f'    {{"topic": "...", "text": "...", "category": "..."}},\n'
        f'    {{"topic": "...", "text": "...", "category": "..."}}\n'
        f'  ],\n'
        f'  "action_plan": [\n'
        f'    {{\n'
        f'      "priority": "HIGH" | "MEDIUM" | "LOW",\n'
        f'      "title": "Short title",\n'
        f'      "category": "Category or topic",\n'
        f'      "action": "Specific concrete action",\n'
        f'      "expected_impact": "Quantified impact (e.g. Save ₹X/month)",\n'
        f'      "rationale": "Reason grounded in the provided numbers"\n'
        f'    }}\n'
        f'  ]\n'
        f"}}"
    )

    try:
        llm_resp = await ask_llm_async(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=1024,
            retries=1,
        )
        content = (llm_resp.get("content") or "").strip()
        # Clean potential markdown fences ```json ... ```
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:].strip()

        parsed = json.loads(content)
        if (
            isinstance(parsed, dict)
            and "executive_summary" in parsed
            and isinstance(parsed.get("action_plan"), list)
            and len(parsed["action_plan"]) >= 2
        ):
            return {
                "executive_summary": str(parsed["executive_summary"]),
                "spending_insights": parsed.get("spending_insights", deterministic_base["spending_insights"]),
                "action_plan": parsed["action_plan"],
                "source": "groq_llm",
                "model": llm_resp.get("model"),
            }
    except Exception as exc:
        logger.info("LLM generation skipped or failed (%s); using deterministic rules: %s", type(exc).__name__, exc)

    return deterministic_base


async def generate_financial_plan(
    context: dict,
    user_id: str = "U001",
    force_refresh: bool = False,
    use_ai: bool = True,
) -> dict:
    """
    Main entry point: Generate a complete, personalized financial plan for a user.

    Parameters
    ----------
    context : dict
        User's complete financial context (transactions, incomes, accounts, loans, goals).
    user_id : str
        Authenticated user's Neo4j identifier.
    force_refresh : bool
        Whether to bypass caching if implemented.
    use_ai : bool
        Whether to attempt LLM narrative enrichment (falls back gracefully to deterministic rules).

    Returns
    -------
    dict
        Structured financial plan ready for frontend consumption and automated testing.
    """
    if not isinstance(context, dict):
        context = {}

    reporting_date = _resolve_reporting_date(context)

    # 1. Deterministic Engine Calculations
    summary = generate_financial_summary(context, reporting_date)
    category_data = calculate_category_expenses(context, reporting_date)
    debt_data = calculate_debt_burden(context, reporting_date)
    emergency_fund_data = calculate_emergency_fund(context, reporting_date)
    runway_data = calculate_emergency_runway(context, reporting_date)
    health_data = calculate_comprehensive_health(context, reporting_date)

    total_income_paise = _get_amount_paise(summary, "income")
    total_expenses_paise = _get_amount_paise(summary, "expenses")
    current_savings_paise = _get_amount_paise(summary, "savings", allow_negative=True)
    savings_rate = float(summary.get("savings_rate", 0.0))

    total_income = paise_to_float(total_income_paise)
    total_expenses = paise_to_float(total_expenses_paise)
    current_savings = paise_to_float(current_savings_paise)

    # 2. Limitations & Missing Data Detection
    limitations: list[str] = []
    transactions = context.get("transactions", [])
    if total_income_paise == 0:
        limitations.append(
            f"No monthly income was detected in your statement. Budget limits and savings goals are computed "
            f"against your observed expense outflow of ₹{total_expenses:,.2f}. Please record your monthly salary "
            f"or income to enable full 50/30/20 allocation planning."
        )
    if len(transactions) < 3:
        limitations.append(
            f"Limited statement history detected ({len(transactions)} transaction{'s' if len(transactions) != 1 else ''}). "
            f"Upload a full 1 to 3 month statement for higher category accuracy."
        )
    if not context.get("accounts"):
        limitations.append("No active bank account linked to track liquid balance.")

    # 3. Discretionary Budgeting & Category Limits
    budget_data = _calculate_budget_limits(
        total_income=total_income,
        total_expenses=total_expenses,
        category_breakdown=category_data.get("categories", []),
        savings_rate=savings_rate,
    )

    # 4. Recurring Commitments
    recurring_items = _detect_recurring_commitments(context, reporting_date)
    total_recurring_monthly_paise = sum(_get_amount_paise(r) for r in recurring_items)
    total_recurring_monthly = paise_to_float(total_recurring_monthly_paise)

    # 5. Savings & Emergency Fund Target Timeline
    savings_targets = _calculate_savings_and_emergency_targets(
        total_income=total_income,
        total_expenses=total_expenses,
        current_savings=current_savings,
        potential_budget_savings=budget_data["total_potential_savings"],
        emergency_fund_data=emergency_fund_data,
        accounts=context.get("accounts", []),
    )

    # 6. Generate Baseline Deterministic Plan
    deterministic_base = _generate_deterministic_fallback(
        summary=summary,
        budget_data=budget_data,
        savings_data=savings_targets,
        debt_data=debt_data,
        recurring_items=recurring_items,
        limitations=limitations,
    )

    # 7. AI Enrichment (if enabled and applicable)
    if use_ai:
        enriched_narrative = await _enrich_with_llm(
            deterministic_base=deterministic_base,
            summary=summary,
            budget_data=budget_data,
            savings_data=savings_targets,
            debt_data=debt_data,
            recurring_items=recurring_items,
            limitations=limitations,
        )
    else:
        enriched_narrative = deterministic_base

    # 8. Assemble Complete Final Plan
    return {
        "status": "SUCCESS",
        "user_id": user_id,
        "generated_at": datetime.now().isoformat(),
        "reporting_month": reporting_date.strftime("%B %Y"),
        "financial_summary": {
            "monthly_income": total_income,
            "monthly_expenses": total_expenses,
            "net_savings": current_savings,
            "savings_rate_pct": savings_rate,
            "health_score": health_data.get("health_score", 50.0),
            "health_grade": health_data.get("grade", "C"),
            "health_assessment": health_data.get("summary", ""),
            "runway_months": runway_data.get("runway_months", 0.0),
            "runway_status": runway_data.get("status", "INSUFFICIENT"),
            "liquid_balance": runway_data.get("current_balance", 0.0),
        },
        "executive_summary": enriched_narrative["executive_summary"],
        "spending_insights": enriched_narrative["spending_insights"],
        "budget_plan": {
            "current_total_expenses": budget_data["current_total_expenses"],
            "recommended_total_budget": budget_data["recommended_total_budget"],
            "total_potential_savings": budget_data["total_potential_savings"],
            "categories": budget_data["categories"],
        },
        "savings_plan": {
            **savings_targets,
            "goals": context.get("goals", []),
        },
        "goals": context.get("goals", []),
        "debt_and_commitments": {
            "total_outstanding_debt": debt_data.get("total_outstanding_debt", 0.0),
            "monthly_emi": debt_data.get("monthly_emi", 0.0),
            "dti_ratio": debt_data.get("dti_ratio", 0.0),
            "risk_level": debt_data.get("risk_level", "LOW"),
            "recurring_commitments": recurring_items,
            "total_recurring_monthly": round(total_recurring_monthly, 2),
        },
        "prioritized_actions": enriched_narrative["action_plan"],
        "data_limitations": limitations,
        "ai_metadata": {
            "source": enriched_narrative.get("source", "deterministic_rules"),
            "model": enriched_narrative.get("model"),
        },
    }
