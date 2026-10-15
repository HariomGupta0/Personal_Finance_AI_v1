from backend.app.services.prompt_builder import build_financial_explanation_prompt
from backend.app.services.llm_service import ask_llm


def generate_explanation(financial_result: dict, question: str | None = None) -> str:
    """
    Build a grounded explanation prompt and call the LLM.

    Returns the explanation text (str). Token usage and latency are logged
    inside ask_llm() and should be extracted by the caller from the full
    ask_llm() dict when per-stage metrics are needed.
    """
    prompt = build_financial_explanation_prompt(financial_result, question=question)
    result = ask_llm(prompt)
    return result["content"]
