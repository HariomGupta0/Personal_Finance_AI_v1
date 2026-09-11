from backend.app.services.prompt_builder import build_financial_explanation_prompt
from backend.app.services.llm_service import ask_llm

def generate_explanation(financial_result, question=None):
    prompt = build_financial_explanation_prompt(financial_result, question=question)
    response = ask_llm(prompt)
    return response
