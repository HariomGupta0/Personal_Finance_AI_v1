"""
Unit tests for Merchant Normalizer & Banking Narration Extraction.
"""

from backend.app.services.merchant_normalizer import normalize_narration


def test_normalize_upi_swiggy():
    result = normalize_narration("UPI/4238910482/SWIGGY/okhdfcbank/Order payment", "EXPENSE")
    assert result.channel == "UPI"
    assert result.clean_merchant == "Swiggy"
    assert result.category == "Food"
    assert result.category_source == "merchant_rule"
    assert result.confidence >= 0.9


def test_normalize_upi_uber():
    result = normalize_narration("UPI/98127391/UBER/paytm/Ride to office", "EXPENSE")
    assert result.channel == "UPI"
    assert result.clean_merchant == "Uber"
    assert result.category == "Transport"
    assert result.category_source == "merchant_rule"


def test_normalize_pos_retail():
    result = normalize_narration("POS 89234 RELIANCE RETAIL MUMBAI", "EXPENSE")
    assert result.channel == "POS"
    assert "Reliance Retail" in result.clean_merchant
    assert result.category == "Shopping"


def test_normalize_atm_withdrawal():
    result = normalize_narration("ATM WDL HDFC BANK KORAMANGALA", "EXPENSE")
    assert result.channel == "ATM"
    assert "ATM Cash Withdrawal" in result.clean_merchant


def test_normalize_income_salary():
    result = normalize_narration("ACH CR TECH CORP SALARY FOR OCT 2026", "INCOME")
    assert result.category == "Salary"
    assert result.category_source == "merchant_rule"


def test_normalize_keyword_fallback():
    result = normalize_narration("Electricity bill BESCOM payment", "EXPENSE")
    assert result.category == "Utilities"


def test_normalize_unknown_merchant():
    result = normalize_narration("RANDOM MERCHANT 99238", "EXPENSE")
    assert result.category == "General"
    assert result.category_source == "default"
    assert result.confidence < 0.5
