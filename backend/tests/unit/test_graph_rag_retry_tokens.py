"""
Tests proving retry-call token usage is properly accumulated in GraphRAG.
"""

from unittest.mock import MagicMock, patch
import pytest

from backend.app.rag.graph_rag import GraphRAG


def test_retry_tokens_accumulate_both_attempts():
    rag = GraphRAG()

    mock_nlu_result = {
        "intent": "PURCHASE_SAFETY",
        "entities": {"amount": 5000.0, "category": "General"},
    }

    mock_reasoning = {
        "decision": "SAFE",
        "risk_level": "LOW",
        "purchase_amount": 5000.0,
        "current_balance": 50000.0,
    }

    # Attempt 1 has blocking violations (e.g. ₹99,999 not in evidence)
    attempt1_content = """
    ### The Quick Take
    You can buy it with ₹99,999.
    ### The Numbers
    • Balance: ₹50,000
    ### Smart Insights
    Looking good.
    ### What You Should Do Next
    Save more.
    """
    attempt1_resp = {
        "content": attempt1_content,
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "tokens_used": 150,
        "model": "openai/gpt-oss-120b",
    }

    # Attempt 2 is verified
    attempt2_content = """
    ### The Quick Take
    A purchase of ₹5,000 is safe.
    ### The Numbers
    • Balance: ₹50,000
    ### Smart Insights
    Looking good.
    ### What You Should Do Next
    Save more.
    """
    attempt2_resp = {
        "content": attempt2_content,
        "prompt_tokens": 120,
        "completion_tokens": 60,
        "tokens_used": 180,
        "model": "openai/gpt-oss-120b",
    }

    with patch("backend.app.rag.graph_rag.parse_question", return_value=mock_nlu_result), \
         patch.object(rag, "retrieve_subgraph", return_value={}), \
         patch.object(rag, "execute_reasoning", return_value=mock_reasoning), \
         patch("backend.app.rag.graph_rag.ask_llm", side_effect=[attempt1_resp, attempt2_resp]):

        res = rag.process_query(question="Can I spend ₹5,000?", user_id="U001")

        assert res["attempts"] == 2
        assert res["fallback_used"] is False
        assert res["tokens"]["prompt"] == 100 + 120
        assert res["tokens"]["completion"] == 50 + 60
        assert res["tokens"]["total"] == 150 + 180
        assert res.get("model") == "openai/gpt-oss-120b"

