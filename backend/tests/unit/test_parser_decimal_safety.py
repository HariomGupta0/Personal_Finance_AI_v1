"""
Decimal safety and differential comparison unit tests for:
- backend/app/services/csv_parser.py (_parse_amount)
- backend/app/nlu/transaction_extractor.py
- backend/app/nlu/question_parser.py (extract_candidate_amounts, parse_question)
- backend/app/nlu/query_plan.py (ExpenditureQueryPlan)
"""

from decimal import Decimal, ROUND_HALF_UP
import random
import re
from typing import Optional
import pytest
import pandas as pd

from backend.app.core.money import normalize_rupees, to_paise, paise_to_float
from backend.app.services.csv_parser import _parse_amount
from backend.app.nlu.transaction_extractor import extract_transaction_rules
from backend.app.nlu.question_parser import extract_candidate_amounts
from backend.app.nlu.query_plan import ExpenditureQueryPlan, create_query_plan_from_parsed


# ---------------------------------------------------------------------------
# Old parsing reference functions (copied from commit ec6e2b9)
# ---------------------------------------------------------------------------

def old_csv_parse_amount(raw) -> Optional[float]:
    r"""
    Reference copy of pre-migration _parse_amount from ec6e2b9:backend/app/services/csv_parser.py:

        if raw is None or (isinstance(raw, float) and pd.isna(raw)):
            return None
        raw_str = str(raw).strip()
        if not raw_str or raw_str in ("-", "—", "N/A", "n/a", "nil", "Nil"):
            return None
        cleaned = re.sub(r"[₹$€£¥,\s]", "", raw_str)
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = "-" + cleaned[1:-1]
        try:
            val = float(cleaned)
        except ValueError:
            return None
        return val
    """
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    raw_str = str(raw).strip()
    if not raw_str or raw_str in ("-", "—", "N/A", "n/a", "nil", "Nil"):
        return None
    cleaned = re.sub(r"[₹$€£¥,\s]", "", raw_str)
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    try:
        val = float(cleaned)
    except ValueError:
        return None
    return val


def old_question_parser_extract_multipliers(text: str) -> list[float]:
    r"""
    Reference copy of pre-migration multiplier parsing from ec6e2b9:backend/app/nlu/question_parser.py:

        mult_pattern = re.compile(
            r"(?:(?:₹|rs\.?|inr)\s*)?(\d+(?:\.\d+)?)\s*(k|thousand|lakhs?|lacs?|lac|crores?|cr)\b",
            re.IGNORECASE,
        )
        for m in mult_pattern.finditer(t_lower):
            num = float(m.group(1))
            unit = m.group(2).lower()
            if unit in ["k", "thousand"]:
                amounts.append(round(num * 1000, 2))
            elif unit in ["lakh", "lakhs", "lac", "lacs"]:
                amounts.append(round(num * 100000, 2))
            elif unit in ["crore", "crores", "cr"]:
                amounts.append(round(num * 10000000, 2))
    """
    mult_pattern = re.compile(
        r"(?:(?:₹|rs\.?|inr)\s*)?(\d+(?:\.\d+)?)\s*(k|thousand|lakhs?|lacs?|lac|crores?|cr)\b",
        re.IGNORECASE,
    )
    amounts = []
    for m in mult_pattern.finditer(text.lower()):
        num = float(m.group(1))
        unit = m.group(2).lower()
        if unit in ["k", "thousand"]:
            amounts.append(round(num * 1000, 2))
        elif unit in ["lakh", "lakhs", "lac", "lacs"]:
            amounts.append(round(num * 100000, 2))
        elif unit in ["crore", "crores", "cr"]:
            amounts.append(round(num * 10000000, 2))
    return amounts


def old_transaction_extractor_rules_amount(text: str) -> Optional[float]:
    r"""
    Reference copy of pre-migration amount parsing from ec6e2b9:backend/app/nlu/transaction_extractor.py:

        amount_match = re.search(r"(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)\s*(?:rs|rupees|inr)?", text_clean, re.IGNORECASE)
        if not amount_match:
            return None
        try:
            amount_val = float(amount_match.group(1).replace(",", ""))
        except ValueError:
            return None
        if amount_val <= 0:
            return None
    """
    amount_match = re.search(r"(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d{1,2})?)\s*(?:rs|rupees|inr)?", text, re.IGNORECASE)
    if not amount_match:
        return None
    try:
        amount_val = float(amount_match.group(1).replace(",", ""))
    except ValueError:
        return None
    if amount_val <= 0:
        return None
    return amount_val


# ---------------------------------------------------------------------------
# Test suite
# ---------------------------------------------------------------------------

def test_tricky_strings_decimal_safety():
    """
    Assert exact results for tricky strings:
    "0.1", "0.2", "1,234.565" (tie), "19999.99", "33.335", "(1234.56)", "1,00,000.50", "₹ 2,500",
    "2.5k" -> 2500.0, "1.2 lakh" -> 120000.0, "0.75 crore" -> 7500000.0, "1.1k", "2.675k".
    All expected values are asserted against exact Decimal-derived constants (not float math).
    """
    # 1. Direct CSV parser & normalize_rupees tests
    assert _parse_amount("0.1") == float(Decimal("0.10"))
    assert _parse_amount("0.2") == float(Decimal("0.20"))

    # Tie-breaking for 3 decimals (rounds half up: 1234.565 -> 1234.57)
    expected_tie_1 = float(Decimal("1234.565").quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    assert _parse_amount("1,234.565") == expected_tie_1
    assert _parse_amount("1,234.565") == 1234.57

    assert _parse_amount("19999.99") == float(Decimal("19999.99"))

    # Tie-breaking: 33.335 -> 33.34
    expected_tie_2 = float(Decimal("33.335").quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    assert _parse_amount("33.335") == expected_tie_2
    assert _parse_amount("33.335") == 33.34

    # Bracket negative: (1234.56) -> -1234.56
    assert _parse_amount("(1234.56)") == float(Decimal("-1234.56"))

    # Indian grouping & currency symbol
    assert _parse_amount("1,00,000.50") == float(Decimal("100000.50"))
    assert _parse_amount("₹ 2,500") == float(Decimal("2500.00"))

    # 2. Question parser multipliers
    k_amounts = extract_candidate_amounts("I want to spend 2.5k on a monitor")
    assert k_amounts == [float(Decimal("2.5") * Decimal("1000"))]
    assert k_amounts == [2500.0]

    lakh_amounts = extract_candidate_amounts("Salary is 1.2 lakh")
    assert lakh_amounts == [float(Decimal("1.2") * Decimal("100000"))]
    assert lakh_amounts == [120000.0]

    crore_amounts = extract_candidate_amounts("House costs 0.75 crore")
    assert crore_amounts == [float(Decimal("0.75") * Decimal("10000000"))]
    assert crore_amounts == [7500000.0]

    k11_amounts = extract_candidate_amounts("Spent 1.1k")
    assert k11_amounts == [float(Decimal("1.1") * Decimal("1000"))]
    assert k11_amounts == [1100.0]

    k2675_amounts = extract_candidate_amounts("Phone is 2.675k")
    assert k2675_amounts == [float(Decimal("2.675") * Decimal("1000"))]
    assert k2675_amounts == [2675.0]

    # 3. Transaction extractor
    tx = extract_transaction_rules("Spent 1,234.56 on groceries today")
    assert tx is not None
    assert tx["amount"] == 1234.56

    # 4. Query plan validation
    plan = ExpenditureQueryPlan(amount="1,234.565", amount_min="1,00,000.50")
    assert plan.amount == 1234.57
    assert plan.amount_min == 100000.50


def test_differential_20000_random_amounts():
    """
    Differential test: runs OLD parsing logic against NEW parsing for 20,000 random amounts
    with at most 2 decimals, formatted as plain, comma-grouped, and Indian-grouped strings.
    Asserts old == new across every single random sample.
    """
    def format_indian_grouping(paise_val: int) -> str:
        sign = "-" if paise_val < 0 else ""
        abs_paise = abs(paise_val)
        rupees = abs_paise // 100
        paise = abs_paise % 100
        r_str = str(rupees)
        if len(r_str) <= 3:
            formatted_r = r_str
        else:
            last3 = r_str[-3:]
            remaining = r_str[:-3]
            groups = []
            while len(remaining) > 2:
                groups.insert(0, remaining[-2:])
                remaining = remaining[:-2]
            if remaining:
                groups.insert(0, remaining)
            formatted_r = ",".join(groups) + "," + last3
        return f"{sign}{formatted_r}.{paise:02d}"

    random.seed(42)
    mismatches = []

    for _ in range(20000):
        paise_val = random.randint(-100000000, 100000000)
        fmt = random.choice(["plain", "comma", "indian", "bracket", "symbol"])

        if fmt == "plain":
            raw = f"{paise_val / 100:.2f}"
        elif fmt == "comma":
            raw = f"{paise_val / 100:,.2f}"
        elif fmt == "indian":
            raw = format_indian_grouping(paise_val)
        elif fmt == "bracket":
            raw = f"({abs(paise_val) / 100:.2f})" if paise_val < 0 else f"{paise_val / 100:.2f}"
        elif fmt == "symbol":
            raw = f"₹ {format_indian_grouping(paise_val)}"

        old_res = old_csv_parse_amount(raw)
        new_res = _parse_amount(raw)

        if old_res != new_res:
            mismatches.append((raw, old_res, new_res))

    assert len(mismatches) == 0, f"Found {len(mismatches)} mismatches in 20,000 samples: {mismatches[:5]}"


def test_differential_more_than_two_decimals_ties():
    """
    Inspects differences for amounts with more than 2 decimals.
    Old float(cleaned) retained unrounded 3+ decimal floats.
    New normalize_rupees quantizes to 2 decimals using ROUND_HALF_UP (ties round away from zero).
    """
    tie_diffs = []
    for i in range(1, 1000):
        val = Decimal(i) * Decimal("0.005")
        raw = f"{val:.3f}"
        old_val = old_csv_parse_amount(raw)
        new_val = _parse_amount(raw)

        if old_val != new_val:
            tie_diffs.append((raw, old_val, new_val))

    # All half-way 3-decimal values differ because new rounds to 2 decimals while old did not round
    assert len(tie_diffs) > 0
    for raw, old_val, new_val in tie_diffs[:10]:
        # Assert new_val is exactly the ROUND_HALF_UP 2-decimal float of raw
        expected = float(Decimal(raw).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        assert new_val == expected


def test_transaction_extractor_llm_json_amount_safety():
    """
    Test that None, 'abc', '', 'NaN', True, -5, 0 all return None from
    extract_transaction_llm without raising exceptions.
    """
    import json
    from unittest.mock import patch
    from backend.app.nlu.transaction_extractor import extract_transaction_llm

    test_vals = [None, "abc", "", "NaN", True, -5, 0]
    for val in test_vals:
        fake_payload = json.dumps({
            "amount": val,
            "description": "Coffee",
            "category": "Food",
            "type": "EXPENSE",
        })
        with patch("backend.app.services.llm_service.ask_llm", return_value=fake_payload):
            res = extract_transaction_llm("dummy text")
            assert res is None, f"Expected None for amount {val!r}, got {res}"

