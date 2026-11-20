"""
Money helper module for integer paise representation.

Contract:
- All "to_" functions accept RUPEE values and return integer PAISE.
- 1 Rupee = 100 Paise.
- Paise values must NEVER be passed into to_paise.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import math
import re
from typing import Any


_STRIP_REGEX = re.compile(r"(?i)\brs\.?|\binr\b|[₹,\s]")


def to_paise(value: Any) -> int:
    """
    Convert a rupee value (int, float, str, Decimal) to integer paise.
    Supports both positive and negative values (refunds, negative balances).
    Negative ties round away from zero with ROUND_HALF_UP (e.g. -0.005 -> -1 paise, -2.675 -> -268 paise).

    Parameters
    ----------
    value : int | float | str | Decimal
        A monetary amount in Rupees (can be positive, zero, or negative).

    Returns
    -------
    int
        The monetary amount in Paise.

    Raises
    -------
    ValueError
        If value is None, bool, NaN, Inf, parenthesised negative like (1234.56),
        or an unparseable string.
    """
    if value is None or isinstance(value, bool):
        raise ValueError(f"Invalid type for to_paise: {type(value).__name__}")

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            raise ValueError("Empty string cannot be converted to paise")
        if "(" in raw or ")" in raw:
            raise ValueError(f"Parenthesised negative values are not supported: {value}")

        cleaned = _STRIP_REGEX.sub("", raw).strip()
        if not cleaned or cleaned in ("-", "+"):
            raise ValueError(f"No numeric value found in: {value}")

        try:
            d = Decimal(cleaned)
            if d.is_nan() or d.is_infinite():
                raise ValueError("NaN and Inf cannot be converted to paise")
        except Exception as exc:
            raise ValueError(f"Unparseable currency string: {value}") from exc

    elif isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError("NaN and Inf cannot be converted to paise")
        d = Decimal(str(value))

    elif isinstance(value, int):
        d = Decimal(value)

    elif isinstance(value, Decimal):
        if value.is_nan() or value.is_infinite():
            raise ValueError("NaN and Inf cannot be converted to paise")
        d = value

    else:
        raise ValueError(f"Unsupported type for to_paise: {type(value).__name__}")

    rounded = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(rounded * 100)


def normalize_rupees(value: Any) -> float:
    """
    Convert any rupee input (int, float, str, Decimal) to a rupee float that is exactly
    the 2-decimal ROUND_HALF_UP value, using Decimal without float arithmetic, by routing
    through to_paise and paise_to_float.

    Parameters
    ----------
    value : int | float | str | Decimal
        Monetary amount in Rupees.

    Returns
    -------
    float
        Clean 2-decimal rupee float.
    """
    return paise_to_float(to_paise(value))


def from_paise(p: int) -> Decimal:
    """
    Convert integer paise to exact Decimal rupees quantized to 2 decimal places.

    Parameters
    ----------
    p : int
        Amount in Paise (may be negative).

    Returns
    -------
    Decimal
        Amount in Rupees, e.g. Decimal("12.34").

    Raises
    -------
    TypeError
        If p is not an integer.
    """
    if isinstance(p, bool) or not isinstance(p, int):
        raise TypeError(f"Expected int paise, got {type(p).__name__}")

    return (Decimal(p) / Decimal(100)).quantize(Decimal("0.01"))


def paise_to_float(p: int) -> float:
    """
    Convert integer paise to float rupees for JSON/API output serialization only.

    Parameters
    ----------
    p : int
        Amount in Paise.

    Returns
    -------
    float
        Amount in Rupees.
    """
    return float(from_paise(p))


def mul_paise(p: int, factor: int | float | str | Decimal) -> int:
    """
    Multiply paise by a factor using Decimal and ROUND_HALF_UP.

    Parameters
    ----------
    p : int
        Amount in Paise.
    factor : int | float | str | Decimal
        Multiplication factor (e.g. 3, "0.40", Decimal("0.40")).

    Returns
    -------
    int
        Resulting amount in Paise.
    """
    if isinstance(p, bool) or not isinstance(p, int):
        raise TypeError(f"Expected int paise, got {type(p).__name__}")

    if isinstance(factor, bool) or factor is None:
        raise ValueError(f"Invalid factor type: {type(factor).__name__}")

    if isinstance(factor, float):
        if math.isnan(factor) or math.isinf(factor):
            raise ValueError("NaN and Inf factors not supported")
        f = Decimal(str(factor))
    elif isinstance(factor, (int, str, Decimal)):
        f = Decimal(factor) if not isinstance(factor, int) else Decimal(str(factor))
        if f.is_nan() or f.is_infinite():
            raise ValueError("NaN and Inf factors not supported")
    else:
        raise ValueError(f"Unsupported factor type: {type(factor).__name__}")

    result = (Decimal(p) * f).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(result)


def ratio(num_paise: int, den_paise: int) -> float | None:
    """
    Compute ratio num_paise / den_paise as float. Returns None if den_paise is 0.

    Parameters
    ----------
    num_paise : int
        Numerator in Paise.
    den_paise : int
        Denominator in Paise.

    Returns
    -------
    float | None
        Ratio as float, or None if denominator is zero.
    """
    if isinstance(num_paise, bool) or not isinstance(num_paise, int):
        raise TypeError(f"Expected int for num_paise, got {type(num_paise).__name__}")
    if isinstance(den_paise, bool) or not isinstance(den_paise, int):
        raise TypeError(f"Expected int for den_paise, got {type(den_paise).__name__}")

    if den_paise == 0:
        return None

    return float(num_paise / den_paise)


def format_inr(paise: int) -> str:
    """
    Format integer paise into Indian currency string format.
    Example: 12000050 -> "₹1,20,000.50"

    Parameters
    ----------
    paise : int
        Amount in Paise (may be negative).

    Returns
    -------
    str
        Formatted string with Indian comma grouping and ₹ symbol.
    """
    if isinstance(paise, bool) or not isinstance(paise, int):
        raise TypeError(f"Expected int paise, got {type(paise).__name__}")

    is_negative = paise < 0
    abs_paise = abs(paise)
    rupees = abs_paise // 100
    cents = abs_paise % 100

    r_str = str(rupees)
    if len(r_str) <= 3:
        grouped = r_str
    else:
        last3 = r_str[-3:]
        remaining = r_str[:-3]
        groups = []
        while remaining:
            groups.append(remaining[-2:])
            remaining = remaining[:-2]
        groups.reverse()
        grouped = ",".join(groups) + "," + last3

    sign = "-" if is_negative else ""
    return f"{sign}₹{grouped}.{cents:02d}"


def div_paise(p: int, n: int) -> int:
    """
    Divide integer paise by an integer divisor n using Decimal and ROUND_HALF_UP.

    Parameters
    ----------
    p : int
        Amount in Paise (may be negative).
    n : int
        Integer divisor (must not be zero).

    Returns
    -------
    int
        Result in Paise rounded with ROUND_HALF_UP.

    Raises
    -------
    TypeError
        If p or n is not an integer or is a bool.
    ValueError
        If n is zero.
    """
    if isinstance(p, bool) or not isinstance(p, int):
        raise TypeError(f"Expected int paise, got {type(p).__name__}")
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError(f"Expected int divisor, got {type(n).__name__}")
    if n == 0:
        raise ValueError("Divisor cannot be zero")

    result = (Decimal(p) / Decimal(n)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(result)


def round_nearest_paise(p: int, step: int = 5000) -> int:
    """
    Round an integer amount in paise to the nearest multiple of step paise (default 5000 paise = ₹50),
    using Decimal arithmetic with ROUND_HALF_UP.

    Parameters
    ----------
    p : int
        Amount in Paise (non-negative).
    step : int
        Step multiple in Paise (default 5000 = ₹50). Must be positive.

    Returns
    -------
    int
        Amount in Paise rounded to the nearest multiple of step.

    Raises
    -------
    TypeError
        If p or step is not an integer or is a bool.
    ValueError
        If step <= 0 or p < 0.
    """
    if isinstance(p, bool) or not isinstance(p, int):
        raise TypeError(f"Expected int paise, got {type(p).__name__}")
    if isinstance(step, bool) or not isinstance(step, int):
        raise TypeError(f"Expected int step, got {type(step).__name__}")
    if step <= 0:
        raise ValueError("Step must be positive")
    if p < 0:
        raise ValueError("Amount must be non-negative")

    steps = (Decimal(p) / Decimal(step)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(steps) * step



