import re
import json
from datetime import date
from backend.app.nlu.transaction_extractor import infer_category

MONTH_NAMES = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9, "october": 10,
    "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12
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


def parse_question_rules(question):
    q = question.strip()
    q_lower = q.lower()
    reporting_date = extract_temporal_reporting_date(q)

    # 1. Transaction Ingestion Detection (e.g. "I spent ₹500 on food today", "Paid 1200 for electricity bill")
    if any(q_lower.startswith(prefix) for prefix in ["i spent", "spent", "paid for", "bought", "received salary", "earned"]) or \
       (any(kw in q_lower for kw in ["spent", "paid", "debited"]) and any(kw in q_lower for kw in ["today", "yesterday", "on", "for"]) and not any(kw in q_lower for kw in ["can i", "how much", "what is", "where"])):
        amount_m = re.search(r"(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)", q_lower)
        if amount_m:
            try:
                amt = float(amount_m.group(1).replace(",", ""))
                return {
                    "intent": "TRANSACTION_INGESTION",
                    "amount": amt,
                    "category": infer_category(q_lower),
                    "reporting_date": reporting_date,
                    "raw_query": q
                }
            except ValueError:
                pass

    # 2. Purchase Safety Detection (e.g. "Can I spend ₹15,000 on a phone?", "Can I buy a car for 500000?", "Can I afford...")
    purchase_kw = ["buy", "purchase", "spend", "afford"]
    is_purchase = any(kw in q_lower for kw in purchase_kw) and any(kw in q_lower for kw in ["can i", "should i", "could i", "am i able to", "is it safe", "afford"])
    if is_purchase or (any(kw in q_lower for kw in ["can i buy", "can i spend", "can i afford", "should i buy"])):
        amount_m = re.search(r"(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)", q_lower)
        amt = float(amount_m.group(1).replace(",", "")) if amount_m else None
        cat = infer_category(q_lower)
        return {
            "intent": "PURCHASE_SAFETY",
            "amount": amt,
            "category": cat,
            "reporting_date": reporting_date,
            "raw_query": q
        }

    # 3. Emergency Runway Detection (e.g. "How many months can I survive?", "What is my emergency runway?", "How long will my money last?")
    if any(kw in q_lower for kw in ["runway", "how long will my money last", "how many months can i survive", "months of coverage", "survival buffer"]):
        return {
            "intent": "EMERGENCY_RUNWAY_ANALYSIS",
            "amount": None,
            "reporting_date": reporting_date,
            "raw_query": q
        }

    # 4. Emergency Fund Analysis (e.g. "How much emergency fund do I need?", "Emergency fund reserve")
    if any(kw in q_lower for kw in ["emergency fund", "emergency reserve", "emergency money", "emergency target"]):
        return {
            "intent": "EMERGENCY_FUND_ANALYSIS",
            "amount": None,
            "reporting_date": reporting_date,
            "raw_query": q
        }

    # 5. Category-Specific Expense Queries (e.g. "How much did I spend on food?", "What are my food expenses?")
    category_matches = ["housing", "rent", "food", "grocery", "groceries", "transport", "travel", "utilities", "electricity", "shopping", "entertainment", "healthcare", "medicine"]
    if ("spend on" in q_lower or "spent on" in q_lower or "expense on" in q_lower or "expenses on" in q_lower or "cost of" in q_lower) and any(c in q_lower for c in category_matches):
        matched_cat = infer_category(q_lower)
        return {
            "intent": "CATEGORY_EXPENSE",
            "category": matched_cat,
            "amount": None,
            "reporting_date": reporting_date,
            "raw_query": q
        }

    # 6. Overall Expense Breakdown & Top Category (e.g. "Where did I spend the most?", "What are my top expenses?", "Show my expense breakdown")
    if any(kw in q_lower for kw in ["spend the most", "where did i spend", "top expense", "largest expense", "highest expense", "expense breakdown", "where is my money going"]):
        return {
            "intent": "EXPENSE_BREAKDOWN",
            "amount": None,
            "reporting_date": reporting_date,
            "raw_query": q
        }

    # 7. Savings Analysis (e.g. "What is my savings rate?", "How much am I saving?", "How much do I save?")
    if any(kw in q_lower for kw in ["savings rate", "saving rate", "how much am i saving", "how much do i save", "total savings", "my savings"]):
        return {
            "intent": "SAVINGS_ANALYSIS",
            "amount": None,
            "reporting_date": reporting_date,
            "raw_query": q
        }

    # 8. Debt & Obligation Analysis (e.g. "How much debt do I have?", "What are my pending EMIs?", "What is my DTI ratio?", "Loan obligations")
    if any(kw in q_lower for kw in ["debt", "loan", "emi", "dti", "outstanding", "liabilities", "obligations"]):
        return {
            "intent": "DEBT_ANALYSIS",
            "amount": None,
            "reporting_date": reporting_date,
            "raw_query": q
        }

    # 9. Comprehensive Financial Health Check (e.g. "What is my financial health score?", "How is my financial health?", "Financial grade")
    if any(kw in q_lower for kw in ["health score", "financial health", "health check", "financial grade"]):
        return {
            "intent": "FINANCIAL_HEALTH",
            "amount": None,
            "reporting_date": reporting_date,
            "raw_query": q
        }

    # 10. Financial Summary & Overview
    if any(kw in q_lower for kw in ["financial summary", "financial situation", "overall finances", "my finances", "financial overview", "summary of my finances", "tell me something about my finances"]):
        return {
            "intent": "FINANCIAL_SUMMARY",
            "amount": None,
            "reporting_date": reporting_date,
            "raw_query": q
        }

    return None

def parse_question_llm(question):
    """
    LLM fallback parser for complex conversational or ambiguous questions.
    """
    from backend.app.services.llm_service import ask_llm
    prompt = f"""
You are a precise financial intent parser. Classify the user query into a JSON object matching this schema:
{{
  "intent": "<PURCHASE_SAFETY | SAVINGS_ANALYSIS | EMERGENCY_FUND_ANALYSIS | EMERGENCY_RUNWAY_ANALYSIS | EXPENSE_BREAKDOWN | CATEGORY_EXPENSE | DEBT_ANALYSIS | FINANCIAL_HEALTH | FINANCIAL_SUMMARY | UNKNOWN>",
  "amount": <number or null>,
  "category": "<category string or null>"
}}

User Query: "{question}"
Return ONLY raw JSON. No explanation, no markdown.
"""
    reporting_date = extract_temporal_reporting_date(question)
    try:
        raw = ask_llm(prompt)["content"].strip()
        raw = re.sub(r"^```json\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"```$", "", raw, flags=re.MULTILINE).strip()
        parsed = json.loads(raw)
        parsed["reporting_date"] = reporting_date
        parsed["raw_query"] = question
        return parsed
    except Exception:
        return {
            "intent": "UNKNOWN",
            "amount": None,
            "category": None,
            "reporting_date": reporting_date,
            "raw_query": question
        }

def parse_question(question, use_llm_fallback=True):
    res = parse_question_rules(question)
    if res:
        return res
    if use_llm_fallback:
        return parse_question_llm(question)
    return {
        "intent": "UNKNOWN",
        "amount": None,
        "category": None,
        "reporting_date": extract_temporal_reporting_date(question),
        "raw_query": question
    }
