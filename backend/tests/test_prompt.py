from backend.app.services.prompt_builder import build_financial_explanation_prompt

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

prompt = build_financial_explanation_prompt(financial_result)
print(prompt)
