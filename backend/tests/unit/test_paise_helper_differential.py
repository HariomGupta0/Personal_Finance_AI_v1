"""
Differential tests for _parse_paise in financial_engine and financial_planner.
Verifies that simplifying _parse_paise by removing the negate-and-invert workaround
(-to_paise(-val) and string slicing -to_paise(s[1:])) produces identical outputs to the
original helper across edge cases, type variations, and a 10,000-sample random sweep.
"""

from decimal import Decimal
import random
from typing import Any
import pytest

from backend.app.core.money import to_paise
from backend.app.engine.financial_engine import _parse_paise as engine_parse_paise
from backend.app.services.financial_planner import _parse_paise as planner_parse_paise


def old_engine_parse_paise(val: Any, allow_negative: bool = False) -> int:
    """
    Verbatim copy of _parse_paise from financial_engine.py prior to Part B refactor:

    def _parse_paise(val: Any, allow_negative: bool = False) -> int:
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
                if not allow_negative and s.startswith("-"):
                    return 0
                return to_paise(s)
            return to_paise(val)
        except (ValueError, TypeError):
            return 0
    """
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
            if not allow_negative and s.startswith("-"):
                return 0
            return to_paise(s)
        return to_paise(val)
    except (ValueError, TypeError):
        return 0


def old_planner_parse_paise(val: Any, allow_negative: bool = False) -> int:
    """
    Verbatim copy of _parse_paise from financial_planner.py prior to Part B refactor:

    def _parse_paise(val: Any, allow_negative: bool = False) -> int:
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
                if not allow_negative and s.startswith("-"):
                    return 0
                return to_paise(s)
            return to_paise(val)
        except (ValueError, TypeError):
            return 0
    """
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
            if not allow_negative and s.startswith("-"):
                return 0
            return to_paise(s)
        return to_paise(val)
    except (ValueError, TypeError):
        return 0


TEST_MATRIX = [
    None,
    True,
    False,
    "",
    "abc",
    "NaN",
    "inf",
    0,
    -0.0,
    1,
    -1,
    0.1,
    -0.1,
    0.005,
    -0.005,
    2.675,
    -2.675,
    1234.565,
    Decimal("1.005"),
    Decimal("-1.005"),
    "1,234.50",
    "-1,234.50",
    "(12.34)",
    "₹500",
]


@pytest.mark.parametrize("input_val", TEST_MATRIX)
@pytest.mark.parametrize("allow_negative", [False, True])
def test_engine_parse_paise_matrix(input_val: Any, allow_negative: bool):
    """Engine helper matches the old implementation across all matrix inputs and flag settings."""
    old_res = old_engine_parse_paise(input_val, allow_negative=allow_negative)
    new_res = engine_parse_paise(input_val, allow_negative=allow_negative)
    assert new_res == old_res, f"Engine mismatch for {input_val!r} (allow_neg={allow_negative}): {new_res} != {old_res}"


@pytest.mark.parametrize("input_val", TEST_MATRIX)
@pytest.mark.parametrize("allow_negative", [False, True])
def test_planner_parse_paise_matrix(input_val: Any, allow_negative: bool):
    """Planner helper matches the old implementation across all matrix inputs and flag settings."""
    old_res = old_planner_parse_paise(input_val, allow_negative=allow_negative)
    new_res = planner_parse_paise(input_val, allow_negative=allow_negative)
    assert new_res == old_res, f"Planner mismatch for {input_val!r} (allow_neg={allow_negative}): {new_res} != {old_res}"


def test_parse_paise_random_sweep_10k():
    """Verify 0 differential differences across 10,000 random 2-decimal amounts."""
    rng = random.Random(1337)
    diff_count = 0

    for _ in range(10000):
        val = round(rng.uniform(-1000000.0, 1000000.0), 2)
        for allow_neg in (False, True):
            old_e = old_engine_parse_paise(val, allow_negative=allow_neg)
            new_e = engine_parse_paise(val, allow_negative=allow_neg)
            old_p = old_planner_parse_paise(val, allow_negative=allow_neg)
            new_p = planner_parse_paise(val, allow_negative=allow_neg)

            if old_e != new_e or old_p != new_p or new_e != new_p:
                diff_count += 1

    assert diff_count == 0, f"Found {diff_count} differences in 10,000 random sweep"
