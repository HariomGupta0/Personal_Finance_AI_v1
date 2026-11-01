import re
import json
from datetime import date
from decimal import Decimal

from backend.app.core.money import normalize_rupees
from backend.app.nlu.transaction_extractor import infer_category

MONTH_NAMES = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9, "october": 10,
    "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12
}

WORD_TO_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "fifteen": 15, "twenty": 20
}


def extract_merchant(text: str) -> tuple[str | None, list[str]]:
    """
    Extracts canonical merchant name from natural language query.
    Returns (matched_canonical_merchant, all_matched_merchants).
    Checks known merchants with word-boundary matching and common merchant phrasings.
    """
    from backend.app.services.merchant_normalizer import KNOWN_MERCHANTS
    t_lower = text.lower()
    matches: list[str] = []

    # 1. Exact / canonical match against KNOWN_MERCHANTS dictionary
    for key, (canonical, _) in KNOWN_MERCHANTS.items():
        pattern = r"\b" + re.escape(key) + r"\b"
        if re.search(pattern, t_lower):
            if canonical not in matches:
                matches.append(canonical)

    # 2. Extract merchant names from explicit relationship phrasings
    # e.g. "belong to Uber", "payments to Netflix", "transactions for Swiggy"
    m_belong = re.search(
        r"\b(?:belong(?:s)?\s+to|payments?\s+(?:to|for)|paid\s+to|bought\s+from|orders?\s+(?:on|from))\s+([A-Za-z0-9]+)\b",
        t_lower,
    )
    if m_belong:
        cand = m_belong.group(1).title()
        excluded_words = {
            "me", "my", "account", "category", "them", "us", "him", "her",
            "food", "rent", "grocery", "groceries", "travel", "transport",
            "shopping", "utilities", "bills", "cash", "bank"
        }
        if cand.lower() not in excluded_words and cand not in matches:
            matches.append(cand)

    if not matches:
        return (None, [])
    if len(matches) == 1:
        return (matches[0], matches)
    return (None, matches)


def extract_top_n_and_thresholds(text: str) -> dict | None:
    """
    Extracts top-N limits and amount thresholds from transaction queries.
    Handles 'top 5', 'five biggest', 'expenses above ₹5,000', 'between 1000 and 3000', etc.
    """
    t_lower = text.lower()

    # Keywords indicating a ranking or filtering of individual transaction items
    has_top_kw = any(kw in t_lower for kw in [
        "biggest expense", "biggest purchase", "largest expense", "largest purchase",
        "highest expense", "highest purchase", "biggest transaction", "largest transaction",
        "top expense", "top purchase", "top transaction", "most expensive"
    ])
    has_threshold_kw = any(kw in t_lower for kw in [
        "above", "over", "greater than", "more than", "exceeding",
        "below", "under", "less than", "between", "cheaper than"
    ]) and any(kw in t_lower for kw in ["expense", "purchase", "transaction", "payment", "spend", "cost"])

    m_top = re.search(r"\b(?:top|first)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b", t_lower)
    m_n_biggest = re.search(
        r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:biggest|largest|highest|greatest|most expensive)\b",
        t_lower,
    )

    if not (has_top_kw or has_threshold_kw or m_top or m_n_biggest):
        return None

    # Resolve limit
    limit = None
    if m_top:
        val = m_top.group(1)
        limit = int(val) if val.isdigit() else WORD_TO_NUM.get(val.lower())
    elif m_n_biggest:
        val = m_n_biggest.group(1)
        limit = int(val) if val.isdigit() else WORD_TO_NUM.get(val.lower())
    elif has_top_kw:
        limit = 5

    # Resolve amount thresholds
    amount_min = None
    amount_max = None

    # Between pattern: "between ₹1,000 and ₹3,000" or "between 1000 and 3000"
    m_between = re.search(
        r"\bbetween\s+(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)\s*(?:and|-|to)\s*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)\b",
        t_lower,
    )
    if m_between:
        try:
            a1 = normalize_rupees(Decimal(m_between.group(1).replace(",", "")))
            a2 = normalize_rupees(Decimal(m_between.group(2).replace(",", "")))
            amount_min = min(a1, a2)
            amount_max = max(a1, a2)
        except (ValueError, Exception):
            pass
    else:
        # Above / Over / More than: "above ₹5,000", "over 5000"
        m_above = re.search(
            r"\b(?:above|over|greater than|more than|exceeding|minimum of|at least)\s+(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)\b",
            t_lower,
        )
        if m_above:
            try:
                amount_min = normalize_rupees(Decimal(m_above.group(1).replace(",", "")))
            except (ValueError, Exception):
                pass

        # Below / Under / Less than: "under ₹2,000", "below 1500"
        m_below = re.search(
            r"\b(?:below|under|less than|maximum of|at most|cheaper than)\s+(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?)\b",
            t_lower,
        )
        if m_below:
            try:
                amount_max = normalize_rupees(Decimal(m_below.group(1).replace(",", "")))
            except (ValueError, Exception):
                pass

    return {
        "limit": limit,
        "amount_min": amount_min,
        "amount_max": amount_max,
        "sort_by": "amount",
        "sort_direction": "DESC",
    }



def extract_temporal_reporting_date(text: str) -> date | None:
    """
    Extracts an explicit month/year or relative month (e.g. 'last month') from natural language.
    Returns a date object pointing to the 1st of that month, or None.
    """
    t_lower = text.lower()
    today = date.today()

    # Relative: "last month", "previous month"
    if "last month" in t_lower or "previous month" in t_lower:
        if today.month == 1:
            return date(today.year - 1, 12, 1)
        return date(today.year, today.month - 1, 1)

    # Explicit: "september 2025" or "in september 2025"
    m_full = re.search(r"\b(" + "|".join(MONTH_NAMES.keys()) + r")\s+(\d{4})\b", t_lower)
    if m_full:
        month_num = MONTH_NAMES[m_full.group(1)]
        year_num = int(m_full.group(2))
        return date(year_num, month_num, 1)

    # ISO Year-Month: "2025-08"
    m_iso = re.search(r"\b(\d{4})-(0[1-9]|1[0-2])\b", t_lower)
    if m_iso:
        return date(int(m_iso.group(1)), int(m_iso.group(2)), 1)

    # Named month without year: "in september", "for august"
    m_month = re.search(r"\b(?:in|for|during)\s+(" + "|".join(MONTH_NAMES.keys()) + r")\b", t_lower)
    if m_month:
        month_num = MONTH_NAMES[m_month.group(1)]
        year = today.year if month_num <= today.month else today.year - 1
        return date(year, month_num, 1)

    return None


def extract_comparison_periods(text: str) -> dict | None:
    """
    Extracts two distinct comparison periods (Period A baseline, Period B comparison)
    from natural language questions. Supports:
    - Explicit month comparisons: "September than October", "in August and September 2026", "September vs October"
    - Relative comparisons: "this month compared with last month", "this month vs last month"
    - ISO month comparisons: "2026-08 and 2026-09"
    - Variance attribution queries: "Why did my expenses increase?", "Which categories increased the most?"
    - Detection of ambiguous single-period comparisons or comparisons of a month to itself.
    """
    t_lower = text.lower()
    today = date.today()

    is_comparative = any(kw in t_lower for kw in [
        "compare", "comparison", "more in", "less in", "higher in", "lower in",
        "than in", "than", "vs", "versus", "compared to", "compared with",
        "increased the most", "decreased the most", "increase the most", "decrease the most",
        "why did my expenses", "why did my spending", "what caused the difference",
        "which categories increased", "which categories decreased", "where did expenses increase"
    ])

    # 1. ISO format: "2026-08 and 2026-09" or "2026-08 vs 2026-09"
    iso_matches = re.findall(r"\b(20\d{2})-(0[1-9]|1[0-2])\b", t_lower)
    if len(iso_matches) >= 2:
        d1 = date(int(iso_matches[0][0]), int(iso_matches[0][1]), 1)
        d2 = date(int(iso_matches[1][0]), int(iso_matches[1][1]), 1)
        if d1 == d2:
            return {
                "is_match": True,
                "needs_clarification": True,
                "clarification_type": "AMBIGUOUS_PERIOD",
                "clarification_message": "Period comparison requires two distinct periods to calculate variance.",
            }
        p_a = min(d1, d2)
        p_b = max(d1, d2)
        return {
            "is_match": True,
            "period_a": p_a,
            "period_b": p_b,
            "first_mentioned": f"{iso_matches[0][0]}-{iso_matches[0][1]}",
            "second_mentioned": f"{iso_matches[1][0]}-{iso_matches[1][1]}",
            "needs_clarification": False,
        }

    # 2. Relative Month Pairs
    has_this_month = any(kw in t_lower for kw in ["this month", "current month"])
    has_last_month = any(kw in t_lower for kw in ["last month", "previous month", "past month"])
    has_two_months_ago = any(kw in t_lower for kw in ["two months ago", "2 months ago"])

    if has_this_month and has_last_month:
        lm_year = today.year if today.month > 1 else today.year - 1
        lm_month = today.month - 1 if today.month > 1 else 12
        p_a = date(lm_year, lm_month, 1)
        p_b = date(today.year, today.month, 1)
        return {
            "is_match": True,
            "period_a": p_a,
            "period_b": p_b,
            "first_mentioned": "this month",
            "second_mentioned": "last month",
            "needs_clarification": False,
        }

    if has_last_month and has_two_months_ago:
        m2_year = today.year if today.month > 2 else today.year - 1
        m2_month = today.month - 2 if today.month > 2 else (today.month - 2 + 12)
        lm_year = today.year if today.month > 1 else today.year - 1
        lm_month = today.month - 1 if today.month > 1 else 12
        p_a = date(m2_year, m2_month, 1)
        p_b = date(lm_year, lm_month, 1)
        return {
            "is_match": True,
            "period_a": p_a,
            "period_b": p_b,
            "first_mentioned": "last month",
            "second_mentioned": "two months ago",
            "needs_clarification": False,
        }

    # 3. Explicit Named Months
    month_keys = sorted(MONTH_NAMES.keys(), key=lambda x: -len(x))
    pattern = r"\b(" + "|".join(month_keys) + r")(?:\s+(\d{4}))?\b"
    matches = list(re.finditer(pattern, t_lower))

    global_year = None
    m_year = re.search(r"\b(20\d{2})\b", t_lower)
    if m_year:
        global_year = int(m_year.group(1))

    if len(matches) >= 2:
        m1_name = matches[0].group(1)
        m1_year = int(matches[0].group(2)) if matches[0].group(2) else global_year or today.year
        m1_num = MONTH_NAMES[m1_name]

        m2_name = matches[1].group(1)
        m2_year = int(matches[1].group(2)) if matches[1].group(2) else global_year or today.year
        m2_num = MONTH_NAMES[m2_name]

        d1 = date(m1_year, m1_num, 1)
        d2 = date(m2_year, m2_num, 1)

        if d1 == d2:
            return {
                "is_match": True,
                "needs_clarification": True,
                "clarification_type": "AMBIGUOUS_PERIOD",
                "clarification_message": "Period comparison requires two distinct periods to calculate variance.",
            }

        p_a = min(d1, d2)
        p_b = max(d1, d2)
        return {
            "is_match": True,
            "period_a": p_a,
            "period_b": p_b,
            "first_mentioned": f"{m1_name.title()} {m1_year}",
            "second_mentioned": f"{m2_name.title()} {m2_year}",
            "needs_clarification": False,
        }

    # 4. Variance attribution inquiries without explicit months
    is_variance_inquiry = any(kw in t_lower for kw in [
        "which categories increased", "which categories decreased",
        "categories increased the most", "categories decreased the most",
        "why did my expenses increase", "why did my spending increase",
        "what caused the difference", "why did my expenses go up", "why did expenses increase"
    ])
    if is_variance_inquiry:
        lm_year = today.year if today.month > 1 else today.year - 1
        lm_month = today.month - 1 if today.month > 1 else 12
        p_a = date(lm_year, lm_month, 1)
        p_b = date(today.year, today.month, 1)
        return {
            "is_match": True,
            "period_a": p_a,
            "period_b": p_b,
            "first_mentioned": "last month",
            "second_mentioned": "this month",
            "needs_clarification": False,
            "is_variance_attribution": True,
        }

    # 5. Check if a single month is mentioned alongside strong comparative phrasing
    if is_comparative and len(matches) == 1:
        single_m = matches[0].group(1).title()
        return {
            "is_match": True,
            "needs_clarification": True,
            "clarification_type": "AMBIGUOUS_PERIOD",
            "clarification_message": f"Which month would you like to compare {single_m} against? (e.g. '{single_m} compared to August' or '{single_m} compared to October').",
        }

    return None


def extract_spending_trend(text: str) -> dict | None:
    """
    Extracts multi-month spending trend intent and month span from questions such as:
    - "Show my spending trend over the last six months."
    - "How much did I spend each month this year?"
    - "Monthly spending trend"
    """
    t_lower = text.lower()
    today = date.today()

    is_trend_kw = any(kw in t_lower for kw in [
        "spending trend", "expense trend", "expenses trend", "trend of my spending",
        "trend over the last", "trend over the past", "monthly spending trend",
        "monthly expense trend", "spending each month", "expenses each month",
        "spend each month", "each month this year", "every month this year",
        "monthly breakdown for this year", "monthly breakdown over"
    ])
    if not is_trend_kw:
        return None

    if "this year" in t_lower:
        num_months = today.month
        return {
            "is_match": True,
            "trend_months": max(1, num_months),
        }

    m_num = re.search(r"\b(?:last|past|over)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten|twelve)\s+months\b", t_lower)
    if m_num:
        val = m_num.group(1)
        num = int(val) if val.isdigit() else WORD_TO_NUM.get(val, 6)
        return {
            "is_match": True,
            "trend_months": max(1, min(36, num)),
        }

    return {
        "is_match": True,
        "trend_months": 6,
    }


def extract_explicit_category(text: str) -> str | None:
    """
    Extracts an explicit expense category from text only if specifically named or keyed.
    Does not assume a generic or miscellaneous category fallback.
    """
    t_lower = text.lower()
    from backend.app.nlu.transaction_extractor import CATEGORY_KEYWORDS
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if re.search(r"\b" + re.escape(cat.lower()) + r"\b", t_lower):
            return cat
        for kw in keywords:
            if kw.lower() in ["uber", "ola", "swiggy", "zomato", "amazon", "flipkart", "netflix", "prime", "hotstar"]:
                continue
            if re.search(r"\b" + re.escape(kw.lower()) + r"\b", t_lower):
                return cat
    return None


def check_date_ambiguity(text: str) -> tuple[date | None, bool, str | None]:
    """
    Checks for ambiguous date representations (e.g., 04/05/2025 where both day and month <= 12).
    Returns (parsed_date, is_ambiguous, clarification_message).
    """
    t_lower = text.lower()

    # Match numeric slash or hyphen dates: DD/MM/YYYY or MM/DD/YYYY
    m_num = re.search(r"\b(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{2,4}))?\b", t_lower)
    if m_num:
        # Avoid false positive on ISO format YYYY-MM
        if not re.search(r"\b\d{4}-(?:0[1-9]|1[0-2])\b", t_lower):
            p1 = int(m_num.group(1))
            p2 = int(m_num.group(2))
            if 1 <= p1 <= 12 and 1 <= p2 <= 12 and p1 != p2:
                matched_str = m_num.group(0)
                msg = (
                    f"The date '{matched_str}' is ambiguous (could be {p1:02d}/{p2:02d} or {p2:02d}/{p1:02d}). "
                    "Please specify the date as YYYY-MM-DD or write out the month name (e.g., 'May 2025')."
                )
                return (None, True, msg)

    parsed_date = extract_temporal_reporting_date(text)
    return (parsed_date, False, None)


def extract_candidate_amounts(text: str, exclude_years: list[int] | None = None) -> list[float]:
    """
    Extracts candidate monetary amounts from text.
    Handles currency symbols (₹, Rs, INR), suffixes (k, thousand, lakh, crore), and bare numbers.
    Ignores percentages and calendar years.
    """
    exclude_years = exclude_years or []
    t_lower = text.lower()
    amounts: list[float] = []
    matched_spans: list[tuple[int, int]] = []

    def _overlaps(start: int, end: int) -> bool:
        return any(s < end and start < e for s, e in matched_spans)

    # 1. Multipliers with k, thousand, lakh, crore (e.g. 15k, 1.5 lakh, 2.5 crore)
    mult_pattern = re.compile(
        r"(?:(?:₹|rs\.?|inr)\s*)?(\d+(?:\.\d+)?)\s*(k|thousand|lakhs?|lacs?|lac|crores?|cr)\b",
        re.IGNORECASE,
    )
    for m in mult_pattern.finditer(t_lower):
        num_dec = Decimal(m.group(1))
        unit = m.group(2).lower()
        if unit in ["k", "thousand"]:
            amounts.append(normalize_rupees(num_dec * Decimal("1000")))
        elif unit in ["lakh", "lakhs", "lac", "lacs"]:
            amounts.append(normalize_rupees(num_dec * Decimal("100000")))
        elif unit in ["crore", "crores", "cr"]:
            amounts.append(normalize_rupees(num_dec * Decimal("10000000")))
        matched_spans.append(m.span())

    # 2. Currency prefixed numbers: e.g. ₹15,000, Rs. 20000
    curr_pattern = re.compile(r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)
    for m in curr_pattern.finditer(t_lower):
        if _overlaps(*m.span()):
            continue
        val_str = m.group(1).replace(",", "")
        try:
            val = normalize_rupees(Decimal(val_str))
            if val not in amounts and val > 0:
                amounts.append(val)
            matched_spans.append(m.span())
        except (ValueError, Exception):
            pass

    # 3. Bare numbers: e.g. "for 50000", "50000"
    num_pattern = re.compile(r"\b\d{1,3}(?:,\d{2,3})+(?:\.\d{1,2})?\b|\b\d+(?:\.\d{1,2})?\b")
    for m in num_pattern.finditer(t_lower):
        if _overlaps(*m.span()):
            continue
        end_idx = m.end()
        if end_idx < len(t_lower) and t_lower[end_idx:end_idx + 2].strip().startswith("%"):
            continue
        val_str = m.group(0).replace(",", "")
        try:
            val = normalize_rupees(Decimal(val_str))
            if val <= 0:
                continue
            # Filter out 4-digit years (1990-2099)
            if 1990 <= val <= 2099 and (int(val) in exclude_years or re.search(r"\b(?:in|for|year|during)\s+" + re.escape(m.group(0)), t_lower)):
                continue
            # If it's a small integer (< 100) without currency or spending context, ignore (e.g. "2 cars", "3 months")
            if val < 100 and not any(kw in t_lower for kw in ["for", "cost", "costs", "price", "spend", "bought", "pay"]):
                continue
            if val not in amounts:
                amounts.append(val)
                matched_spans.append(m.span())
        except (ValueError, Exception):
            pass

    return amounts


def _extract_prev_user_context(conversation_history: list[dict] | None) -> dict:
    """
    Extracts relevant entity and intent context strictly from previous USER turns.
    Assistant turns are explicitly ignored so that AI prose or hypothetical assertions
    are never treated as authoritative financial facts.
    """
    if not conversation_history:
        return {}

    for turn in reversed(conversation_history):
        if not isinstance(turn, dict):
            continue
        role = str(turn.get("role", "")).strip().lower()
        if role != "user":
            continue
        content = turn.get("content", "")
        if not content or not isinstance(content, str):
            continue

        c_lower = content.lower()
        prev_date = extract_temporal_reporting_date(content)
        prev_cat = infer_category(content)
        if prev_cat == "General":
            prev_cat = None

        prev_intent = None
        if (any(kw in c_lower for kw in ["buy", "purchase", "afford", "spend"]) and any(kw in c_lower for kw in ["can i", "should i", "could i", "am i able to", "is it safe", "afford"])) or any(kw in c_lower for kw in ["can i buy", "can i spend", "can i afford", "should i buy"]):
            prev_intent = "PURCHASE_SAFETY"
        elif any(kw in c_lower for kw in ["spend on", "spent on", "expense on", "cost of"]):
            prev_intent = "CATEGORY_EXPENSE"
        elif any(kw in c_lower for kw in ["spend the most", "where did i spend", "expense breakdown", "top expense"]):
            prev_intent = "EXPENSE_BREAKDOWN"
        elif any(kw in c_lower for kw in ["savings rate", "saving rate", "how much am i saving", "how much do i save"]):
            prev_intent = "SAVINGS_ANALYSIS"
        elif any(kw in c_lower for kw in ["runway", "survive", "months of coverage"]):
            prev_intent = "EMERGENCY_RUNWAY_ANALYSIS"
        elif any(kw in c_lower for kw in ["emergency fund", "emergency reserve", "emergency target"]):
            prev_intent = "EMERGENCY_FUND_ANALYSIS"
        elif any(kw in c_lower for kw in ["debt", "loan", "emi", "dti"]):
            prev_intent = "DEBT_ANALYSIS"
        elif any(kw in c_lower for kw in ["health score", "financial health"]):
            prev_intent = "FINANCIAL_HEALTH"
        elif any(kw in c_lower for kw in ["summary", "overview", "situation"]):
            prev_intent = "FINANCIAL_SUMMARY"

        amounts = extract_candidate_amounts(content)
        prev_amt = amounts[0] if amounts else None
        was_missing_amount = (prev_intent == "PURCHASE_SAFETY" and prev_amt is None)

        return {
            "content": content,
            "intent": prev_intent,
            "category": prev_cat,
            "amount": prev_amt,
            "reporting_date": prev_date,
            "was_missing_amount": was_missing_amount,
        }

    return {}


def parse_question_rules(question: str, conversation_history: list[dict] | None = None) -> dict | None:
    q = question.strip()
    q_lower = q.lower()
    q_clean = q_lower.rstrip("?.! ")

    # 1. Date and Ambiguity Check
    reporting_date, is_date_ambiguous, date_clarification = check_date_ambiguity(q)
    year_to_exclude = [reporting_date.year] if reporting_date else []
    candidate_amounts = extract_candidate_amounts(q, exclude_years=year_to_exclude)

    # 2. Extract Prior User Context (never trust assistant messages as facts)
    prev_ctx = _extract_prev_user_context(conversation_history)
    prev_intent = prev_ctx.get("intent")
    prev_category = prev_ctx.get("category")
    prev_amount = prev_ctx.get("amount")
    prev_reporting_date = prev_ctx.get("reporting_date")
    was_missing_amount = prev_ctx.get("was_missing_amount", False)

    # ─────────────────────────────────────────────────────────────────────────
    # A. Date Ambiguity Handling
    # ─────────────────────────────────────────────────────────────────────────
    if is_date_ambiguous:
        return {
            "intent": prev_intent or "UNKNOWN",
            "amount": candidate_amounts[0] if candidate_amounts else None,
            "category": prev_category or infer_category(q_lower),
            "reporting_date": None,
            "raw_query": q,
            "is_followup": bool(prev_intent),
            "turn_type": "FOLLOW_UP" if prev_intent else "NEW_TOPIC",
            "needs_clarification": True,
            "clarification_type": "AMBIGUOUS_DATE",
            "clarification_message": date_clarification,
            "is_date_ambiguous": True,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # B. Transaction Ingestion Detection (e.g. "I spent ₹500 on food today")
    # ─────────────────────────────────────────────────────────────────────────
    if any(q_lower.startswith(prefix) for prefix in ["i spent", "spent", "paid for", "bought", "received salary", "earned"]) or \
       (any(kw in q_lower for kw in ["spent", "paid", "debited"]) and any(kw in q_lower for kw in ["today", "yesterday", "on", "for"]) and not any(kw in q_lower for kw in ["can i", "how much", "what is", "where"])):
        amt = candidate_amounts[0] if candidate_amounts else None
        return {
            "intent": "TRANSACTION_INGESTION",
            "amount": amt,
            "category": infer_category(q_lower),
            "reporting_date": reporting_date,
            "raw_query": q,
            "is_followup": False,
            "turn_type": "NEW_TOPIC",
            "needs_clarification": amt is None,
            "clarification_type": "MISSING_AMOUNT" if amt is None else None,
            "clarification_message": "Please specify the transaction amount." if amt is None else None,
            "is_date_ambiguous": False,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # C. Follow-up: Modified Purchase Amount or Clarification Answer
    # e.g. "what if it costs ₹25,000?", "how about ₹30000?", "₹20,000", "what if it is 15000"
    # ─────────────────────────────────────────────────────────────────────────
    is_purchase_mod_phrase = any(kw in q_lower for kw in ["what if it costs", "how about", "what if it is", "and if it's", "what if i buy", "what if"])
    is_bare_amount_reply = was_missing_amount and len(candidate_amounts) > 0 and len(q.split()) <= 5

    if (is_purchase_mod_phrase and len(candidate_amounts) > 0) or is_bare_amount_reply:
        if len(candidate_amounts) > 1:
            return {
                "intent": "PURCHASE_SAFETY",
                "amount": None,
                "category": prev_category or infer_category(q_lower),
                "reporting_date": reporting_date or prev_reporting_date,
                "raw_query": q,
                "is_followup": True,
                "turn_type": "FOLLOW_UP",
                "needs_clarification": True,
                "clarification_type": "AMBIGUOUS_AMOUNT",
                "clarification_message": f"Multiple amounts detected ({', '.join(f'₹{int(a):,}' for a in candidate_amounts)}). Please specify a single purchase amount.",
                "is_date_ambiguous": False,
            }
        new_amt = candidate_amounts[0]
        return {
            "intent": "PURCHASE_SAFETY",
            "amount": new_amt,
            "category": prev_category or infer_category(q_lower),
            "reporting_date": reporting_date or prev_reporting_date,
            "raw_query": q,
            "is_followup": True,
            "turn_type": "FOLLOW_UP",
            "needs_clarification": False,
            "clarification_type": None,
            "clarification_message": None,
            "is_date_ambiguous": False,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # D. Follow-up: Justification / Elaboration ("Why?", "Why is it not safe?")
    # ─────────────────────────────────────────────────────────────────────────
    if any(q_clean == w or q_clean.startswith(w + " ") for w in ["why", "why is it not safe", "why is it safe", "can i still do it", "what should i do", "tell me more"]):
        if prev_intent:
            return {
                "intent": prev_intent,
                "amount": prev_amount,
                "category": prev_category,
                "reporting_date": reporting_date or prev_reporting_date,
                "raw_query": q,
                "is_followup": True,
                "turn_type": "FOLLOW_UP",
                "needs_clarification": False,
                "clarification_type": None,
                "clarification_message": None,
                "is_date_ambiguous": False,
            }

    # ─────────────────────────────────────────────────────────────────────────
    # E. Follow-up: Temporal Date Switch ("What about last month?", "And in August?")
    # ─────────────────────────────────────────────────────────────────────────
    is_temporal_followup = any(q_lower.startswith(p) for p in ["what about", "how about", "and in", "and for", "what of"]) and reporting_date is not None
    if is_temporal_followup and prev_intent:
        return {
            "intent": prev_intent,
            "amount": prev_amount,
            "category": prev_category,
            "reporting_date": reporting_date,
            "raw_query": q,
            "is_followup": True,
            "turn_type": "FOLLOW_UP",
            "needs_clarification": False,
            "clarification_type": None,
            "clarification_message": None,
            "is_date_ambiguous": False,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # F0. Multi-Month Spending Trend Detection
    # e.g. "Show my spending trend over the last six months.", "How much did I spend each month this year?"
    # ─────────────────────────────────────────────────────────────────────────
    trend_info = extract_spending_trend(q)
    if trend_info and trend_info.get("is_match"):
        num_m = trend_info.get("trend_months", 6)
        merchant_cand, _ = extract_merchant(q)
        cat_cand = None if merchant_cand else extract_explicit_category(q)
        return {
            "intent": "SPENDING_TREND",
            "trend_months": num_m,
            "category": cat_cand,
            "merchant": merchant_cand,
            "reporting_date": reporting_date,
            "raw_query": q,
            "is_followup": False,
            "turn_type": "NEW_TOPIC",
            "needs_clarification": False,
            "clarification_type": None,
            "clarification_message": None,
            "is_date_ambiguous": False,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # F1. Period Comparison & Category-Wise Variance Attribution
    # e.g. "Did I spend more in September than October?", "Compare my expenses in August and September 2026",
    #      "How much more did I spend on Food this month compared with last month?",
    #      "Did I spend more on Uber in September or October?", "Which categories increased the most?"
    # ─────────────────────────────────────────────────────────────────────────
    comp_info = extract_comparison_periods(q)
    if comp_info and comp_info.get("is_match"):
        if comp_info.get("needs_clarification"):
            return {
                "intent": "PERIOD_COMPARISON",
                "reporting_date": None,
                "comparison_reporting_date": None,
                "category": None,
                "merchant": None,
                "raw_query": q,
                "is_followup": False,
                "turn_type": "NEW_TOPIC",
                "needs_clarification": True,
                "clarification_type": comp_info.get("clarification_type"),
                "clarification_message": comp_info.get("clarification_message"),
                "is_date_ambiguous": False,
            }

        # Check for merchant filter
        m_cand, m_matches = extract_merchant(q)
        if len(m_matches) > 1:
            return {
                "intent": "PERIOD_COMPARISON",
                "reporting_date": comp_info["period_a"],
                "comparison_reporting_date": comp_info["period_b"],
                "category": None,
                "merchant": None,
                "raw_query": q,
                "is_followup": False,
                "turn_type": "NEW_TOPIC",
                "needs_clarification": True,
                "clarification_type": "AMBIGUOUS_MERCHANT",
                "clarification_message": f"Multiple merchants detected ({', '.join(m_matches)}). Please specify which merchant you would like to analyze.",
                "is_date_ambiguous": False,
            }

        # Check for category filter only if merchant is not present
        cat_cand = None if m_cand else extract_explicit_category(q)

        return {
            "intent": "PERIOD_COMPARISON",
            "reporting_date": comp_info["period_a"],
            "comparison_reporting_date": comp_info["period_b"],
            "category": cat_cand,
            "merchant": m_cand,
            "first_mentioned": comp_info.get("first_mentioned"),
            "second_mentioned": comp_info.get("second_mentioned"),
            "is_variance_attribution": comp_info.get("is_variance_attribution", False),
            "raw_query": q,
            "is_followup": False,
            "turn_type": "NEW_TOPIC",
            "needs_clarification": False,
            "clarification_type": None,
            "clarification_message": None,
            "is_date_ambiguous": False,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # F. Standalone Topic: Purchase Safety Detection
    # e.g. "Can I spend ₹15,000 on a phone?", "Can I buy a car for 500000?", "Can I afford to buy a laptop?"
    # ─────────────────────────────────────────────────────────────────────────
    purchase_kw = ["buy", "purchase", "spend", "afford"]
    is_purchase = any(kw in q_lower for kw in purchase_kw) and any(kw in q_lower for kw in ["can i", "should i", "could i", "am i able to", "is it safe", "afford"])
    if is_purchase or any(kw in q_lower for kw in ["can i buy", "can i spend", "can i afford", "should i buy"]):
        cat = infer_category(q_lower)
        # Check ambiguous multiple amounts
        if len(candidate_amounts) > 1:
            return {
                "intent": "PURCHASE_SAFETY",
                "amount": None,
                "category": cat,
                "reporting_date": reporting_date,
                "raw_query": q,
                "is_followup": False,
                "turn_type": "NEW_TOPIC",
                "needs_clarification": True,
                "clarification_type": "AMBIGUOUS_AMOUNT",
                "clarification_message": f"Multiple amounts detected ({', '.join(f'₹{int(a):,}' for a in candidate_amounts)}). Please specify a single purchase amount to check affordability.",
                "is_date_ambiguous": False,
            }

        # Check missing amount
        if len(candidate_amounts) == 0:
            return {
                "intent": "PURCHASE_SAFETY",
                "amount": None,
                "category": cat,
                "reporting_date": reporting_date,
                "raw_query": q,
                "is_followup": False,
                "turn_type": "NEW_TOPIC",
                "needs_clarification": True,
                "clarification_type": "MISSING_AMOUNT",
                "clarification_message": "Please specify the purchase amount (e.g. 'Can I buy a phone for ₹20,000?') to check affordability.",
                "is_date_ambiguous": False,
            }

        return {
            "intent": "PURCHASE_SAFETY",
            "amount": candidate_amounts[0],
            "category": cat,
            "reporting_date": reporting_date,
            "raw_query": q,
            "is_followup": False,
            "turn_type": "NEW_TOPIC",
            "needs_clarification": False,
            "clarification_type": None,
            "clarification_message": None,
            "is_date_ambiguous": False,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # G1. Merchant Expenditure Queries
    # e.g. "How much did I spend on Uber?", "Show my Netflix payments", "Which transactions belong to Uber?"
    # ─────────────────────────────────────────────────────────────────────────
    merchant, merchant_matches = extract_merchant(q)
    is_merchant_spend_query = any(kw in q_lower for kw in [
        "spend on", "spent on", "expense on", "expenses on", "payments", "payment",
        "belong to", "cost of", "orders on", "bought from", "paid for"
    ]) or any(q_lower.startswith(p) for p in ["show my", "show", "list", "how much did i spend on", "which transactions", "what are my"])

    if len(merchant_matches) > 1:
        # Ambiguous merchant match: ask user to clarify
        return {
            "intent": "MERCHANT_EXPENSE",
            "merchant": None,
            "amount": None,
            "category": None,
            "reporting_date": reporting_date,
            "raw_query": q,
            "is_followup": False,
            "turn_type": "NEW_TOPIC",
            "needs_clarification": True,
            "clarification_type": "AMBIGUOUS_MERCHANT",
            "clarification_message": f"Multiple merchants detected ({', '.join(merchant_matches)}). Please specify which merchant you would like to analyze.",
            "is_date_ambiguous": False,
        }

    if merchant and (is_merchant_spend_query or any(m.lower() in q_lower for m in [merchant])):
        return {
            "intent": "MERCHANT_EXPENSE",
            "merchant": merchant,
            "amount": None,
            "category": None,
            "reporting_date": reporting_date,
            "raw_query": q,
            "is_followup": False,
            "turn_type": "NEW_TOPIC",
            "needs_clarification": False,
            "clarification_type": None,
            "clarification_message": None,
            "is_date_ambiguous": False,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # G2. Top-N and Amount-Filtered Transaction Queries
    # e.g. "What are my five biggest expenses?", "Show my three largest purchases in September", "List expenses above ₹5,000"
    # ─────────────────────────────────────────────────────────────────────────
    top_info = extract_top_n_and_thresholds(q)
    if top_info:
        return {
            "intent": "TOP_TRANSACTIONS",
            "limit": top_info.get("limit"),
            "amount_min": top_info.get("amount_min"),
            "amount_max": top_info.get("amount_max"),
            "sort_by": top_info.get("sort_by", "amount"),
            "sort_direction": top_info.get("sort_direction", "DESC"),
            "amount": None,
            "category": None,
            "reporting_date": reporting_date,
            "raw_query": q,
            "is_followup": False,
            "turn_type": "NEW_TOPIC",
            "needs_clarification": False,
            "clarification_type": None,
            "clarification_message": None,
            "is_date_ambiguous": False,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # G3. Category-Specific Expense Queries & Follow-ups
    # ─────────────────────────────────────────────────────────────────────────
    category_matches = ["housing", "rent", "food", "grocery", "groceries", "transport", "travel", "utilities", "electricity", "shopping", "entertainment", "healthcare", "medicine"]
    has_cat = any(c in q_lower for c in category_matches)
    is_cat_spend = ("spend on" in q_lower or "spent on" in q_lower or "spending on" in q_lower or "expense on" in q_lower or "expenses on" in q_lower or "cost of" in q_lower)
    is_cat_followup = any(q_lower.startswith(p) for p in ["what about", "how about", "and for", "and what about", "tell me about"])


    if (is_cat_spend and has_cat) or (is_cat_followup and has_cat):
        matched_cat = infer_category(q_lower)
        is_follow = is_cat_followup or (prev_intent in ["CATEGORY_EXPENSE", "EXPENSE_BREAKDOWN"])
        return {
            "intent": "CATEGORY_EXPENSE",
            "category": matched_cat,
            "amount": None,
            "reporting_date": reporting_date or (prev_reporting_date if is_follow else None),
            "raw_query": q,
            "is_followup": is_follow,
            "turn_type": "FOLLOW_UP" if is_follow else "NEW_TOPIC",
            "needs_clarification": False,
            "clarification_type": None,
            "clarification_message": None,
            "is_date_ambiguous": False,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # H. Overall Expense Breakdown & Top Category (New Topic)
    # ─────────────────────────────────────────────────────────────────────────
    if any(kw in q_lower for kw in ["spend the most", "where did i spend", "top expense", "largest expense", "highest expense", "expense breakdown", "where is my money going", "spending breakdown", "break down", "breakdown"]):
        return {
            "intent": "EXPENSE_BREAKDOWN",
            "amount": None,
            "category": None,
            "reporting_date": reporting_date,
            "raw_query": q,
            "is_followup": False,
            "turn_type": "NEW_TOPIC",
            "needs_clarification": False,
            "clarification_type": None,
            "clarification_message": None,
            "is_date_ambiguous": False,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # I. Emergency Runway Detection (New Topic)
    # ─────────────────────────────────────────────────────────────────────────
    runway_keywords = [
        "runway",
        "survive",
        "how long will my money last",
        "how long can i survive",
        "how long will my savings last",
        "how long can i last",
        "how many months can i survive",
        "how many months can i last",
        "months of coverage",
        "survival buffer",
        "survival time",
        "money last",
        "savings last",
        "live on my savings",
        "survive on my savings",
        "how long would my savings last",
        "how long could i survive",
    ]
    if any(kw in q_lower for kw in runway_keywords):
        return {
            "intent": "EMERGENCY_RUNWAY_ANALYSIS",
            "amount": None,
            "category": None,
            "reporting_date": reporting_date,
            "raw_query": q,
            "is_followup": False,
            "turn_type": "NEW_TOPIC",
            "needs_clarification": False,
            "clarification_type": None,
            "clarification_message": None,
            "is_date_ambiguous": False,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # J. Savings Analysis (New Topic)
    # ─────────────────────────────────────────────────────────────────────────
    if any(kw in q_lower for kw in ["savings rate", "saving rate", "how much am i saving", "how much do i save", "total savings", "my savings"]):
        return {
            "intent": "SAVINGS_ANALYSIS",
            "amount": None,
            "category": None,
            "reporting_date": reporting_date,
            "raw_query": q,
            "is_followup": False,
            "turn_type": "NEW_TOPIC",
            "needs_clarification": False,
            "clarification_type": None,
            "clarification_message": None,
            "is_date_ambiguous": False,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # K. Emergency Fund Analysis (New Topic)
    # ─────────────────────────────────────────────────────────────────────────
    if any(kw in q_lower for kw in ["emergency fund", "emergency reserve", "emergency money", "emergency target"]):
        return {
            "intent": "EMERGENCY_FUND_ANALYSIS",
            "amount": None,
            "category": None,
            "reporting_date": reporting_date,
            "raw_query": q,
            "is_followup": False,
            "turn_type": "NEW_TOPIC",
            "needs_clarification": False,
            "clarification_type": None,
            "clarification_message": None,
            "is_date_ambiguous": False,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # L. Debt & Obligation Analysis (New Topic)
    # ─────────────────────────────────────────────────────────────────────────
    if any(kw in q_lower for kw in ["debt", "loan", "emi", "dti", "outstanding", "liabilities", "obligations"]):
        return {
            "intent": "DEBT_ANALYSIS",
            "amount": None,
            "category": None,
            "reporting_date": reporting_date,
            "raw_query": q,
            "is_followup": False,
            "turn_type": "NEW_TOPIC",
            "needs_clarification": False,
            "clarification_type": None,
            "clarification_message": None,
            "is_date_ambiguous": False,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # M. Comprehensive Financial Health Check (New Topic)
    # ─────────────────────────────────────────────────────────────────────────
    if any(kw in q_lower for kw in ["health score", "financial health", "health check", "financial grade", "financial score"]):
        return {
            "intent": "FINANCIAL_HEALTH",
            "amount": None,
            "category": None,
            "reporting_date": reporting_date,
            "raw_query": q,
            "is_followup": False,
            "turn_type": "NEW_TOPIC",
            "needs_clarification": False,
            "clarification_type": None,
            "clarification_message": None,
            "is_date_ambiguous": False,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # N. Financial Summary & Overview (New Topic)
    # ─────────────────────────────────────────────────────────────────────────
    if any(kw in q_lower for kw in ["financial summary", "financial situation", "overall finances", "my finances", "financial overview", "summary of my finances", "tell me something about my finances"]):
        return {
            "intent": "FINANCIAL_SUMMARY",
            "amount": None,
            "category": None,
            "reporting_date": reporting_date,
            "raw_query": q,
            "is_followup": False,
            "turn_type": "NEW_TOPIC",
            "needs_clarification": False,
            "clarification_type": None,
            "clarification_message": None,
            "is_date_ambiguous": False,
        }

    return None


def parse_question_llm(question: str) -> dict:
    """
    LLM fallback parser for complex conversational or ambiguous questions.
    """
    from backend.app.services.llm_service import ask_llm
    from backend.app.nlu.query_plan import create_query_plan_from_parsed

    prompt = f"""
You are a precise financial intent parser. Classify the user query into a JSON object matching this schema:
{{
  "intent": "<PURCHASE_SAFETY | SAVINGS_ANALYSIS | EMERGENCY_FUND_ANALYSIS | EMERGENCY_RUNWAY_ANALYSIS | EXPENSE_BREAKDOWN | CATEGORY_EXPENSE | MERCHANT_EXPENSE | TOP_TRANSACTIONS | PERIOD_COMPARISON | SPENDING_TREND | DEBT_ANALYSIS | FINANCIAL_HEALTH | FINANCIAL_SUMMARY | UNKNOWN>",
  "amount": <number or null>,
  "category": "<category string or null>",
  "merchant": "<merchant name string or null>",
  "limit": <integer or null>,
  "amount_min": <number or null>,
  "amount_max": <number or null>
}}

User Query: "{question}"
Return ONLY raw JSON. No explanation, no markdown.
"""
    reporting_date, is_ambiguous, clarification_msg = check_date_ambiguity(question)
    try:
        raw = ask_llm(prompt)["content"].strip()
        raw = re.sub(r"^```json\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"```$", "", raw, flags=re.MULTILINE).strip()
        parsed = json.loads(raw)
        parsed["reporting_date"] = reporting_date
        parsed["raw_query"] = question
        parsed["is_followup"] = False
        parsed["turn_type"] = "NEW_TOPIC"
        parsed["needs_clarification"] = is_ambiguous
        parsed["clarification_type"] = "AMBIGUOUS_DATE" if is_ambiguous else None
        parsed["clarification_message"] = clarification_msg
        parsed["is_date_ambiguous"] = is_ambiguous

        plan = create_query_plan_from_parsed(parsed)
        legacy = plan.to_legacy_entities()
        legacy["turn_type"] = "NEW_TOPIC"
        legacy["is_date_ambiguous"] = is_ambiguous
        return legacy
    except Exception:
        fallback = {
            "intent": "UNKNOWN",
            "amount": None,
            "category": None,
            "merchant": None,
            "limit": None,
            "amount_min": None,
            "amount_max": None,
            "reporting_date": reporting_date,
            "raw_query": question,
            "is_followup": False,
            "turn_type": "NEW_TOPIC",
            "needs_clarification": is_ambiguous,
            "clarification_type": "AMBIGUOUS_DATE" if is_ambiguous else None,
            "clarification_message": clarification_msg,
            "is_date_ambiguous": is_ambiguous,
        }
        plan = create_query_plan_from_parsed(fallback)
        legacy = plan.to_legacy_entities()
        legacy["turn_type"] = "NEW_TOPIC"
        legacy["is_date_ambiguous"] = is_ambiguous
        return legacy


def parse_question(question: str, conversation_history: list[dict] | None = None, use_llm_fallback: bool = True) -> dict:
    from backend.app.nlu.query_plan import create_query_plan_from_parsed

    res = parse_question_rules(question, conversation_history=conversation_history)
    if res:
        plan = create_query_plan_from_parsed(res)
        legacy = plan.to_legacy_entities()
        legacy["turn_type"] = res.get("turn_type", "NEW_TOPIC")
        legacy["is_date_ambiguous"] = res.get("is_date_ambiguous", False)
        legacy["raw_query"] = question
        if "first_mentioned" in res:
            legacy["first_mentioned"] = res["first_mentioned"]
        if "second_mentioned" in res:
            legacy["second_mentioned"] = res["second_mentioned"]
        if "is_variance_attribution" in res:
            legacy["is_variance_attribution"] = res["is_variance_attribution"]
        return legacy

    if use_llm_fallback:
        return parse_question_llm(question)

    reporting_date, is_ambiguous, clarification_msg = check_date_ambiguity(question)
    unknown_dict = {
        "intent": "UNKNOWN",
        "amount": None,
        "category": None,
        "merchant": None,
        "limit": None,
        "amount_min": None,
        "amount_max": None,
        "reporting_date": reporting_date,
        "raw_query": question,
        "is_followup": False,
        "turn_type": "NEW_TOPIC",
        "needs_clarification": is_ambiguous,
        "clarification_type": "AMBIGUOUS_DATE" if is_ambiguous else None,
        "clarification_message": clarification_msg,
        "is_date_ambiguous": is_ambiguous,
    }
    plan = create_query_plan_from_parsed(unknown_dict)
    legacy = plan.to_legacy_entities()
    legacy["turn_type"] = "NEW_TOPIC"
    legacy["is_date_ambiguous"] = is_ambiguous
    return legacy


