"""
Merchant Normalizer & Indian Banking Narration Parser.

Cleans noisy bank statement narrations (UPI, POS, IMPS, NEFT, ATM, ACH)
and extracts canonical merchant/payee names with explainable categorization.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class NormalizedMerchant:
    raw_description: str
    clean_merchant: str
    channel: str              # UPI, POS, NEFT, IMPS, ATM, ACH, OTHER
    category: str
    category_source: str       # merchant_rule, keyword, default
    confidence: float          # 0.0 to 1.0


# High-confidence merchant mappings (canonical merchant -> category)
KNOWN_MERCHANTS: dict[str, tuple[str, str]] = {
    # Food & Dining
    "swiggy": ("Swiggy", "Food"),
    "zomato": ("Zomato", "Food"),
    "mcdonalds": ("McDonald's", "Food"),
    "starbucks": ("Starbucks", "Food"),
    "dominos": ("Domino's Pizza", "Food"),
    "kfc": ("KFC", "Food"),
    "subway": ("Subway", "Food"),
    "blinkit": ("Blinkit", "Food"),
    "zepto": ("Zepto", "Food"),
    "instamart": ("Swiggy Instamart", "Food"),
    "dunzo": ("Dunzo", "Food"),
    "bigbasket": ("BigBasket", "Food"),

    # Transport & Fuel
    "uber": ("Uber", "Transport"),
    "ola": ("Ola Cabs", "Transport"),
    "rapido": ("Rapido", "Transport"),
    "irctc": ("IRCTC", "Transport"),
    "hpcl": ("HP Petrol", "Transport"),
    "bpcl": ("Bharat Petroleum", "Transport"),
    "ioc": ("Indian Oil", "Transport"),
    "indianoil": ("Indian Oil", "Transport"),
    "makemytrip": ("MakeMyTrip", "Transport"),
    "indigo": ("IndiGo", "Transport"),

    # Shopping & E-Commerce
    "amazon": ("Amazon", "Shopping"),
    "flipkart": ("Flipkart", "Shopping"),
    "myntra": ("Myntra", "Shopping"),
    "nykaa": ("Nykaa", "Shopping"),
    "ajio": ("Ajio", "Shopping"),
    "meesho": ("Meesho", "Shopping"),
    "croma": ("Croma", "Shopping"),
    "reliance retail": ("Reliance Retail", "Shopping"),
    "dmart": ("DMart", "Shopping"),

    # Entertainment & Subscriptions
    "netflix": ("Netflix", "Entertainment"),
    "spotify": ("Spotify", "Entertainment"),
    "hotstar": ("Disney+ Hotstar", "Entertainment"),
    "prime video": ("Amazon Prime", "Entertainment"),
    "bookmyshow": ("BookMyShow", "Entertainment"),
    "youtube": ("YouTube Premium", "Entertainment"),

    # Utilities & Bills
    "airtel": ("Airtel", "Utilities"),
    "jio": ("Jio", "Utilities"),
    "vi": ("Vodafone Idea", "Utilities"),
    "bescom": ("Electricity Board (BESCOM)", "Utilities"),
    "tneb": ("Electricity Board (TNEB)", "Utilities"),
    "mahadiscom": ("Electricity Board (MSEDCL)", "Utilities"),
    "tata power": ("Tata Power", "Utilities"),
    "adanigas": ("Adani Gas", "Utilities"),
    "igl": ("Indraprastha Gas", "Utilities"),

    # Healthcare
    "apollo": ("Apollo Pharmacy", "Healthcare"),
    "1mg": ("Tata 1mg", "Healthcare"),
    "pharmeasy": ("PharmEasy", "Healthcare"),
    "netmeds": ("Netmeds", "Healthcare"),
    "medplus": ("MedPlus", "Healthcare"),

    # Financial / Investment
    "zerodha": ("Zerodha", "Investment"),
    "groww": ("Groww", "Investment"),
    "upstox": ("Upstox", "Investment"),
    "cred": ("CRED (Credit Card Bill)", "Debt"),
}

# General keyword fallbacks
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Housing": ["rent", "maintenance", "landlord", "apartment", "mortgage", "housing"],
    "Food": ["food", "groceries", "grocery", "restaurant", "dinner", "lunch", "breakfast", "snacks", "cafe", "coffee", "bakery"],
    "Transport": ["travel", "bus", "auto", "metro", "cab", "petrol", "diesel", "fuel", "train", "flight", "taxi", "toll", "fastag"],
    "Utilities": ["electricity", "water", "wifi", "internet", "gas", "recharge", "phone bill", "utility", "broadband"],
    "Shopping": ["shopping", "clothes", "shirt", "shoes", "electronics", "gadget", "laptop", "mobile"],
    "Entertainment": ["movie", "cinema", "game", "outing", "concert"],
    "Healthcare": ["doctor", "medicine", "pharmacy", "hospital", "clinic", "health", "dental", "lab"],
    "Education": ["tuition", "books", "course", "fees", "school", "college", "exam"],
    "Salary": ["salary", "payroll", "wage", "stipend"],
}

INCOME_SIGNALS = {
    "salary", "bonus", "freelance", "dividend", "interest",
    "cashback", "refund", "credited", "received",
}


def normalize_narration(raw: str, tx_type: str = "EXPENSE") -> NormalizedMerchant:
    """
    Parse a raw bank statement line and extract the cleanest possible merchant name,
    channel, and category.
    """
    s = str(raw or "").strip()
    if not s:
        return NormalizedMerchant(
            raw_description="",
            clean_merchant="Unknown",
            channel="OTHER",
            category="Income" if tx_type == "INCOME" else "General",
            category_source="default",
            confidence=0.1,
        )

    channel = "OTHER"
    candidate_name = s

    # 1. Detect Channel & extract core name segment
    # UPI format: UPI/1234567890/MERCHANT/okhdfcbank/Payment
    upi_match = re.search(r"UPI[/:\-](?:CR[/:\-]|DR[/:\-])?(?:\d+[/:\-])?([^/:\-]+)", s, re.IGNORECASE)
    if upi_match:
        channel = "UPI"
        candidate_name = upi_match.group(1).strip()
    elif s.upper().startswith("POS") or " POS " in s.upper():
        channel = "POS"
        candidate_name = re.sub(r"^POS\s*\d*\s*", "", s, flags=re.IGNORECASE).strip()
    elif s.upper().startswith("NEFT") or " NEFT " in s.upper():
        channel = "NEFT"
        candidate_name = re.sub(r"^NEFT[\s\-_]*[A-Z0-9]*[\s\-_]*", "", s, flags=re.IGNORECASE).strip()
    elif s.upper().startswith("IMPS") or " IMPS " in s.upper():
        channel = "IMPS"
        candidate_name = re.sub(r"^IMPS[\s\-_]*\d*[\s\-_]*", "", s, flags=re.IGNORECASE).strip()
    elif "ATM" in s.upper():
        channel = "ATM"
        candidate_name = "ATM Cash Withdrawal" if tx_type == "EXPENSE" else "ATM Deposit"
    elif "ACH" in s.upper() or "NACH" in s.upper():
        channel = "ACH"
        candidate_name = re.sub(r"^(?:N?ACH)[\s\-_]*\d*[\s\-_]*", "", s, flags=re.IGNORECASE).strip()

    # Clean up trailing noise (bank codes, account numbers, dates)
    cleaned = re.sub(r"[@/:\-_].*$", "", candidate_name).strip()
    cleaned = re.sub(r"\b\d{4,}\b", "", cleaned).strip()
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if not cleaned:
        cleaned = candidate_name.strip() or s

    lower_raw = s.lower()
    lower_clean = cleaned.lower()

    # Handle Income first if direction is INCOME
    if tx_type == "INCOME":
        for kw in INCOME_SIGNALS:
            if kw in lower_raw or kw in lower_clean:
                return NormalizedMerchant(
                    raw_description=s,
                    clean_merchant=cleaned.title(),
                    channel=channel,
                    category=kw.capitalize(),
                    category_source="merchant_rule",
                    confidence=0.9,
                )
        return NormalizedMerchant(
            raw_description=s,
            clean_merchant=cleaned.title(),
            channel=channel,
            category="Income",
            category_source="default",
            confidence=0.7,
        )

    if channel == "ATM":
        clean_name = "ATM Cash Withdrawal" if tx_type == "EXPENSE" else "ATM Deposit"
        return NormalizedMerchant(
            raw_description=s,
            clean_merchant=clean_name,
            channel="ATM",
            category="General",
            category_source="merchant_rule",
            confidence=0.9,
        )

    # 2. Check Known High-Confidence Merchants
    for key, (display_name, category) in KNOWN_MERCHANTS.items():
        if key in lower_clean or key in lower_raw:
            return NormalizedMerchant(
                raw_description=s,
                clean_merchant=display_name,
                channel=channel,
                category=category,
                category_source="merchant_rule",
                confidence=0.95,
            )

    # 3. Check Keyword Dictionaries
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in lower_raw or kw in lower_clean for kw in keywords):
            return NormalizedMerchant(
                raw_description=s,
                clean_merchant=cleaned.title() if len(cleaned) <= 30 else s[:30],
                channel=channel,
                category=cat,
                category_source="keyword",
                confidence=0.75,
            )

    # 4. Fallback: General
    display_title = cleaned.title() if (cleaned and len(cleaned) <= 40) else s[:40]
    return NormalizedMerchant(
        raw_description=s,
        clean_merchant=display_title,
        channel=channel,
        category="General",
        category_source="default",
        confidence=0.4,
    )

