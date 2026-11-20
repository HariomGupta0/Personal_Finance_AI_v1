"""
Unit tests for Prompt Versioning & Registry (Audit Gap H1).
"""
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.app.services.prompt_builder import (
    PROMPT_REGISTRY,
    build_financial_explanation_prompt,
    get_prompt_template,
    list_prompt_versions,
)

client = TestClient(app)

MOCK_RESULT = {
    "decision": "SAFE",
    "risk_level": "LOW",
    "metrics": {
        "current_balance": 45000,
        "purchase_amount": 3000,
        "balance_after_purchase": 42000,
    },
}


def test_list_prompt_versions():
    versions = list_prompt_versions()
    assert len(versions) >= 2
    ver_names = [v["version"] for v in versions]
    assert "v1.0" in ver_names
    assert "v1.1" in ver_names

    default_versions = [v for v in versions if v["is_default"]]
    assert len(default_versions) == 1
    assert default_versions[0]["version"] == "v1.1"


def test_get_prompt_template_valid():
    t_v10 = get_prompt_template("v1.0")
    assert t_v10.version == "v1.0"
    assert "Baseline" in t_v10.description

    t_v11 = get_prompt_template("v1.1")
    assert t_v11.version == "v1.1"
    assert "Executive" in t_v11.description


def test_get_prompt_template_invalid():
    with pytest.raises(ValueError) as exc:
        get_prompt_template("v99.0")
    assert "Unknown prompt version 'v99.0'" in str(exc.value)


def test_prompt_v1_0_structure():
    prompt = build_financial_explanation_prompt(
        financial_result=MOCK_RESULT,
        question="Can I spend ₹3000?",
        version="v1.0",
    )
    assert "₹" in prompt
    assert "Can I spend ₹3000?" in prompt
    assert "Verified Financial Analysis:" in prompt
    assert "45000" in prompt


def test_prompt_v1_1_executive_structure():
    prompt = build_financial_explanation_prompt(
        financial_result=MOCK_RESULT,
        question="Can I spend ₹3000?",
        version="v1.1",
    )
    # Check 4 mandatory executive sections
    assert "🎯 The Quick Take" in prompt
    assert "📊 The Numbers" in prompt
    assert "💡 Smart Insights" in prompt
    assert "🚀 What You Should Do Next" in prompt

    # Check strict currency preservation rule
    assert "Indian Rupee symbol ₹ exactly" in prompt
    assert "Can I spend ₹3000?" in prompt


def test_prompt_with_conversation_history():
    history = [
        {"role": "user", "content": "What is my current savings rate?"},
        {"role": "assistant", "content": "Your current savings rate is 65%."},
    ]
    prompt = build_financial_explanation_prompt(
        financial_result=MOCK_RESULT,
        question="What about next month?",
        conversation_history=history,
        version="v1.1",
    )
    assert "Recent Conversation History" in prompt
    assert "User: What is my current savings rate?" in prompt
    assert "Assistant: Your current savings rate is 65%." in prompt


def test_api_prompt_versions_endpoint():
    res = client.get("/api/assistant/prompt-versions")
    assert res.status_code == 200
    data = res.json()
    assert "versions" in data
    assert len(data["versions"]) >= 2
