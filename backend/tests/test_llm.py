from backend.app.services.llm_service import ask_llm

financial_result = {
    "decision": "NOT_SAFE",
    "risk_level": "HIGH",
    "evidence": {
        "current_balance": 45000,
        "pending_emi": 10000,
        "purchase_amount": 15000,
        "emergency_requirement": 63000,
        "balance_after_purchase": 20000
    }
}

prompt = f"""
You are an explainable personal finance assistant.

Explain the financial analysis to the user in simple language.

STRICT RULES:
1. Preserve every number exactly as provided.
2. Preserve the Indian Rupee symbol ₹ exactly.
3. Never convert ₹ to $, USD, or any other currency.
4. Never invent or modify financial information.
5. Do not perform additional calculations.
6. Do not contradict the decision or risk level.
7. Clearly explain how the provided evidence supports the decision.
8. Keep the explanation concise.

Financial analysis:
{financial_result}
"""

response = ask_llm(prompt)
print("\nLLM Explanation:")
print(response)
