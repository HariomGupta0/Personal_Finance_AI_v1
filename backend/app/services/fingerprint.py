"""
Deterministic Transaction Fingerprint Generator.

Computes an idempotent, collision-resistant hash for bank statement transactions
to guarantee zero duplicate ingestion even if files are re-uploaded.
"""

from __future__ import annotations

import hashlib
import re
from typing import Optional

from backend.app.core.money import from_paise, to_paise


def compute_transaction_fingerprint(
    account_id: str,
    date_str: str,
    amount: float,
    tx_type: str,
    description: str,
    source_ref: Optional[str] = None,
    occurrence_index: int = 0,
) -> str:
    """
    Generate a 24-character hexadecimal SHA-256 fingerprint.

    Parameters
    ----------
    account_id : str
        The account to which this transaction belongs.
    date_str : str
        ISO date (YYYY-MM-DD).
    amount : float
        Transaction amount (strictly positive).
    tx_type : str
        'EXPENSE' or 'INCOME'.
    description : str
        Narration / payee description.
    source_ref : Optional[str]
        UTR, Cheque number, or external reference ID if present.
    occurrence_index : int
        The n-th occurrence of this identical transaction within the same batch.
        Guarantees that two legitimate identical ₹20 chai purchases on the same
        day do not collide with each other.

    Returns
    -------
    str : 24-char hex string, e.g. "a3b9f1092e48..."
    """
    clean_desc = re.sub(r"\s+", " ", (description or "").strip().lower())
    clean_ref = (source_ref or "").strip().lower()
    amt_formatted = f"{from_paise(to_paise(amount)):.2f}"
    clean_type = (tx_type or "EXPENSE").strip().upper()

    seed = (
        f"{account_id}|{date_str}|{amt_formatted}|{clean_type}|"
        f"{clean_desc}|{clean_ref}|{occurrence_index}"
    )

    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
