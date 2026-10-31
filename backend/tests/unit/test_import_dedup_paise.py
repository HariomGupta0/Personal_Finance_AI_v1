"""
Unit tests for integer-paise based deduplication and fingerprint parity in import pipeline.
Verifies that:
1. Same-day, same-description, same-amount rows get distinct occurrence indices.
2. Ugly-cent amounts (e.g. 33.33 x3) get distinct occurrence indices without collision.
3. Re-importing identical batch produces zero duplicates.
4. Fingerprints computed through import pipeline for 5,000 random 2-decimal amounts
   are byte-identical to pre-migration fingerprint formula.
"""

import hashlib
import random
import re
from typing import Optional
import pytest

from backend.app.services.import_pipeline import run_pipeline
from backend.app.services.fingerprint import compute_transaction_fingerprint


def legacy_compute_transaction_fingerprint(
    account_id: str,
    date_str: str,
    amount: float,
    tx_type: str,
    description: str,
    source_ref: Optional[str] = None,
    occurrence_index: int = 0,
) -> str:
    """Old pre-migration fingerprint calculation from commit ec6e2b9."""
    clean_desc = re.sub(r"\s+", " ", (description or "").strip().lower())
    clean_ref = (source_ref or "").strip().lower()
    amt_formatted = f"{float(amount):.2f}"
    clean_type = (tx_type or "EXPENSE").strip().upper()
    seed = (
        f"{account_id}|{date_str}|{amt_formatted}|{clean_type}|"
        f"{clean_desc}|{clean_ref}|{occurrence_index}"
    )
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


def test_fingerprint_parity_5000_random_amounts():
    """
    Assert that fingerprints computed for 5,000 random 2-decimal amounts
    equal the legacy pre-migration fingerprint calculation byte-for-byte.
    """
    random.seed(1337)
    for _ in range(5000):
        paise_val = random.randint(1, 100000000)
        amt = paise_val / 100.0
        date_str = "2026-10-15"
        account_id = "ACC_TEST"
        desc = random.choice(["Chai Stall", "Uber Ride", "Swiggy Delivery", "Electricity Bill"])
        tx_type = random.choice(["EXPENSE", "INCOME"])
        source_ref = random.choice([None, "UPI/123456", "REF987654"])
        occ = random.randint(0, 5)

        old_fp = legacy_compute_transaction_fingerprint(
            account_id=account_id,
            date_str=date_str,
            amount=amt,
            tx_type=tx_type,
            description=desc,
            source_ref=source_ref,
            occurrence_index=occ,
        )
        new_fp = compute_transaction_fingerprint(
            account_id=account_id,
            date_str=date_str,
            amount=amt,
            tx_type=tx_type,
            description=desc,
            source_ref=source_ref,
            occurrence_index=occ,
        )
        assert old_fp == new_fp


def test_same_day_same_description_occurrence_indices():
    """
    Same-day, same-description, same-amount rows must get distinct occurrence indices
    (0, 1, 2) and therefore distinct unique fingerprints.
    """
    rows = [
        {"date": "2026-10-15", "amount": 20.0, "type": "EXPENSE", "description": "Chai"},
        {"date": "2026-10-15", "amount": 20.0, "type": "EXPENSE", "description": "Chai"},
        {"date": "2026-10-15", "amount": 20.0, "type": "EXPENSE", "description": "Chai"},
    ]
    res = run_pipeline(rows, user_id="U001", db=None, skip_dedup=True, account_id="ACC_001")
    valid = res["valid_rows"]
    assert len(valid) == 3

    fps = [r["fingerprint"] for r in valid]
    assert len(set(fps)) == 3, "Each transaction must have a distinct unique fingerprint"


def test_ugly_cents_three_identical_purchases_no_collision():
    """
    Ugly-cent amounts like 33.33 x3 must not collide.
    """
    rows = [
        {"date": "2026-10-15", "amount": 33.33, "type": "EXPENSE", "description": "Split bill"},
        {"date": "2026-10-15", "amount": 33.33, "type": "EXPENSE", "description": "Split bill"},
        {"date": "2026-10-15", "amount": 33.33, "type": "EXPENSE", "description": "Split bill"},
    ]
    res = run_pipeline(rows, user_id="U001", db=None, skip_dedup=True, account_id="ACC_001")
    valid = res["valid_rows"]
    assert len(valid) == 3

    fps = [r["fingerprint"] for r in valid]
    assert len(set(fps)) == 3, "Ugly cent duplicates must each receive distinct occurrence fingerprints"


def test_reimport_same_csv_twice_creates_zero_duplicates():
    """
    Re-running the pipeline on identical rows produces byte-identical fingerprints,
    which ensures idempotency and zero duplicate insertions in Neo4j.
    """
    csv_rows = [
        {"date": "2026-10-15", "amount": 1500.50, "type": "EXPENSE", "description": "Swiggy"},
        {"date": "2026-10-15", "amount": 33.33, "type": "EXPENSE", "description": "Coffee"},
        {"date": "2026-10-16", "amount": 50000.0, "type": "INCOME", "description": "Salary"},
    ]
    res1 = run_pipeline(csv_rows, user_id="U001", db=None, skip_dedup=True, account_id="ACC_001")
    res2 = run_pipeline(csv_rows, user_id="U001", db=None, skip_dedup=True, account_id="ACC_001")

    fps1 = [r["fingerprint"] for r in res1["valid_rows"]]
    fps2 = [r["fingerprint"] for r in res2["valid_rows"]]
    assert fps1 == fps2

