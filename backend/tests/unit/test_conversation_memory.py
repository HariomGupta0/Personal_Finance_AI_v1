"""
Unit tests for multi-turn conversation memory and prompt formatting.
Zero live database or network dependencies.
"""
from backend.app.services.prompt_builder import build_financial_explanation_prompt
from backend.app.api.assistant import QueryRequest, ConversationTurn


def test_build_prompt_with_history():
    history = [
        {"role": "user", "content": "How much should my emergency fund be?"},
        {"role": "assistant", "content": "Your recommended emergency fund is ₹63,000."},
    ]
    math_result = {"status": "HEALTHY", "runway_months": 3.5}
    prompt = build_financial_explanation_prompt(
        math_result,
        question="Can I reach that in 6 months?",
        conversation_history=history
    )

    assert "Recent Conversation History" in prompt
    assert "User: How much should my emergency fund be?" in prompt
    assert "Assistant: Your recommended emergency fund is ₹63,000." in prompt
    assert "Can I reach that in 6 months?" in prompt
    assert "₹" in prompt


def test_build_prompt_without_history():
    math_result = {"savings_rate": 65.0}
    prompt = build_financial_explanation_prompt(math_result, question="What is my savings rate?")

    assert "Recent Conversation History" not in prompt
    assert "What is my savings rate?" in prompt


def test_query_request_model_with_history():
    req = QueryRequest(
        question="Can I afford it?",
        history=[
            ConversationTurn(role="user", content="What is my runway?"),
            ConversationTurn(role="assistant", content="You have 2.1 months."),
        ]
    )
    assert req.question == "Can I afford it?"
    assert len(req.history) == 2
    assert req.history[0].role == "user"
    assert req.history[1].content == "You have 2.1 months."


def test_query_request_model_default_empty_history():
    req = QueryRequest(question="Give me a summary")
    assert req.history == []
