"""
Unit tests for non-blocking Async LLM client and GraphRAG async pipeline (Audit Gap C6).
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.services.llm_service import ask_llm_async, ask_llm_sync
from backend.app.rag.graph_rag import GraphRAG
from backend.tests.unit.test_financial_engine import MOCK_CONTEXT


def test_ask_llm_async_success():
    async def _test():
        mock_choice = MagicMock()
        mock_choice.message.content = "Here is your verified financial analysis."
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 150
        mock_usage.completion_tokens = 45
        mock_usage.total_tokens = 195

        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]
        mock_resp.usage = mock_usage

        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_resp

        with patch("backend.app.services.llm_service._get_async_client", return_value=mock_client):
            result = await ask_llm_async("Can I afford ₹10,000?")

            assert result["content"] == "Here is your verified financial analysis."
            assert result["tokens_used"] == 195
            assert result["prompt_tokens"] == 150
            assert result["completion_tokens"] == 45
            assert result["latency_ms"] >= 0.0
            assert result["error"] is None

    asyncio.run(_test())


def test_ask_llm_async_fallback_on_failure():
    async def _test():
        mock_client = AsyncMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("Groq rate limit exceeded")

        with patch("backend.app.services.llm_service._get_async_client", return_value=mock_client):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await ask_llm_async("Will this fail?", retries=1)

                assert "Financial Analysis Complete" in result["content"]
                assert result["tokens_used"] == 0
                assert "Groq rate limit exceeded" in result["error"]

    asyncio.run(_test())


def test_ask_llm_sync_wrapper():
    mock_choice = MagicMock()
    mock_choice.message.content = "Sync response text"
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 50
    mock_usage.completion_tokens = 20
    mock_usage.total_tokens = 70

    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    mock_resp.usage = mock_usage

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_resp

    with patch("backend.app.services.llm_service._get_client", return_value=mock_client):
        result = ask_llm_sync("Test sync prompt")
        assert result["content"] == "Sync response text"
        assert result["tokens_used"] == 70


def test_graph_rag_process_query_async():
    async def _test():
        mock_db = MagicMock()
        mock_db.get_purchase_context.return_value = MOCK_CONTEXT

        rag = GraphRAG(db=mock_db)

        with patch("backend.app.rag.graph_rag.ask_llm_async", new_callable=AsyncMock) as mock_async_llm:
            mock_async_llm.return_value = {
                "content": "Async purchase affordability verified.",
                "prompt_tokens": 120,
                "completion_tokens": 30,
                "tokens_used": 150,
            }

            result = await rag.process_query_async("Can I spend ₹5000 on shopping?", user_id="U001")

            assert result["intent"] == "PURCHASE_SAFETY"
            assert result["explanation"] == "Async purchase affordability verified."
            assert result["latency_breakdown"]["total_ms"] >= 0
            assert result["tokens"]["total"] == 150

    asyncio.run(_test())

