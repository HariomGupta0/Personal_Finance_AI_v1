"""
Golden regression test for financial engine and planner calculations.
Re-runs make_engine_golden fixtures and compares outputs against engine_baseline.json.
Floats compare equal at 2 decimal places for money and 4 decimal places for ratios.
"""

from __future__ import annotations

import json
from pathlib import Path

from backend.tests.golden.make_engine_golden import FIXTURES, run_all_functions

BASELINE_FILE = Path(__file__).resolve().parent / "engine_baseline.json"

RATIO_KEYWORDS = (
    "ratio",
    "rate",
    "percentage",
    "pct",
    "dti",
    "fraction",
    "runway",
    "months",
    "score",
)


def _is_ratio_key(key: str) -> bool:
    key_lower = key.lower()
    return any(kw in key_lower for kw in RATIO_KEYWORDS)


def _assert_match(actual, expected, path: str = ""):
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        last_key = path.split(".")[-1].split("[")[0]
        if _is_ratio_key(last_key):
            diff = abs(float(actual) - float(expected))
            assert diff < 1e-4, f"Ratio mismatch at {path}: actual {actual} != expected {expected} (diff={diff})"
        else:
            diff = abs(float(actual) - float(expected))
            assert diff < 1e-2, f"Money mismatch at {path}: actual {actual} != expected {expected} (diff={diff})"
        return

    if type(actual) is not type(expected):
        raise AssertionError(f"Type mismatch at {path}: {type(actual)} != {type(expected)}")

    if isinstance(actual, dict):
        assert set(actual.keys()) == set(expected.keys()), (
            f"Dict keys mismatch at {path}: {set(actual.keys()) ^ set(expected.keys())}"
        )
        for k in expected:
            subpath = f"{path}.{k}" if path else k
            _assert_match(actual[k], expected[k], subpath)
    elif isinstance(actual, list):
        assert len(actual) == len(expected), (
            f"List length mismatch at {path}: {len(actual)} != {len(expected)}"
        )
        for i, (a, e) in enumerate(zip(actual, expected)):
            _assert_match(a, e, f"{path}[{i}]")
    else:
        assert actual == expected, f"Value mismatch at {path}: {actual} != {expected}"


def test_engine_golden_baseline():
    """Verify current engine and planner functions match recorded baseline."""
    assert BASELINE_FILE.exists(), f"Baseline file {BASELINE_FILE} missing."
    with open(BASELINE_FILE, "r", encoding="utf-8") as f:
        baseline = json.load(f)

    for fixture_name, fixture_data in FIXTURES.items():
        assert fixture_name in baseline, f"Missing fixture '{fixture_name}' in baseline."
        actual_output = run_all_functions(fixture_data)
        expected_output = baseline[fixture_name]
        _assert_match(actual_output, expected_output, path=fixture_name)
