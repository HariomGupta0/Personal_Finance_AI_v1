"""
Unit tests for backend/scripts/migrate_money_to_paise.py.
Verifies pure-Python census, decimal detection, paise calculation,
and idempotency/mismatch handling without requiring a database connection.
"""

from decimal import Decimal
import pytest

from backend.scripts.migrate_money_to_paise import (
    NodeMoneyRecord,
    analyze_records,
    has_more_than_two_decimals,
)


def test_has_more_than_two_decimals():
    assert has_more_than_two_decimals(100) is False
    assert has_more_than_two_decimals(100.5) is False
    assert has_more_than_two_decimals(100.55) is False
    assert has_more_than_two_decimals(100.555) is True
    assert has_more_than_two_decimals("12.345") is True
    assert has_more_than_two_decimals("12.34") is False
    assert has_more_than_two_decimals(None) is False
    assert has_more_than_two_decimals(True) is False


def test_analyze_records_types_and_census():
    records = [
        NodeMoneyRecord(node_id=1, element_id="4:1", legacy_val=100),
        NodeMoneyRecord(node_id=2, element_id="4:2", legacy_val=250.75),
        NodeMoneyRecord(node_id=3, element_id="4:3", legacy_val=-50.25),  # negative
        NodeMoneyRecord(node_id=4, element_id="4:4", legacy_val=0.07),    # ugly cents
        NodeMoneyRecord(node_id=5, element_id="4:5", legacy_val=None),     # null
    ]

    census, items_to_write = analyze_records("Transaction", "amount", "amount_paise", records)

    assert census.total_nodes == 5
    assert census.null_count == 1
    assert census.int_count == 1
    assert census.float_count == 3
    assert census.min_val == -50.25
    assert census.max_val == 250.75
    assert census.over_two_decimals_count == 0
    assert census.would_migrate_count == 4
    assert census.already_migrated_count == 0
    assert census.mismatch_drift_count == 0

    assert items_to_write == [
        (1, 10000),
        (2, 25075),
        (3, -5025),
        (4, 7),
    ]


def test_analyze_records_over_two_decimals_detection():
    records = [
        NodeMoneyRecord(node_id=10, element_id="4:10", legacy_val=12.345),
        NodeMoneyRecord(node_id=11, element_id="4:11", legacy_val=99.999),
        NodeMoneyRecord(node_id=12, element_id="4:12", legacy_val=50.00),
    ]

    census, _ = analyze_records("Account", "balance", "balance_paise", records)
    assert census.total_nodes == 3
    assert census.over_two_decimals_count == 2
    assert len(census.over_two_decimals_samples) == 2
    assert census.over_two_decimals_samples[0] == (10, 12.345)
    assert census.over_two_decimals_samples[1] == (11, 99.999)


def test_analyze_records_idempotency_and_mismatch():
    records = [
        # Already migrated correctly: 100.50 -> 10050 paise
        NodeMoneyRecord(node_id=20, element_id="4:20", legacy_val=100.50, existing_paise=10050),
        # Mismatch drift: legacy says 50.00 (5000 paise), but existing_paise says 9999 paise
        NodeMoneyRecord(node_id=21, element_id="4:21", legacy_val=50.00, existing_paise=9999),
        # Pending migration:
        NodeMoneyRecord(node_id=22, element_id="4:22", legacy_val=75.25, existing_paise=None),
    ]

    census, items_to_write = analyze_records("Goal", "target_amount", "target_amount_paise", records)

    assert census.already_migrated_count == 1
    assert census.mismatch_drift_count == 1
    assert census.would_migrate_count == 1
    assert len(census.mismatch_samples) == 1
    assert census.mismatch_samples[0] == (21, 50.00, 9999, 5000)

    # Only node 22 is written; node 21 is NOT overwritten
    assert items_to_write == [(22, 7525)]
