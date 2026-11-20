"""
Unit tests validating intent routing and phrasing robustness across core analytical intents.
Ensures that phrasing variations (including "How long can I survive on my savings?")
correctly route to their intended OperationType/intent without requiring live LLM fallback.
"""

import pytest
from backend.app.nlu.question_parser import parse_question


INTENT_PHRASINGS = {
    "PURCHASE_SAFETY": [
        "Can I afford to buy an iPhone for 80,000?",
        "Should I buy a laptop for ₹45,000?",
        "Is it safe to spend 15000 on shoes?",
        "Can I purchase a car for ₹5,00,000?",
        "Am I able to buy furniture worth 30000?",
        "Can I afford a 25000 vacation?",
    ],
    "CATEGORY_EXPENSE": [
        "How much did I spend on groceries?",
        "What were my expenses on food?",
        "How much did I spend on travel?",
        "Show my spending on entertainment",
        "Tell me about my expenses on utilities",
        "Cost of healthcare this month",
    ],
    "EXPENSE_BREAKDOWN": [
        "Where did I spend the most money?",
        "Show my expense breakdown",
        "Show my spending breakdown",
        "Where is my money going?",
        "Break down my monthly expenses",
        "Give me a breakdown of all my expenses",
    ],
    "SAVINGS_ANALYSIS": [
        "What is my savings rate?",
        "How much am I saving each month?",
        "How much do I save?",
        "What are my total savings?",
        "Check my savings rate for this month",
        "Show my savings rate",
    ],
    "EMERGENCY_RUNWAY_ANALYSIS": [
        "How long can I survive on my savings?",
        "What is my emergency runway?",
        "How many months can I survive without income?",
        "How long will my money last?",
        "What is my survival buffer in months?",
        "How many months of runway do I have?",
    ],
    "EMERGENCY_FUND_ANALYSIS": [
        "How is my emergency fund?",
        "Do I have enough emergency reserve?",
        "What is my emergency target?",
        "Check my emergency money requirement",
        "Is my emergency fund adequate?",
        "What is my emergency reserve shortfall?",
    ],
    "DEBT_ANALYSIS": [
        "What is my current debt?",
        "How much loan EMI do I have?",
        "What is my debt-to-income ratio?",
        "Show my outstanding liabilities",
        "What are my monthly debt obligations?",
        "Check my DTI ratio",
    ],
    "FINANCIAL_HEALTH": [
        "What is my financial health score?",
        "How is my overall financial health?",
        "Give me a financial health check",
        "What is my financial grade?",
        "Evaluate my financial health",
        "Check my financial score",
    ],
    "FINANCIAL_SUMMARY": [
        "Give me a summary of my finances",
        "What is my financial overview?",
        "How does my financial situation look?",
        "Summarize my overall finances",
        "Give me a financial summary",
        "Overview of my finances",
    ],
}


@pytest.mark.parametrize("expected_intent,queries", INTENT_PHRASINGS.items())
def test_six_phrasings_per_intent(expected_intent, queries):
    assert len(queries) >= 6, f"Intent {expected_intent} must have at least 6 test phrasings"
    for query in queries:
        result = parse_question(query, use_llm_fallback=False)
        actual_intent = result.get("intent")
        assert actual_intent == expected_intent, (
            f"Query '{query}' was expected to route to '{expected_intent}', "
            f"but routed to '{actual_intent}'"
        )


def test_survival_on_savings_specifically():
    """Specific regression test for 'How long can I survive on my savings?'"""
    res = parse_question("How long can I survive on my savings?", use_llm_fallback=False)
    assert res.get("intent") == "EMERGENCY_RUNWAY_ANALYSIS"

