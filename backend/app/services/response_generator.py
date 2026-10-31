"""
Response Generator for Personal Finance AI Assistant.

Coordinates prompt assembly, deterministic evidence grounding, and LLM explanation.
Maintains backward compatibility for callers expecting plain strings while offering
structured metadata wrappers for modern telemetry.
Enforces the deterministic financial engine as the sole authority for calculations,
actively intercepting contradictory or malformed LLM claims.
"""
import logging
import re
from typing import Any

from backend.app.services.llm_service import ask_llm, ask_llm_async
from backend.app.services.prompt_builder import build_financial_explanation_prompt

logger = logging.getLogger(__name__)


def build_deterministic_fallback(financial_result: dict | Any, error_note: str | None = None) -> str:
    """
    Construct an authoritative four-section explanation directly from deterministic metrics.
    Ensures that even if the LLM fails, is empty, or hallucinates, the user receives
    a beautifully formatted, 100% accurate 4-section report adhering to ₹ rules.
    """
    if not isinstance(financial_result, dict):
        return (
            "🎯 **The Quick Take**\n"
            "Your financial analysis is complete and verified by the deterministic engine.\n\n"
            "📊 **The Numbers**\n"
            "• All figures have been computed by the deterministic Python engine.\n"
            "• Please consult the evidence card for itemized amounts.\n\n"
            "💡 **Smart Insights**\n"
            "• Deterministic calculations serve as the single source of truth.\n"
            "• The LLM acts strictly as an explainer and cannot alter numerical findings.\n\n"
            "🚀 **What You Should Do Next**\n"
            "• Review the verified financial breakdown in the evidence cards below."
        )

    decision = financial_result.get("decision")
    risk_level = financial_result.get("risk_level")
    evidence = financial_result.get("evidence") or financial_result.get("metrics") or {}
    savings_rate = financial_result.get("savings_rate")
    runway_months = financial_result.get("runway_months") or financial_result.get("months_of_runway")

    # 🎯 Section 1: The Quick Take
    if financial_result.get("comparison_verdict"):
        quick_take = financial_result["comparison_verdict"]
    elif financial_result.get("trend_points"):
        t_dir = str(financial_result.get("trend_direction", "STABLE")).lower()
        avg_spend = float(financial_result.get("average_monthly_spend", 0))
        eval_months = financial_result.get("total_months_evaluated", 6)
        quick_take = (
            f"Your spending trend over {eval_months} evaluated months indicates an average monthly spend of "
            f"**₹{avg_spend:,.2f}** with an overall **{t_dir}** trajectory."
        )
    elif decision:
        quick_take = (
            f"This purchase is classified as **{decision}** with a risk level of "
            f"**{risk_level or 'MODERATE'}** based on your current liquid reserves and pending liabilities."
        )
    elif savings_rate is not None:
        quick_take = (
            f"Your current verified savings rate is **{float(savings_rate):.1f}%**, "
            f"calculated directly from your verified income and expenses."
        )
    elif runway_months is not None:
        quick_take = (
            f"Your current emergency runway is **{float(runway_months):.1f} months**, "
            f"representing the time you can comfortably sustain baseline living expenses."
        )
    else:
        quick_take = "Your financial health metrics have been verified deterministically by the Python engine."

    # 📊 Section 2: The Numbers
    num_lines = []
    if financial_result.get("period_a") and financial_result.get("period_b"):
        p_a = financial_result["period_a"]
        p_b = financial_result["period_b"]
        num_lines.append(f"• Baseline Spend ({p_a.get('name')}): ₹{float(p_a.get('total_spent', 0)):,.2f} ({p_a.get('transaction_count', 0)} transactions)")
        num_lines.append(f"• Comparison Spend ({p_b.get('name')}): ₹{float(p_b.get('total_spent', 0)):,.2f} ({p_b.get('transaction_count', 0)} transactions)")
        abs_ch = float(financial_result.get("absolute_change", 0))
        sign = "+" if abs_ch > 0 else ""
        num_lines.append(f"• Net Absolute Difference: {sign}₹{abs_ch:,.2f}")
        num_lines.append(f"• Percentage Change: {financial_result.get('percentage_change_display', 'N/A')}")
        if financial_result.get("category_variances"):
            top_var = financial_result["category_variances"][0]
            v_sign = "+" if top_var.get("absolute_difference", 0) > 0 else ""
            num_lines.append(f"• Largest Category Shift: {top_var.get('category')} ({v_sign}₹{top_var.get('absolute_difference', 0):,.2f})")
    elif financial_result.get("trend_points"):
        num_lines.append(f"• Average Monthly Expenditure: ₹{float(financial_result.get('average_monthly_spend', 0)):,.2f}")
        num_lines.append(f"• Verified Coverage: {financial_result.get('available_months_count', 0)} of {financial_result.get('total_months_evaluated', 0)} months")
        for pt in financial_result.get("trend_points", [])[-4:]:
            if pt.get("status") == "DATA_UNAVAILABLE":
                num_lines.append(f"• {pt.get('month_name')}: Data Unavailable")
            else:
                num_lines.append(f"• {pt.get('month_name')}: ₹{float(pt.get('total_spent', 0)):,.2f} ({pt.get('transaction_count', 0)} txns)")
    else:
        if "current_balance" in evidence:
            num_lines.append(f"• Current Balance: ₹{float(evidence['current_balance']):,.0f}")
        if "purchase_amount" in evidence:
            num_lines.append(f"• Purchase Amount: ₹{float(evidence['purchase_amount']):,.0f}")
        if "pending_emi" in evidence:
            num_lines.append(f"• Pending EMIs: ₹{float(evidence['pending_emi']):,.0f}")
        if "emergency_requirement" in evidence:
            num_lines.append(f"• Emergency Reserve Needed: ₹{float(evidence['emergency_requirement']):,.0f}")
        if "balance_after_purchase" in evidence:
            num_lines.append(f"• Balance After Purchase: ₹{float(evidence['balance_after_purchase']):,.0f}")
        if savings_rate is not None and "savings_rate" not in evidence:
            num_lines.append(f"• Savings Rate: {float(savings_rate):.1f}%")
        if runway_months is not None and "runway_months" not in evidence:
            num_lines.append(f"• Emergency Runway: {float(runway_months):.1f} months")

    if not num_lines:
        num_lines.append("• Verified amounts are recorded in the accompanying evidence card.")

    numbers_sec = "\n".join(num_lines)

    # 💡 Section 3: Smart Insights & 🚀 Section 4: What You Should Do Next
    if financial_result.get("period_a") and financial_result.get("period_b"):
        insights_list = []
        if financial_result.get("category_variances"):
            for v in financial_result["category_variances"][:2]:
                insights_list.append(f"• {v.get('mathematical_contribution_note')}")
        if financial_result.get("caveats"):
            for cav in financial_result["caveats"]:
                insights_list.append(f"• Caveat: {cav}")
        if not insights_list:
            insights_list.append("• Period spending has been verified deterministically by the Python engine.")
        insights = "\n".join(insights_list)

        action = (
            "• Review the itemized category variance breakdown in the evidence cards below.\n"
            "• Focus spending control on the categories contributing the largest increases."
        )
    elif financial_result.get("trend_points"):
        insights_list = []
        for cav in financial_result.get("caveats", []):
            insights_list.append(f"• Caveat: {cav}")
        insights_list.append("• Missing months are explicitly differentiated from confirmed zero expenditure.")
        insights = "\n".join(insights_list)
        action = (
            "• Maintain steady recurring expenses to stabilize monthly savings.\n"
            "• Import statement records for any unavailable months to ensure complete trend accuracy."
        )
    elif decision == "NOT_SAFE":
        insights = (
            "• Making this expenditure would reduce your balance below your essential emergency reserve threshold.\n"
            "• Upcoming loan EMIs and fixed commitments require liquidity preservation."
        )
        action = (
            "• Postpone this non-essential purchase until your emergency buffer is fully funded.\n"
            "• Consider saving incrementally over several months to avoid high financial strain."
        )
    elif decision == "SAFE":
        insights = (
            "• Your liquid reserves comfortably cover this amount while preserving your full emergency buffer.\n"
            "• Upcoming EMIs and fixed obligations will remain completely protected."
        )
        action = (
            "• You can safely proceed with this purchase without endangering monthly obligations.\n"
            "• Continue maintaining regular contributions to your long-term savings goals."
        )
    else:
        insights = (
            "• All figures are sourced strictly from the deterministic engine to prevent arithmetic hallucination.\n"
            "• Financial decisions should prioritize emergency liquidity and high-interest debt clearance."
        )
        action = (
            "• Examine the detailed breakdown in the evidence cards below.\n"
            "• Maintain steady discipline on non-essential categories."
        )

    disclaimer = f"\n\n*(Note: {error_note})*" if error_note else ""

    return (
        f"🎯 **The Quick Take**\n{quick_take}\n\n"
        f"📊 **The Numbers**\n{numbers_sec}\n\n"
        f"💡 **Smart Insights**\n{insights}\n\n"
        f"🚀 **What You Should Do Next**\n{action}"
        f"{disclaimer}"
    )


def verify_explanation_consistency(
    explanation_text: str,
    financial_result: dict | Any,
) -> tuple[bool, str | None]:
    """
    Verify that the LLM explanation does not contradict authoritative deterministic conclusions.
    Returns (is_valid, optional_error_reason).
    """
    if not explanation_text or not explanation_text.strip():
        return False, "LLM returned empty or whitespace explanation"

    if not isinstance(financial_result, dict):
        return True, None

    text_lower = explanation_text.lower()
    decision = financial_result.get("decision")
    risk_level = financial_result.get("risk_level")

    # Contradiction check: NOT_SAFE vs claims of being completely safe
    if decision == "NOT_SAFE":
        contradiction_patterns = [
            r"\bdecision\s*(?:is|:)?\s*safe\b",
            r"\bpurchase is safe\b",
            r"\bcompletely safe to purchase\b",
            r"\brisk\s*(?:is|:)?\s*low\b",
        ]
        for pat in contradiction_patterns:
            match = re.search(pat, text_lower)
            if match:
                start = max(0, match.start() - 20)
                prefix = text_lower[start:match.start()]
                if "not" not in prefix and "n't" not in prefix and "never" not in prefix:
                    return (
                        False,
                        "LLM contradicted deterministic decision: claimed SAFE/LOW risk when decision is NOT_SAFE",
                    )

    elif decision == "SAFE":
        contradiction_patterns = [
            r"\bdecision\s*(?:is|:)?\s*not safe\b",
            r"\bpurchase is not safe\b",
            r"\brisk\s*(?:is|:)?\s*high\b",
            r"\brisk\s*(?:is|:)?\s*very high\b",
        ]
        for pat in contradiction_patterns:
            if re.search(pat, text_lower):
                return (
                    False,
                    "LLM contradicted deterministic decision: claimed NOT_SAFE/HIGH risk when decision is SAFE",
                )

    if risk_level in ("HIGH", "VERY_HIGH"):
        if re.search(r"\blow risk\b", text_lower) and not re.search(r"\bnot\s+low risk\b", text_lower):
            return (
                False,
                f"LLM contradicted deterministic risk level: claimed LOW risk when risk is {risk_level}",
            )

    return True, None


def generate_explanation(
    financial_result: dict | Any,
    question: str | None = None,
    prompt_version: str | None = None,
) -> str:
    """
    Build a grounded explanation prompt and call the LLM.

    Returns the explanation text (str). Maintains strict backward compatibility
    for all existing CLI and API callers while validating that the LLM does not
    contradict the deterministic engine.
    """
    prompt = build_financial_explanation_prompt(
        financial_result, question=question, version=prompt_version
    )
    result = ask_llm(prompt)
    content = str(result.get("content", ""))

    is_valid, reason = verify_explanation_consistency(content, financial_result)
    if not is_valid:
        logger.warning("generate_explanation detected inconsistent LLM response: %s", reason)
        return build_deterministic_fallback(financial_result, error_note=reason)

    return content


def generate_explanation_with_metadata(
    financial_result: dict | Any,
    question: str | None = None,
    conversation_history: list[dict] | None = None,
    prompt_version: str | None = None,
) -> dict[str, Any]:
    """
    Generate an explanation with complete internal telemetry and telemetry metadata.

    The deterministic financial calculation remains the authoritative source of truth.
    The LLM response is strictly an explanatory projection and never overrides
    the underlying decision, amounts, or risk ratings.
    """
    prompt = build_financial_explanation_prompt(
        financial_result,
        question=question,
        conversation_history=conversation_history,
        version=prompt_version,
    )
    llm_resp = ask_llm(prompt)
    content = str(llm_resp.get("content", ""))

    is_valid, reason = verify_explanation_consistency(content, financial_result)
    is_fallback = llm_resp.get("is_fallback", False) or (not is_valid)
    error = llm_resp.get("error") or reason

    if not is_valid:
        logger.warning(
            "generate_explanation_with_metadata detected inconsistent LLM response: %s", reason
        )
        explanation = build_deterministic_fallback(financial_result, error_note=reason)
    else:
        explanation = content

    decision = financial_result.get("decision") if isinstance(financial_result, dict) else None
    risk_level = financial_result.get("risk_level") if isinstance(financial_result, dict) else None

    return {
        "explanation": explanation,
        "math_result": financial_result,
        "decision": decision,
        "risk_level": risk_level,
        "is_fallback": is_fallback,
        "latency_ms": llm_resp.get("latency_ms", 0.0),
        "tokens_used": llm_resp.get("tokens_used", 0),
        "prompt_tokens": llm_resp.get("prompt_tokens", 0),
        "completion_tokens": llm_resp.get("completion_tokens", 0),
        "model": llm_resp.get("model", ""),
        "error": error,
    }


async def generate_explanation_async(
    financial_result: dict | Any,
    question: str | None = None,
    conversation_history: list[dict] | None = None,
    prompt_version: str | None = None,
) -> dict[str, Any]:
    """
    Asynchronous non-blocking variant of generate_explanation_with_metadata.
    """
    prompt = build_financial_explanation_prompt(
        financial_result,
        question=question,
        conversation_history=conversation_history,
        version=prompt_version,
    )
    llm_resp = await ask_llm_async(prompt)
    content = str(llm_resp.get("content", ""))

    is_valid, reason = verify_explanation_consistency(content, financial_result)
    is_fallback = llm_resp.get("is_fallback", False) or (not is_valid)
    error = llm_resp.get("error") or reason

    if not is_valid:
        logger.warning(
            "generate_explanation_async detected inconsistent LLM response: %s", reason
        )
        explanation = build_deterministic_fallback(financial_result, error_note=reason)
    else:
        explanation = content

    decision = financial_result.get("decision") if isinstance(financial_result, dict) else None
    risk_level = financial_result.get("risk_level") if isinstance(financial_result, dict) else None

    return {
        "explanation": explanation,
        "math_result": financial_result,
        "decision": decision,
        "risk_level": risk_level,
        "is_fallback": is_fallback,
        "latency_ms": llm_resp.get("latency_ms", 0.0),
        "tokens_used": llm_resp.get("tokens_used", 0),
        "prompt_tokens": llm_resp.get("prompt_tokens", 0),
        "completion_tokens": llm_resp.get("completion_tokens", 0),
        "model": llm_resp.get("model", ""),
        "error": error,
    }


__all__ = [
    "generate_explanation",
    "generate_explanation_with_metadata",
    "generate_explanation_async",
    "build_deterministic_fallback",
    "verify_explanation_consistency",
]


