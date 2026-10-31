"""
Unit tests for backend/app/core/money.py helper module.
"""

from decimal import Decimal
import math
import random
import pytest

from backend.app.core.money import (
    div_paise,
    format_inr,
    from_paise,
    mul_paise,
    paise_to_float,
    ratio,
    round_nearest_paise,
    to_paise,
)


def test_float_addition_representation():
    # 0.1 + 0.2 as binary float is 0.30000000000000004
    assert to_paise(0.1 + 0.2) == 30


def test_standard_two_decimal_conversion():
    assert to_paise(1234.56) == 123456
    assert to_paise("1234.56") == 123456
    assert to_paise(Decimal("1234.56")) == 123456


def test_round_half_up_cases():
    # 0.005 rounds up to 0.01 -> 1 paise
    assert to_paise(0.005) == 1
    assert to_paise(Decimal("0.005")) == 1

    # 0.015 rounds up to 0.02 -> 2 paise
    assert to_paise(0.015) == 2
    assert to_paise(Decimal("0.015")) == 2

    # 2.675 rounds up to 2.68 -> 268 paise
    assert to_paise(2.675) == 268
    assert to_paise(Decimal("2.675")) == 268


def test_string_parsing_currency_symbols():
    # Strip ₹, Rs, commas, spaces
    assert to_paise("₹1,500.00") == 150000
    assert to_paise("Rs. 1,500.00") == 150000
    assert to_paise("Rs 1500.00") == 150000
    assert to_paise("1,00,000") == 10000000
    assert to_paise("₹ 1,00,000.50") == 10000050


def test_negative_values_raise_value_error():
    with pytest.raises(ValueError):
        to_paise(-10)
    with pytest.raises(ValueError):
        to_paise(-0.01)
    with pytest.raises(ValueError):
        to_paise(Decimal("-5.00"))
    with pytest.raises(ValueError):
        to_paise("-1500.00")
    with pytest.raises(ValueError):
        to_paise("(1234.56)")


def test_invalid_types_and_values_raise_value_error():
    with pytest.raises(ValueError):
        to_paise(None)
    with pytest.raises(ValueError):
        to_paise(True)
    with pytest.raises(ValueError):
        to_paise(False)
    with pytest.raises(ValueError):
        to_paise(float("nan"))
    with pytest.raises(ValueError):
        to_paise(float("inf"))
    with pytest.raises(ValueError):
        to_paise(float("-inf"))
    with pytest.raises(ValueError):
        to_paise(Decimal("NaN"))
    with pytest.raises(ValueError):
        to_paise("abc")
    with pytest.raises(ValueError):
        to_paise("")


def test_large_values():
    large_rupees = 10**9
    assert to_paise(large_rupees) == 10**11
    assert from_paise(10**11) == Decimal("1000000000.00")


def test_from_paise():
    assert from_paise(123456) == Decimal("1234.56")
    assert from_paise(-5) == Decimal("-0.05")
    assert from_paise(0) == Decimal("0.00")

    with pytest.raises(TypeError):
        from_paise(1234.56)  # float not allowed
    with pytest.raises(TypeError):
        from_paise("123456")  # str not allowed
    with pytest.raises(TypeError):
        from_paise(True)  # bool not allowed


def test_paise_to_float():
    assert paise_to_float(123456) == 1234.56
    assert paise_to_float(-5) == -0.05
    assert paise_to_float(0) == 0.0


def test_mul_paise():
    assert mul_paise(6300000, "0.40") == 2520000
    assert mul_paise(6300000, 3) == 18900000
    assert mul_paise(100, Decimal("0.333")) == 33
    assert mul_paise(100, Decimal("0.335")) == 34

    with pytest.raises(TypeError):
        mul_paise(100.0, 3)
    with pytest.raises(ValueError):
        mul_paise(100, None)
    with pytest.raises(ValueError):
        mul_paise(100, float("nan"))


def test_ratio():
    assert ratio(100, 200) == 0.5
    assert ratio(0, 500) == 0.0
    assert ratio(100, 0) is None

    with pytest.raises(TypeError):
        ratio(100.0, 200)
    with pytest.raises(TypeError):
        ratio(100, 200.0)
    with pytest.raises(TypeError):
        ratio(True, 100)


def test_format_inr():
    assert format_inr(12000050) == "₹1,20,000.50"
    assert format_inr(10000000) == "₹1,00,000.00"
    assert format_inr(0) == "₹0.00"
    assert format_inr(50) == "₹0.50"
    assert format_inr(50000) == "₹500.00"
    assert format_inr(150000) == "₹1,500.00"
    assert format_inr(-50000) == "-₹500.00"
    assert format_inr(-12000050) == "-₹1,20,000.50"
    assert format_inr(10**11) == "₹1,00,00,00,000.00"

    with pytest.raises(TypeError):
        format_inr(123.45)
    with pytest.raises(TypeError):
        format_inr(True)


def test_round_trip_property_10k_random():
    rng = random.Random(42)
    for _ in range(10_000):
        # Generate random 2-decimal rupee values between 0.00 and 1,000,000.00
        cents = rng.randint(0, 100_000_000)
        rupees_str = f"{cents // 100}.{cents % 100:02d}"
        val_float = float(rupees_str)

        paise = to_paise(val_float)
        assert paise == cents

        dec = from_paise(paise)
        expected_dec = Decimal(rupees_str).quantize(Decimal("0.01"))
        assert dec == expected_dec


def test_div_paise():
    assert div_paise(1000, 2) == 500
    assert div_paise(1, 2) == 1  # 0.5 -> 1 (ROUND_HALF_UP)
    assert div_paise(3, 2) == 2  # 1.5 -> 2
    assert div_paise(100, 3) == 33  # 33.333... -> 33
    assert div_paise(200, 3) == 67  # 66.666... -> 67
    assert div_paise(-100, 3) == -33

    with pytest.raises(ValueError, match="Divisor cannot be zero"):
        div_paise(100, 0)

    with pytest.raises(TypeError):
        div_paise(100, 2.5)  # non-integer divisor

    with pytest.raises(TypeError):
        div_paise(100.5, 2)  # non-integer paise

    with pytest.raises(TypeError):
        div_paise(True, 2)

    with pytest.raises(TypeError):
        div_paise(100, False)


def test_round_nearest_paise():
    # 50 rupees = 5000 paise
    assert round_nearest_paise(0, 5000) == 0
    assert round_nearest_paise(2499, 5000) == 0
    assert round_nearest_paise(2500, 5000) == 5000  # half up
    assert round_nearest_paise(4999, 5000) == 5000
    assert round_nearest_paise(5000, 5000) == 5000
    assert round_nearest_paise(7499, 5000) == 5000
    assert round_nearest_paise(7500, 5000) == 10000  # half up
    assert round_nearest_paise(360000, 5000) == 360000
    assert round_nearest_paise(120109, 5000) == 120000
    assert round_nearest_paise(89999, 5000) == 90000

    # Custom steps
    assert round_nearest_paise(45, 10) == 50
    assert round_nearest_paise(44, 10) == 40

    with pytest.raises(ValueError, match="Step must be positive"):
        round_nearest_paise(100, 0)

    with pytest.raises(ValueError, match="Step must be positive"):
        round_nearest_paise(100, -5000)

    with pytest.raises(ValueError, match="Amount must be non-negative"):
        round_nearest_paise(-100, 5000)

    with pytest.raises(TypeError):
        round_nearest_paise(True, 5000)

    with pytest.raises(TypeError):
        round_nearest_paise(5000, False)


