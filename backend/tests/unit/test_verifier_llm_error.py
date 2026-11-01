"""
Unit tests asserting that when llm_service returns _DEFAULT_FALLBACK_TEXT
after exhausted retries, verification["llm_error"]=True and verified=False.
"""

import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import pytest

from backend.app.rag.graph_rag import GraphRAG
from backend.app.services.llm_service import _DEFAULT_FALLBACK_TEXT, LLMResponse
from backend.app.services.verifier import verify_explanation


MOCK_CONTEXT = {
    "user_id": "U001",
    "accounts": [{"id": "ACC1", "balance": 50000, "bank": "HDFC"}],
    "loans": [],
    "incomes": [{"id": "INC1", "amount": 60000, "source": "Salary"}],
    "transactions": [],
    "goals": [{"id": "EMERGENCY", "name": "Emergency Fund", "target_amount": 100000, "current_amount": 50000}],
}


def test_verify_explanation_flags_default_fallback_as_llm_error():
    """Direct verify_explanation call with _DEFAULT_FALLBACK_TEXT must yield verified=False and llm_error=True."""
    evidence = {
        "facts": ["Your monthly income is ₹60,000", "Total liquid savings: ₹50,000"],
        "amounts": [60000, 50000],
        "decision": "SAFE",
    }
    result = verify_explanation(_DEFAULT_FALLBACK_TEXT, evidence, intent="PURCHASE_SAFETY")
    assert result.verified is False
    assert result.get("llm_error") is True
    assert any(v.get("type") == "LLM_ERROR" for v in result.get("violations", []))


def test_graph_rag_process_query_handles_mocked_llm_failure():
    """GraphRAG.process_query sets verified=False and llm_error=True when LLM returns fallback text."""
    mock_db = MagicMock()
    mock_db.get_purchase_context.return_value = MOCK_CONTEXT

    rag = GraphRAG(db=mock_db)

    fallback_resp = LLMResponse({
        "content": _DEFAULT_FALLBACK_TEXT,
        "tokens_used": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "latency_ms": 150.0,
        "model": "llama-3.3-70b-versatile",
        "is_fallback": True,
        "error": "Groq API error 500",
    })

    with patch("backend.app.rag.graph_rag.ask_llm", return_value=fallback_resp):
        res = rag.process_query("Can I afford a 15000 purchase?", user_id="U001")

    assert res["verified"] is False
    assert res["verification"]["llm_error"] is True
    assert res["llm_error"] is True
    assert res["explanation"] == _DEFAULT_FALLBACK_TEXT
    assert res["tokens"]["total"] == 0


def test_graph_rag_process_query_async_handles_mocked_llm_failure():
    """GraphRAG.process_query_async sets verified=False and llm_error=True when async LLM fails."""
    async def _run():
        mock_db = MagicMock()
        mock_db.get_purchase_context.return_value = MOCK_CONTEXT
        rag = GraphRAG(db=mock_db)

        fallback_resp = LLMResponse({
            "content": _DEFAULT_FALLBACK_TEXT,
            "tokens_used": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "latency_ms": 120.0,
            "model": "llama-3.3-70b-versatile",
            "is_fallback": True,
            "error": "Groq timeout",
        })

        with patch("backend.app.rag.graph_rag.ask_llm_async", new_callable=AsyncMock, return_value=fallback_resp):
            res = await rag.process_query_async("Can I afford a 15000 purchase?", user_id="U001")

        assert res["verified"] is False
        assert res["verification"]["llm_error"] is True
        assert res["llm_error"] is True
        assert res["explanation"] == _DEFAULT_FALLBACK_TEXT

    asyncio.run(_run())


def test_graph_rag_process_query_retry_fails_with_llm_error():
    """When attempt 1 fails verifier but attempt 2 hits an LLM failure, result has verified=False and llm_error=True."""
    mock_db = MagicMock()
    mock_db.get_purchase_context.return_value = MOCK_CONTEXT
    rag = GraphRAG(db=mock_db)

    # Attempt 1: hallucinated amount causing blocking violation
    attempt1_resp = LLMResponse({
        "content": (
            "🎯 **The Quick Take**\nSafe to spend ₹99,999 on shopping.\n\n"
            "📊 **The Numbers**\n• Balance is ₹50,000.\n\n"
            "💡 **Smart Insights**\n• Budget allows it.\n\n"
            "🚀 **What You Should Do Next**\n• Go ahead."
        ),
        "tokens_used": 150,
        "prompt_tokens": 120,
        "completion_tokens": 30,
        "latency_ms": 500.0,
        "model": "llama-3.3-70b-versatile",
        "is_fallback": False,
    })

    # Attempt 2: Groq connection failure returning default fallback
    attempt2_resp = LLMResponse({
        "content": _DEFAULT_FALLBACK_TEXT,
        "tokens_used": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "latency_ms": 100.0,
        "model": "llama-3.3-70b-versatile",
        "is_fallback": True,
        "error": "Groq connection aborted",
    })

    with patch("backend.app.rag.graph_rag.ask_llm", side_effect=[attempt1_resp, attempt2_resp]):
        res = rag.process_query("Can I afford a 15000 purchase?", user_id="U001")

    assert res["verified"] is False
    assert res["verification"]["llm_error"] is True
    assert res["llm_error"] is True
    assert res["attempts"] == 2
    assert res["explanation"] == _DEFAULT_FALLBACK_TEXT
