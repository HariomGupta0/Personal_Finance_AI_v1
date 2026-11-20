"""
Fingerprint compatibility test.
Asserts that the Decimal-based refactored fingerprint computation is byte-identical
to the legacy float-based implementation across 20,000 random amounts with at most 2 decimals.
"""

from __future__ import annotations

import hashlib
import random
import re
from typing import Optional

from backend.app.services.fingerprint import compute_transaction_fingerprint
from backend.tests.unit.test_fingerprint import (
    test_fingerprint_deterministic,
    test_fingerprint_diff_amount,
    test_fingerprint_diff_date,
    test_fingerprint_occurrence_collision_protection,
)


def legacy_compute_transaction_fingerprint(
    account_id: str,
    date_str: str,
    amount: float,
    tx_type: str,
    description: str,
    source_ref: Optional[str] = None,
    occurrence_index: int = 0,
) -> str:
    """Exact copy of the OLD formula for verification reference."""
    clean_desc = re.sub(r"\s+", " ", (description or "").strip().lower())
    clean_ref = (source_ref or "").strip().lower()
    amt_formatted = f"{float(amount):.2f}"
    clean_type = (tx_type or "EXPENSE").strip().upper()

    seed = (
        f"{account_id}|{date_str}|{amt_formatted}|{clean_type}|"
        f"{clean_desc}|{clean_ref}|{occurrence_index}"
    )

    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


def test_specific_amounts_identical():
    test_amounts = [
        0.01,
        0.10,
        500.0,
        500.01,
        19999.99,
        1234.5,
        100000.0,
        0.1 + 0.2,  # 0.30000000000000004
    ]
    for amt in test_amounts:
        old_fp = legacy_compute_transaction_fingerprint(
            "ACC_1", "2026-10-15", amt, "EXPENSE", "Swiggy Order", "REF_99", 0
        )
        new_fp = compute_transaction_fingerprint(
            "ACC_1", "2026-10-15", amt, "EXPENSE", "Swiggy Order", "REF_99", 0
        )
        assert old_fp == new_fp, f"Mismatch for amount {amt}: old={old_fp}, new={new_fp}"


def test_20000_random_amounts_identical():
    rng = random.Random(2026)
    for _ in range(20_000):
        cents = rng.randint(1, 100_000_000)
        # Amounts with at most 2 decimal places
        amt = cents / 100.0
        old_fp = legacy_compute_transaction_fingerprint(
            "A001", "2026-10-15", amt, "EXPENSE", "Merchant Test", "REF123", 0
        )
        new_fp = compute_transaction_fingerprint(
            "A001", "2026-10-15", amt, "EXPENSE", "Merchant Test", "REF123", 0
        )
        assert old_fp == new_fp


def test_legacy_unmodified_suite():
    """Verify original tests pass unmodified."""
    test_fingerprint_deterministic()
    test_fingerprint_diff_amount()
    test_fingerprint_diff_date()
    test_fingerprint_occurrence_collision_protection()


def test_tie_differences_for_more_than_two_decimals():
    """
    Demonstrates documented tie cases where >2 decimals legitimately differ
    between IEEE-754 binary float formatting and Decimal ROUND_HALF_UP.
    """
    # 2.675 in binary float is 2.6749999999999998... -> f"{float:.2f}" gives "2.67"
    # In Decimal with ROUND_HALF_UP, 2.675 -> 2.68 -> "2.68"
    old_fp = legacy_compute_transaction_fingerprint("A", "2026-10-15", 2.675, "EXPENSE", "Tie", None, 0)
    new_fp = compute_transaction_fingerprint("A", "2026-10-15", 2.675, "EXPENSE", "Tie", None, 0)
    assert old_fp != new_fp  # Legitimately differs at 3-decimal tie

