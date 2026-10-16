"""
Prompt Builder & Versioned Prompt Registry for Personal Finance AI Assistant.

Supports prompt template versioning (Audit Gap H1), rollback, and dynamic evaluation.
Every prompt template adheres to strict currency preservation (₹) and 
deterministic grounding rules.
"""
from dataclasses import dataclass
from typing import Any, Callable

from backend.config import DEFAULT_PROMPT_VERSION


@dataclass(frozen=True)
class PromptTemplate:
    version: str
    description: str
    created_at: str
    builder: Callable[[Any, str | None, list[dict] | None], str]

    def render(
        self,
        financial_result: Any,
        question: str | None = None,
        conversation_history: list[dict] | None = None,
    ) -> str:
        return self.builder(financial_result, question, conversation_history)


def _format_conversation_history(conversation_history: list[dict] | None, max_turns: int = 4) -> str:
    if not conversation_history or not isinstance(conversation_history, list):
        return ""
    formatted_turns = []
    for turn in conversation_history[-max_turns:]:
        role = turn.get("role", "user").capitalize()
        content = turn.get("content", "")
        if content:
            formatted_turns.append(f"{role}: {content}")
    if formatted_turns:
        return "Recent Conversation History (use for context on follow-ups):\n" + "\n".join(formatted_turns) + "\n\n"
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Template v1.0: Baseline Structured Explainer
# ─────────────────────────────────────────────────────────────────────────────
def _build_v1_0(financial_result: Any, question: str | None = None, conversation_history: list[dict] | None = None) -> str:
    q_context = f'User Question: "{question}"\n' if question else ""
    history_context = _format_conversation_history(conversation_history, max_turns=3)

    return f"""You are a helpful personal finance assistant.
{history_context}{q_context}
Explain the following verified financial calculation accurately and concisely:

RULES:
1. Preserve all exact amounts in Indian Rupees (₹). Never convert to dollars or other currencies.
2. Clearly state the financial outcome, safety decision, and supporting numbers.
3. Keep the explanation grounded strictly in the provided data.

Verified Financial Analysis:
{financial_result}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Template v1.1: 4-Section Executive Wealth Advisor (Current Production Standard)
# ─────────────────────────────────────────────────────────────────────────────
def _build_v1_1(financial_result: Any, question: str | None = None, conversation_history: list[dict] | None = None) -> str:
    q_context = f'User Question: "{question}"\n' if question else ""
    history_context = _format_conversation_history(conversation_history, max_turns=4)

    return f"""You are an expert personal financial advisor who communicates with warmth, clarity, intelligence, and modern visual polish.

{history_context}{q_context}Explain the provided financial analysis to the user in an engaging, human, and easily scannable format.

CORE COMMUNICATION RULES:
1. TONE: Warm, direct, encouraging, and human—like a premier wealth advisor. Avoid robotic jargon, formula algebra (never write equations like "Income - Expenses = ₹39,000"), or stiff academic phrasing.
2. CURRENCY: Always preserve the Indian Rupee symbol ₹ exactly. NEVER convert ₹ to $, USD, or any other currency.
3. ACCURACY: Preserve every number and metric computed in the analysis. Do NOT contradict the decision, risk rating, or figures.
4. STRUCTURE: Always organize your response using these 4 sleek visual sections:

🎯 The Quick Take
[1-2 punchy, conversational sentences giving the bottom-line answer immediately]

📊 The Numbers
[Clean bullet points using '•' with exact ₹ amounts and key percentages]

💡 Smart Insights
[2-3 conversational, practical bullet points explaining what these numbers mean for their life and finances, without reciting raw math formulas]

🚀 What You Should Do Next
[2-3 clear, actionable, and encouraging steps tailored to their situation]

5. Formatting: Ensure clean line breaks between sections and punchy bullet points.

Verified Financial Analysis:
{financial_result}
"""


PROMPT_REGISTRY: dict[str, PromptTemplate] = {
    "v1.0": PromptTemplate(
        version="v1.0",
        description="Baseline concise financial explainer without executive sections",
        created_at="2026-09-10",
        builder=_build_v1_0,
    ),
    "v1.1": PromptTemplate(
        version="v1.1",
        description="Executive 4-section advisor with conversational warmth and strict ₹ preservation",
        created_at="2026-10-15",
        builder=_build_v1_1,
    ),
}


def get_prompt_template(version: str | None = None) -> PromptTemplate:
    """Retrieve a versioned prompt template. Defaults to DEFAULT_PROMPT_VERSION."""
    target_version = version or DEFAULT_PROMPT_VERSION
    if target_version not in PROMPT_REGISTRY:
        raise ValueError(
            f"Unknown prompt version '{target_version}'. "
            f"Available versions: {list(PROMPT_REGISTRY.keys())}"
        )
    return PROMPT_REGISTRY[target_version]


def list_prompt_versions() -> list[dict]:
    """List metadata for all registered prompt template versions."""
    return [
        {
            "version": t.version,
            "description": t.description,
            "created_at": t.created_at,
            "is_default": (t.version == DEFAULT_PROMPT_VERSION),
        }
        for t in PROMPT_REGISTRY.values()
    ]


def build_financial_explanation_prompt(
    financial_result: Any,
    question: str | None = None,
    conversation_history: list[dict] | None = None,
    version: str | None = None,
) -> str:
    """
    Build the formatted financial explanation prompt using the registered version.
    Backward-compatible with original 3-argument signature.
    """
    template = get_prompt_template(version=version)
    return template.render(
        financial_result=financial_result,
        question=question,
        conversation_history=conversation_history,
    )


__all__ = [
    "PromptTemplate",
    "PROMPT_REGISTRY",
    "get_prompt_template",
    "list_prompt_versions",
    "build_financial_explanation_prompt",
]
