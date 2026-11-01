"""
PII Redaction Service.

Masks sensitive personal and financial identifiers (Account IDs, UPI IDs,
card numbers) before sending prompts or evidence payloads to external LLM
or vision APIs.
"""

from __future__ import annotations

import re
from typing import Any


# Card-like numbers: 13 to 19 digits (optionally grouped by 4 with spaces or hyphens)
CARD_PATTERN = re.compile(r"\b(?:\d{4}[ -]?){3}\d{1,7}\b|\b\d{13,19}\b")

# UPI IDs: user@handle where handle is a known bank or VPA domain
UPI_PATTERN = re.compile(
    r"\b([a-zA-Z0-9.\-_]{2,})@([a-zA-Z0-9.\-]{2,})\b"
)

# Account IDs: explicit account prefixes or "Account: ..." patterns
ACCOUNT_PATTERN = re.compile(
    r"(?i)\b(account(?:[_\s]*(?:id|no|number|num))?|acct|a/c)[\s_#:=-]*([a-zA-Z0-9_-]{3,})\b"
)

# Specific node-level account IDs like ACC001, A001, ACC_12345
NODE_ACCOUNT_PATTERN = re.compile(r"\b(ACC[0-9A-Za-z_]+|A\d{3,})\b")


def mask_card_number(match: re.Match) -> str:
    raw = match.group(0)
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 13 or len(digits) > 19:
        return raw
    last4 = digits[-4:]
    return f"****-****-****-{last4}"


def mask_upi_id(match: re.Match) -> str:
    user = match.group(1)
    handle = match.group(2)
    # Don't mask common domain extensions in plain text if it's not a handle/email
    masked_user = user[0] + "***" if len(user) > 1 else "***"
    return f"{masked_user}@{handle}"


def mask_account(match: re.Match) -> str:
    prefix = match.group(1)
    acct = match.group(2)
    masked_acct = acct[:2] + "***" if len(acct) > 3 else "***"
    return f"{prefix} {masked_acct}"


def mask_node_account(match: re.Match) -> str:
    val = match.group(1)
    return f"{val[:2]}***"


def redact_pii(text: str) -> str:
    """
    Mask account IDs, UPI IDs, and card-like numbers in text before
    dispatching to external APIs. Preserves currency amounts and dates.
    """
    if not text or not isinstance(text, str):
        return text

    # 1. Mask card numbers
    redacted = CARD_PATTERN.sub(mask_card_number, text)

    # 2. Mask UPI IDs
    redacted = UPI_PATTERN.sub(mask_upi_id, redacted)

    # 3. Mask descriptive Account patterns (e.g. "Account No: 123456789")
    redacted = ACCOUNT_PATTERN.sub(mask_account, redacted)

    # 4. Mask node-level Account IDs (e.g. "ACC001", "A001")
    redacted = NODE_ACCOUNT_PATTERN.sub(mask_node_account, redacted)

    return redacted


def redact_payload(payload: Any) -> Any:
    """Recursively redact text in nested dictionaries, lists, or strings."""
    if isinstance(payload, str):
        return redact_pii(payload)
    if isinstance(payload, list):
        return [redact_payload(item) for item in payload]
    if isinstance(payload, dict):
        return {k: redact_payload(v) for k, v in payload.items()}
    return payload
