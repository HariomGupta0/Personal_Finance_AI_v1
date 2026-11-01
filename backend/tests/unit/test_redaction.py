"""
Unit tests for PII Redaction before external API calls.
Validates masking of Account IDs, UPI IDs, and card numbers while preserving
financial figures, currency symbols (₹), percentages, and ISO dates.
"""

from unittest.mock import MagicMock, patch
import pytest

from backend.app.services.redaction import redact_pii, redact_payload
from backend.app.services.llm_service import ask_llm, ask_llm_async


def test_redact_account_ids():
    """Account identifiers and bank account numbers must be masked."""
    # Descriptive account expressions
    assert "987654" not in redact_pii("User account number: 9876543210")
    assert "12345" not in redact_pii("Acct: 123456789")
    assert "54321" not in redact_pii("Transfer to a/c 5432167890")

    # Node account IDs
    res1 = redact_pii("Transaction from node ACC001234 to node ACC0099")
    assert "ACC001234" not in res1
    assert "ACC0099" not in res1

    res2 = redact_pii("Account A001 has liquid balance ₹45,000")
    assert "A001" not in res2
    assert "₹45,000" in res2  # Financial balance preserved


def test_redact_upi_ids():
    """UPI virtual payment addresses must have user handles masked."""
    sample = "Paid ₹350 to rahul.sharma@okaxis and swiggy@okhdfcbank via UPI"
    redacted = redact_pii(sample)

    assert "rahul.sharma" not in redacted
    assert "@okaxis" in redacted
    assert "swiggy" not in redacted
    assert "@okhdfcbank" in redacted
    assert "₹350" in redacted  # Amount preserved


def test_redact_card_numbers():
    """13-19 digit card numbers must be masked to last 4 digits only."""
    # Hyphenated
    res1 = redact_pii("Charged on card 4111-2222-3333-4444 today")
    assert "4111-2222-3333" not in res1
    assert "****-****-****-4444" in res1

    # Spaced
    res2 = redact_pii("Card 5500 1234 5678 9012 authorized")
    assert "5500 1234" not in res2
    assert "****-****-****-9012" in res2

    # Unseparated 16-digit
    res3 = redact_pii("Card 4111222233338888 used")
    assert "411122223333" not in res3
    assert "****-****-****-8888" in res3


def test_redact_preserves_financial_values_dates_and_percentages():
    """Normal financial figures, dates, and percentages must NOT be mangled."""
    text = (
        "On 2026-09-15, monthly expenses were ₹45,000.50. "
        "Savings rate reached 35.5% with a reserve of ₹1,35,000 across 3 months."
    )
    redacted = redact_pii(text)
    assert "2026-09-15" in redacted
    assert "₹45,000.50" in redacted
    assert "35.5%" in redacted
    assert "₹1,35,000" in redacted


def test_redact_payload_nested_structure():
    """Recursive payload redaction should sanitize nested lists and dicts."""
    data = {
        "user": "Rahul",
        "accounts": ["A001", "ACC002"],
        "transactions": [
            {"desc": "Swiggy order by user@okicici", "amount": 450.0},
            {"desc": "Payment with card 4111 2222 3333 4444", "amount": 1200.0},
        ],
    }
    cleaned = redact_payload(data)
    assert cleaned["user"] == "Rahul"
    assert "A001" not in cleaned["accounts"][0]
    assert "user@okicici" not in cleaned["transactions"][0]["desc"]
    assert "@okicici" in cleaned["transactions"][0]["desc"]
    assert "4111 2222" not in cleaned["transactions"][1]["desc"]
    assert cleaned["transactions"][0]["amount"] == 450.0


def test_llm_service_masks_prompts_sync():
    """ask_llm must pass redacted messages to the external client."""
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="Answer"))]
    mock_resp.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    mock_client.chat.completions.create.return_value = mock_resp

    with patch("backend.app.services.llm_service._get_client", return_value=mock_client):
        prompt = "Account A001 made payment to merchant@okaxis with card 4111-2222-3333-1234"
        system = "System rule for account ACC12345"

        ask_llm(prompt=prompt, system_prompt=system)

        calls = mock_client.chat.completions.create.call_args
        messages = calls.kwargs["messages"]

        sys_content = messages[0]["content"]
        user_content = messages[1]["content"]

        assert "ACC12345" not in sys_content
        assert "A001" not in user_content
        assert "merchant@okaxis" not in user_content
        assert "4111-2222-3333" not in user_content
        assert "****-****-****-1234" in user_content


def test_llm_service_masks_prompts_async():
    """ask_llm_async must pass redacted messages to the external async client."""
    import asyncio

    mock_async_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="Async Answer"))]
    mock_resp.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)

    async def mock_create(**kwargs):
        messages = kwargs.get("messages", [])
        assert "A001" not in messages[0]["content"]
        assert "upi_user@okhdfcbank" not in messages[0]["content"]
        return mock_resp

    mock_async_client.chat.completions.create = mock_create

    with patch("backend.app.services.llm_service._get_async_client", return_value=mock_async_client):
        prompt = "User paying via upi_user@okhdfcbank for account A001"
        res = asyncio.run(ask_llm_async(prompt=prompt))
        assert res.content == "Async Answer"
