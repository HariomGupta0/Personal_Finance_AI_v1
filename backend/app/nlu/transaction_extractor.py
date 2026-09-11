import re
import json
from datetime import date, timedelta

CATEGORY_KEYWORDS = {
    "Housing": ["rent", "maintenance", "landlord", "apartment", "mortgage"],
    "Food": ["food", "groceries", "grocery", "restaurant", "swiggy", "zomato", "dinner", "lunch", "breakfast", "snacks", "cafe", "coffee"],
    "Transport": ["travel", "bus", "auto", "metro", "cab", "uber", "ola", "petrol", "diesel", "fuel", "train", "flight", "taxi"],
    "Utilities": ["electricity", "water", "wifi", "internet", "gas", "recharge", "phone bill", "utility", "power bill"],
    "Shopping": ["shopping", "clothes", "shirt", "shoes", "amazon", "flipkart", "electronics", "gadget", "laptop", "mobile"],
    "Entertainment": ["movie", "cinema", "netflix", "prime", "hotstar", "game", "outing", "concert"],
    "Healthcare": ["doctor", "medicine", "pharmacy", "hospital", "clinic", "health", "dental"],
    "Education": ["tuition", "books", "course", "fees", "school", "college", "exam"]
}

INCOME_KEYWORDS = [
    "salary", "bonus", "freelance", "dividend", "interest", "cashback", "refund", "received", "credited"
]

EXPENSE_KEYWORDS = [
    "spent", "paid", "buy", "bought", "purchase", "shopping", "debited", "transferred", "expense", "bill"
]

def infer_category(text):
    text_lower = text.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return cat
    return "Miscellaneous"

def infer_date(text):
    text_lower = text.lower()
    today = date.today()
    if "yesterday" in text_lower:
        return (today - timedelta(days=1)).isoformat()
    if "today" in text_lower or "now" in text_lower:
        return today.isoformat()
    
    match_iso = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if match_iso:
        return match_iso.group(0)
    
    match_dmy = re.search(r"\b(\d{2})[-/](\d{2})[-/](\d{4})\b", text)
    if match_dmy:
        d, m, y = match_dmy.groups()
        return f"{y}-{m}-{d}"

    return today.isoformat()

def extract_transaction_rules(text):
    text_clean = text.strip()
    text_lower = text_clean.lower()

    is_income = any(kw in text_lower for kw in INCOME_KEYWORDS) and not any(kw in text_lower for kw in ["spent on", "paid for"])
    tx_type = "INCOME" if is_income else "EXPENSE"

    amount_match = re.search(r"(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)\s*(?:rs|rupees|inr)?", text_clean, re.IGNORECASE)
    if not amount_match:
        return None

    try:
        amount_val = float(amount_match.group(1).replace(",", ""))
    except ValueError:
        return None

    if amount_val <= 0:
        return None

    category = "Salary" if is_income and "salary" in text_lower else infer_category(text_clean)
    tx_date = infer_date(text_clean)

    desc = re.sub(r"(?:₹|rs\.?|inr)?\s*[\d,]+(?:\.\d{1,2})?\s*(?:rs|rupees|inr)?", "", text_clean, flags=re.IGNORECASE)
    for word in ["i spent", "spent", "paid for", "paid", "bought", "received", "credited", "today", "yesterday", "for", "on", "a", "an"]:
        desc = re.sub(rf"\b{word}\b", "", desc, flags=re.IGNORECASE)
    desc = desc.strip()
    if not desc or len(desc) < 2:
        desc = f"{category} {tx_type.lower()}"

    return {
        "amount": amount_val,
        "description": desc.capitalize(),
        "category": category,
        "type": tx_type,
        "date": tx_date
    }

def extract_transaction_llm(text):
    from backend.app.services.llm_service import ask_llm
    today_str = date.today().isoformat()
    prompt = f"""
You are a financial entity extraction engine. Extract transaction details from the given text into JSON.
Today's date is: {today_str}

STRICT INSTRUCTIONS:
1. Return ONLY valid JSON matching this exact schema:
{{
  "amount": <number>,
  "description": "<string>",
  "category": "<Housing | Food | Transport | Utilities | Shopping | Entertainment | Healthcare | Education | Miscellaneous | Salary>",
  "type": "<EXPENSE | INCOME>",
  "date": "<YYYY-MM-DD>"
}}
2. Do not include markdown codeblocks or extra text. Only JSON.

Input text: "{text}"
"""
    try:
        raw_response = ask_llm(prompt).strip()
        raw_response = re.sub(r"^```json\s*", "", raw_response, flags=re.MULTILINE)
        raw_response = re.sub(r"```$", "", raw_response, flags=re.MULTILINE).strip()
        data = json.loads(raw_response)
        if "amount" in data and float(data["amount"]) > 0:
            return {
                "amount": float(data["amount"]),
                "description": str(data.get("description", "Transaction")).capitalize(),
                "category": str(data.get("category", "Miscellaneous")),
                "type": "INCOME" if str(data.get("type", "")).upper() == "INCOME" else "EXPENSE",
                "date": str(data.get("date", today_str))
            }
    except Exception:
        pass
    return None

def extract_transaction(text, use_llm_fallback=True):
    result = extract_transaction_rules(text)
    if result:
        return result

    if use_llm_fallback:
        return extract_transaction_llm(text)

    return None
