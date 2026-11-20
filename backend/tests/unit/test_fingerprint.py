"""
Unit tests for Deterministic Transaction Fingerprint Generator.
"""

from backend.app.services.fingerprint import compute_transaction_fingerprint


def test_fingerprint_deterministic():
    fp1 = compute_transaction_fingerprint("A001", "2026-10-15", 500.0, "EXPENSE", "Swiggy", "REF123", 0)
    fp2 = compute_transaction_fingerprint("A001", "2026-10-15", 500.0, "EXPENSE", "Swiggy", "REF123", 0)
    assert fp1 == fp2
    assert len(fp1) == 24


def test_fingerprint_diff_amount():
    fp1 = compute_transaction_fingerprint("A001", "2026-10-15", 500.0, "EXPENSE", "Swiggy", "REF123", 0)
    fp2 = compute_transaction_fingerprint("A001", "2026-10-15", 500.01, "EXPENSE", "Swiggy", "REF123", 0)
    assert fp1 != fp2


def test_fingerprint_diff_date():
    fp1 = compute_transaction_fingerprint("A001", "2026-10-15", 500.0, "EXPENSE", "Swiggy", "REF123", 0)
    fp2 = compute_transaction_fingerprint("A001", "2026-10-16", 500.0, "EXPENSE", "Swiggy", "REF123", 0)
    assert fp1 != fp2


def test_fingerprint_occurrence_collision_protection():
    # Two legitimate identical ₹20 chai payments on the same day in the same statement
    fp_chai_1 = compute_transaction_fingerprint("A001", "2026-10-15", 20.0, "EXPENSE", "Chai Stall", None, 0)
    fp_chai_2 = compute_transaction_fingerprint("A001", "2026-10-15", 20.0, "EXPENSE", "Chai Stall", None, 1)
    assert fp_chai_1 != fp_chai_2
