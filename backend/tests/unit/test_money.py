"""
Unit tests for backend/app/core/money.py helper module.
"""

from decimal import Decimal
import math
import random
import pytest

from backend.app.core.money import (
    from_paise,
    mul_paise,
    paise_to_float,
    ratio,
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
