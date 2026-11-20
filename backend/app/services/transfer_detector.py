"""
Transfer Detector Service.

Detects and disambiguates internal bank transfers across user accounts:
1. Exact amount matching in paise.
2. Date proximity (window <= 2 calendar days to accommodate inter-bank clearing delays).
3. Opposite transaction types (EXPENSE on Account A vs INCOME on Account B).
4. Strict 1-to-1 matching (no double-pairing).
5. Disqualification of ATM withdrawals, commercial merchants, and external refunds.
6. Narration signals (self-transfer keywords, account number hints).
7. Retroactive candidate discovery across existing accounts in Neo4j.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.core.money import to_paise


# ---------------------------------------------------------------------------
# Regex Patterns
# ---------------------------------------------------------------------------

ATM_PATTERNS = re.compile(
    r"(?i)\b(atm|cash wdl|cash withdrawal|atm-wdl|atw|nfs\b|matm|cash disp|self wdl|atm cash|cwdr)\b"
)

REFUND_PATTERNS = re.compile(
    r"(?i)\b(refund|cashback|reversal|chargeback|interest credited|dividend|subsidy)\b"
)

COMMERCIAL_MERCHANTS = {
    "swiggy", "zomato", "amazon", "flipkart", "uber", "ola", "netflix", "spotify",
    "starbucks", "myntra", "blinkit", "zepto", "irctc", "apollo", "pharmacy",
    "billdesk", "makemytrip", "cleartrip", "bookmyshow", "airtel", "jio", "vi bill",
    "tatasky", "electricity", "broadband", "groceries", "restaurant", "hotel", "cinema",
    "mcdonalds", "kfc", "dominos", "pizza", "croma", "reliance", "nykaa", "cult"
}

TRANSFER_BOOSTER_PATTERNS = re.compile(
    r"(?i)\b(self|own a/c|own account|to a/c|from a/c|transfer to|transfer from|funds transfer|fund transfer|internal transfer|sweep|sweep trf|neft|imps|rtgs|upi/p2p|trf to|trf from|self trf)\b"
)

ACCOUNT_NUMBER_HINT_PATTERNS = re.compile(
    r"(?i)(?:a/c|acct|acc|to|from|ending in|x+|[*]+)\s*[:#\-]?\s*(\d{3,6})\b"
)


# ---------------------------------------------------------------------------
# Disqualification & Signal Helpers
# ---------------------------------------------------------------------------

def is_atm_or_cash(desc: str) -> bool:
    """Return True if narration indicates ATM withdrawal or physical cash dispersal."""
    if not desc:
        return False
    return bool(ATM_PATTERNS.search(desc))


def is_external_refund(desc: str, clean_merchant: Optional[str] = None) -> bool:
    """Return True if narration or merchant indicates commercial refund or cash reversal."""
    text = f"{desc or ''} {clean_merchant or ''}".lower()
    return bool(REFUND_PATTERNS.search(text))


def is_commercial_merchant(desc: str, clean_merchant: Optional[str] = None) -> bool:
    """Return True if transaction is linked to a known commercial vendor or merchant."""
    d = (desc or "").lower()
    m = (clean_merchant or "").lower()
    for vendor in COMMERCIAL_MERCHANTS:
        if vendor in d or vendor in m:
            return True
    return False


def has_transfer_signal(desc: str) -> bool:
    """Return True if narration contains explicit inter-account transfer terminology."""
    if not desc:
        return False
    return bool(TRANSFER_BOOSTER_PATTERNS.search(desc))


def extract_account_hint(desc: str) -> Optional[str]:
    """Extract account number suffix if present in narration (e.g. 'A/C ...1234')."""
    if not desc:
        return None
    m = ACCOUNT_NUMBER_HINT_PATTERNS.search(desc)
    return m.group(1) if m else None


def _parse_date(date_val: Any) -> Optional[date]:
    if not date_val:
        return None
    if isinstance(date_val, datetime):
        return date_val.date()
    if isinstance(date_val, date):
        return date_val
    try:
        return date.fromisoformat(str(date_val)[:10])
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Candidate Scoring
# ---------------------------------------------------------------------------

def score_transfer_candidate(
    debit: Dict[str, Any],
    credit: Dict[str, Any],
    account_lookup: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Tuple[float, List[str]]:
    """
    Evaluate transfer compatibility between a debit (EXPENSE) and credit (INCOME).

    Returns:
        (score: float in [0.0, 1.0], reasons: list[str])
    """
    reasons: List[str] = []

    # 1. Basic Type & Account Sanity
    deb_type = str(debit.get("type") or "").upper().strip()
    cred_type = str(credit.get("type") or "").upper().strip()
    if deb_type != "EXPENSE" or cred_type != "INCOME":
        return 0.0, ["INVALID_TYPES"]

    deb_acc = str(debit.get("account_id") or "")
    cred_acc = str(credit.get("account_id") or "")
    if deb_acc and cred_acc and deb_acc == cred_acc:
        # Same account cannot have an internal transfer to itself
        return 0.0, ["SAME_ACCOUNT"]

    # 2. Exact Paise Matching
    try:
        deb_paise = to_paise(debit.get("amount", 0))
        cred_paise = to_paise(credit.get("amount", 0))
    except Exception:
        return 0.0, ["INVALID_AMOUNT"]

    if deb_paise <= 0 or cred_paise <= 0 or deb_paise != cred_paise:
        return 0.0, ["AMOUNT_MISMATCH"]
    reasons.append("EXACT_AMOUNT_MATCH")

    # 3. Disqualify ATM Withdrawals
    deb_desc = str(debit.get("description") or "")
    cred_desc = str(credit.get("description") or "")
    if is_atm_or_cash(deb_desc) or is_atm_or_cash(cred_desc):
        return 0.0, ["ATM_DISQUALIFIED"]

    # 4. Disqualify Commercial Refunds and Merchants
    deb_m = str(debit.get("clean_merchant") or "")
    cred_m = str(credit.get("clean_merchant") or "")
    if is_external_refund(cred_desc, cred_m) or is_external_refund(deb_desc, deb_m):
        return 0.0, ["REFUND_DISQUALIFIED"]
    if is_commercial_merchant(deb_desc, deb_m) or is_commercial_merchant(cred_desc, cred_m):
        return 0.0, ["COMMERCIAL_MERCHANT_DISQUALIFIED"]

    # 5. Date Proximity Check (|d1 - d2| <= 2 calendar days)
    d_deb = _parse_date(debit.get("date"))
    d_cred = _parse_date(credit.get("date"))
    if not d_deb or not d_cred:
        return 0.0, ["DATE_PARSE_ERROR"]

    days_diff = abs((d_deb - d_cred).days)
    if days_diff > 2:
        return 0.0, ["DATE_TOO_FAR"]
    reasons.append(f"DATE_PROXIMITY_{days_diff}_DAYS")

    # 6. Scoring Weights
    score = 0.5  # Base score for valid amount + opposite types + date proximity

    if days_diff == 0:
        score += 0.2
    elif days_diff == 1:
        score += 0.1

    deb_signal = has_transfer_signal(deb_desc)
    cred_signal = has_transfer_signal(cred_desc)
    if deb_signal or cred_signal:
        score += 0.2
        reasons.append("TRANSFER_NARRATION_SIGNAL")

    # Account hint matching
    hint_deb = extract_account_hint(deb_desc)
    hint_cred = extract_account_hint(cred_desc)
    matched_hint = False

    if account_lookup:
        target_cred = account_lookup.get(cred_acc, {})
        target_deb = account_lookup.get(deb_acc, {})
        # If debit narration mentions credit account number
        if hint_deb and any(hint_deb in str(v) for v in target_cred.values() if v):
            score += 0.25
            reasons.append("ACCOUNT_NUMBER_MATCH")
            matched_hint = True
        elif hint_cred and any(hint_cred in str(v) for v in target_deb.values() if v):
            score += 0.25
            reasons.append("ACCOUNT_NUMBER_MATCH")
            matched_hint = True

    final_score = min(1.0, round(score, 2))
    return final_score, reasons


# ---------------------------------------------------------------------------
# Intra-Batch Transfer Detection (1-to-1 Matching)
# ---------------------------------------------------------------------------

def detect_intra_batch_transfers(
    rows: List[Dict[str, Any]],
    user_accounts: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Find internal transfer candidate pairs among rows within the same import batch.
    Enforces strict 1-to-1 matching so no row is assigned to more than one pair.
    """
    if not rows or len(rows) < 2:
        return []

    account_lookup: Dict[str, Dict[str, Any]] = {}
    if user_accounts:
        for acc in user_accounts:
            acc_id = acc.get("id")
            if acc_id:
                account_lookup[acc_id] = acc

    debits: List[Tuple[int, Dict[str, Any]]] = []
    credits: List[Tuple[int, Dict[str, Any]]] = []

    for idx, r in enumerate(rows):
        tx_type = str(r.get("type") or "").upper().strip()
        if tx_type == "EXPENSE":
            debits.append((idx, r))
        elif tx_type == "INCOME":
            credits.append((idx, r))

    if not debits or not credits:
        return []

    scored_pairs = []
    for d_idx, d_row in debits:
        for c_idx, c_row in credits:
            score, reasons = score_transfer_candidate(d_row, c_row, account_lookup)
            if score >= 0.4:
                d_deb = _parse_date(d_row.get("date"))
                d_cred = _parse_date(c_row.get("date"))
                days_diff = abs((d_deb - d_cred).days) if (d_deb and d_cred) else 99
                scored_pairs.append({
                    "score": score,
                    "days_diff": days_diff,
                    "debit_index": d_idx,
                    "credit_index": c_idx,
                    "debit_row": d_row,
                    "credit_row": c_row,
                    "reasons": reasons,
                })

    # Sort descending by score, ascending by date diff, stable by indices
    scored_pairs.sort(key=lambda x: (-x["score"], x["days_diff"], x["debit_index"], x["credit_index"]))

    used_debits: Set[int] = set()
    used_credits: Set[int] = set()
    transfer_candidates: List[Dict[str, Any]] = []

    for pair in scored_pairs:
        d_idx = pair["debit_index"]
        c_idx = pair["credit_index"]
        if d_idx in used_debits or c_idx in used_credits:
            continue

        used_debits.add(d_idx)
        used_credits.add(c_idx)

        score = pair["score"]
        confidence = "HIGH" if score >= 0.75 else ("MEDIUM" if score >= 0.55 else "LOW")
        d_row = pair["debit_row"]
        c_row = pair["credit_row"]

        candidate_id = f"XFER_{d_idx}_{c_idx}"
        transfer_candidates.append({
            "candidate_id": candidate_id,
            "confidence": confidence,
            "score": score,
            "debit_index": d_idx,
            "credit_index": c_idx,
            "amount": d_row.get("amount"),
            "debit_account_id": d_row.get("account_id"),
            "credit_account_id": c_row.get("account_id"),
            "debit_date": d_row.get("date"),
            "credit_date": c_row.get("date"),
            "debit_description": d_row.get("description"),
            "credit_description": c_row.get("description"),
            "reasons": pair["reasons"],
            "is_retroactive": False,
        })

    return transfer_candidates


# ---------------------------------------------------------------------------
# Retroactive Transfer Detection (Against Existing Neo4j Nodes)
# ---------------------------------------------------------------------------

def detect_retroactive_transfers(
    unmatched_rows: List[Tuple[int, Dict[str, Any]]],
    user_id: str,
    db: Any,
    user_accounts: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Match new incoming transactions against existing unlinked transactions in Neo4j.
    Enforces strict 1-to-1 matching so no existing transaction is paired more than once.
    """
    if not unmatched_rows or not hasattr(db, "find_unlinked_transfer_candidates"):
        return []

    account_lookup: Dict[str, Dict[str, Any]] = {}
    if user_accounts:
        for acc in user_accounts:
            acc_id = acc.get("id")
            if acc_id:
                account_lookup[acc_id] = acc

    candidates: List[Dict[str, Any]] = []
    used_existing_ids: Set[str] = set()

    for row_idx, row in unmatched_rows:
        tx_type = str(row.get("type") or "").upper().strip()
        if tx_type not in ("EXPENSE", "INCOME"):
            continue

        opposite_type = "INCOME" if tx_type == "EXPENSE" else "EXPENSE"
        amt = row.get("amount") or 0.0
        try:
            amt_paise = to_paise(amt)
        except Exception:
            continue

        d = _parse_date(row.get("date"))
        if not d:
            continue

        date_from = (d - timedelta(days=2)).isoformat()
        date_to = (d + timedelta(days=2)).isoformat()
        acc_id = row.get("account_id") or ""

        try:
            db_candidates = db.find_unlinked_transfer_candidates(
                user_id=user_id,
                account_id=acc_id,
                opposite_type=opposite_type,
                amount_paise=amt_paise,
                date_from=date_from,
                date_to=date_to,
            )
        except Exception:
            continue

        # Evaluate and score matching records
        scored_matches = []
        for existing in db_candidates:
            ext_id = existing.get("id")
            if not ext_id or ext_id in used_existing_ids:
                continue

            if tx_type == "EXPENSE":
                debit_record = row
                credit_record = existing
            else:
                debit_record = existing
                credit_record = row

            score, reasons = score_transfer_candidate(debit_record, credit_record, account_lookup)
            if score >= 0.4:
                d_ext = _parse_date(existing.get("date"))
                days_diff = abs((d - d_ext).days) if d_ext else 99
                scored_matches.append({
                    "score": score,
                    "days_diff": days_diff,
                    "existing": existing,
                    "reasons": reasons,
                })

        if not scored_matches:
            continue

        # Pick best match 1-to-1
        scored_matches.sort(key=lambda x: (-x["score"], x["days_diff"]))
        best = scored_matches[0]
        ext_match = best["existing"]
        used_existing_ids.add(ext_match["id"])

        score = best["score"]
        confidence = "HIGH" if score >= 0.75 else ("MEDIUM" if score >= 0.55 else "LOW")

        candidates.append({
            "candidate_id": f"XFER_RETRO_{row_idx}_{ext_match['id']}",
            "confidence": confidence,
            "score": score,
            "batch_row_index": row_idx,
            "existing_transaction_id": ext_match["id"],
            "existing_account_id": ext_match.get("account_id"),
            "existing_date": ext_match.get("date"),
            "existing_description": ext_match.get("description"),
            "existing_type": ext_match.get("type"),
            "batch_row_type": tx_type,
            "amount": amt,
            "reasons": best["reasons"],
            "is_retroactive": True,
        })

    return candidates

