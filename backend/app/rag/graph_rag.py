import logging
import time

from backend.app.database.neo4j_service import Neo4jService
from backend.app.nlu.question_parser import parse_question
from backend.app.engine.financial_engine import (
    check_purchase_safety,
    calculate_savings_rate,
    calculate_emergency_fund,
    calculate_emergency_runway,
    calculate_category_expenses,
    calculate_debt_burden,
    calculate_comprehensive_health,
    generate_financial_summary,
)
from backend.app.services.prompt_builder import build_financial_explanation_prompt
from backend.app.services.llm_service import ask_llm

logger = logging.getLogger(__name__)


class GraphRAG:

    def __init__(self, db=None):
        self.db = db or Neo4jService()

    def retrieve_subgraph(self, user_id: str, intent: str, entities: dict | None = None) -> dict:
        """
        Targeted retrieval of the exact subgraphs needed for a given intent.
        Avoids dumping the entire database.
        """
        entities = entities or {}

        if intent == "PURCHASE_SAFETY":
            return self.db.get_purchase_context(user_id)

        elif intent == "SAVINGS_ANALYSIS":
            return self.db.get_savings_context(user_id)

        elif intent in ["EMERGENCY_FUND_ANALYSIS", "EMERGENCY_RUNWAY_ANALYSIS"]:
            return self.db.get_emergency_fund_context(user_id)

        elif intent in ["EXPENSE_BREAKDOWN", "CATEGORY_EXPENSE"]:
            return self.db.get_financial_context(user_id)

        elif intent == "DEBT_ANALYSIS":
            return self.db.get_purchase_context(user_id)

        elif intent in ["FINANCIAL_HEALTH", "FINANCIAL_SUMMARY"]:
            return self.db.get_summary_context(user_id)

        else:
            return self.db.get_financial_context(user_id)

    def execute_reasoning(self, intent: str, context: dict, entities: dict | None = None) -> dict:
        """
        Executes deterministic mathematical reasoning over the retrieved subgraph.
        """
        entities = entities or {}

        if intent == "PURCHASE_SAFETY":
            amount = entities.get("amount") or 0.0
            return check_purchase_safety(context, amount)

        elif intent == "SAVINGS_ANALYSIS":
            return calculate_savings_rate(context)

        elif intent == "EMERGENCY_FUND_ANALYSIS":
            return calculate_emergency_fund(context)

        elif intent == "EMERGENCY_RUNWAY_ANALYSIS":
            return calculate_emergency_runway(context)

        elif intent == "EXPENSE_BREAKDOWN":
            return calculate_category_expenses(context)

        elif intent == "CATEGORY_EXPENSE":
            target_cat = entities.get("category", "General")
            all_cat_stats = calculate_category_expenses(context)
            matching_cat = next(
                (c for c in all_cat_stats["categories"] if c["category"].lower() == target_cat.lower()),
                None,
            )
            return {
                "requested_category": target_cat,
                "category_spent": matching_cat["amount"] if matching_cat else 0.0,
                "percentage_of_total": matching_cat["percentage"] if matching_cat else 0.0,
                "total_expenses": all_cat_stats["total_expenses"],
                "all_categories": all_cat_stats["categories"],
            }

        elif intent == "DEBT_ANALYSIS":
            return calculate_debt_burden(context)

        elif intent == "FINANCIAL_HEALTH":
            return calculate_comprehensive_health(context)

        elif intent == "FINANCIAL_SUMMARY":
            return generate_financial_summary(context)

        else:
            return generate_financial_summary(context)

    def construct_evidence_payload(self, intent: str, reasoning_result: dict, context: dict) -> dict:
        """
        Builds a verifiable evidence structure linking facts, calculations, and recommendations.
        """
        sym = "₹"
        evidence_items = []

        if intent == "PURCHASE_SAFETY":
            ev = reasoning_result.get("evidence", {})
            evidence_items = [
                {"label": "Current Account Balance", "value": f"{sym}{ev.get('current_balance', 0):,}", "source": "Account.balance"},
                {"label": "Pending EMI Obligations", "value": f"{sym}{ev.get('pending_emi', 0):,}", "source": "EMI.amount"},
                {"label": "Purchase Cost", "value": f"{sym}{ev.get('purchase_amount', 0):,}", "source": "User Query"},
                {"label": "Post-Purchase Remaining Balance", "value": f"{sym}{ev.get('balance_after_purchase', 0):,}", "source": "Deterministic Math"},
                {"label": "Recommended 3-Month Emergency Buffer", "value": f"{sym}{ev.get('emergency_requirement', 0):,}", "source": "Emergency Fund Formula"},
            ]

        elif intent == "SAVINGS_ANALYSIS":
            evidence_items = [
                {"label": "Total Monthly Income", "value": f"{sym}{reasoning_result.get('total_income', 0):,}", "source": "Income.amount"},
                {"label": "Total Monthly Expenses", "value": f"{sym}{reasoning_result.get('total_expenses', 0):,}", "source": "Transaction.amount"},
                {"label": "Net Monthly Savings", "value": f"{sym}{reasoning_result.get('savings', 0):,}", "source": "Deterministic Math"},
                {"label": "Savings Rate", "value": f"{reasoning_result.get('savings_rate', 0)}%", "source": "Savings Formula"},
            ]

        elif intent == "EMERGENCY_RUNWAY_ANALYSIS":
            evidence_items = [
                {"label": "Current Liquid Balance", "value": f"{sym}{reasoning_result.get('current_balance', 0):,}", "source": "Account.balance"},
                {"label": "Monthly Expenses", "value": f"{sym}{reasoning_result.get('monthly_expenses', 0):,}", "source": "Transaction.amount"},
                {"label": "Months of Runway", "value": f"{reasoning_result.get('runway_months', 0)} months", "source": "Runway Formula"},
                {"label": "Buffer Health Status", "value": reasoning_result.get("status", "INSUFFICIENT"), "source": "Health Classifier"},
            ]

        elif intent == "EXPENSE_BREAKDOWN":
            evidence_items = [
                {"label": "Total Monthly Expenses", "value": f"{sym}{reasoning_result.get('total_expenses', 0):,}", "source": "Ledger Sum"},
                {"label": "Highest Spending Category", "value": f"{reasoning_result.get('top_category', 'None')} ({sym}{reasoning_result.get('top_amount', 0):,})", "source": "Category Analytics"},
            ]

        elif intent == "DEBT_ANALYSIS":
            evidence_items = [
                {"label": "Total Outstanding Loan Principal", "value": f"{sym}{reasoning_result.get('total_outstanding_debt', 0):,}", "source": "Loan.outstanding"},
                {"label": "Pending Monthly EMI", "value": f"{sym}{reasoning_result.get('monthly_emi', 0):,}", "source": "EMI.amount"},
                {"label": "Debt-to-Income (DTI) Ratio", "value": f"{reasoning_result.get('dti_ratio', 0)}%", "source": "DTI Formula"},
                {"label": "Debt Risk Assessment", "value": reasoning_result.get("assessment", "Healthy"), "source": "Risk Classifier"},
            ]

        elif intent == "FINANCIAL_HEALTH":
            evidence_items = [
                {"label": "Overall Financial Health Score", "value": f"{reasoning_result.get('health_score', 0)} / 100", "source": "Composite Scoring Model"},
                {"label": "Financial Grade", "value": f"Grade {reasoning_result.get('grade', 'B')}", "source": "Grading Engine"},
                {"label": "Savings Rate", "value": f"{reasoning_result.get('savings_rate', 0)}%", "source": "Savings Model"},
                {"label": "Emergency Runway", "value": f"{reasoning_result.get('runway_months', 0)} months", "source": "Runway Model"},
                {"label": "DTI Ratio", "value": f"{reasoning_result.get('dti_ratio', 0)}%", "source": "Debt Model"},
            ]

        return {
            "intent": intent,
            "facts": evidence_items,
            "raw_result": reasoning_result,
        }

    def process_query(self, question: str, user_id: str = "U001", conversation_history: list[dict] | None = None) -> dict:
        """
        Complete GraphRAG pipeline:
        NLU → Targeted Subgraph Retrieval → Deterministic Math → Grounded Evidence → LLM Explanation.

        Returns a response dict that includes:
          - explanation      : LLM-generated natural language explanation
          - intent           : Classified intent string
          - math_result      : Raw deterministic calculation result
          - evidence         : List of evidence cards (label/value/source)
          - latency_breakdown: Per-stage latency in milliseconds
          - tokens           : LLM token usage (prompt / completion / total)
        """
        pipeline_start = time.perf_counter()

        # ── Stage 1: NLU ─────────────────────────────────────────────────────
        nlu_t0 = time.perf_counter()
        parsed = parse_question(question)
        intent = parsed["intent"]
        nlu_ms = (time.perf_counter() - nlu_t0) * 1000

        logger.info("pipeline_start | user=%s | intent=%s | question=%r", user_id, intent, question[:80])

        if intent == "UNKNOWN":
            total_ms = (time.perf_counter() - pipeline_start) * 1000
            logger.info("pipeline_done | user=%s | intent=UNKNOWN | total_ms=%.0f", user_id, total_ms)
            return {
                "query": question,
                "intent": "UNKNOWN",
                "decision": None,
                "math_result": None,
                "evidence": [],
                "explanation": (
                    "I'm sorry, I couldn't understand that financial question. "
                    "You can ask about purchase affordability (e.g. 'Can I spend ₹15000 on a phone?'), "
                    "savings rate, emergency runway, expenses breakdown, or financial health."
                ),
                "latency_breakdown": {"nlu_ms": round(nlu_ms, 1), "graph_ms": 0, "engine_ms": 0, "llm_ms": 0, "total_ms": round(total_ms, 1)},
                "tokens": {"prompt": 0, "completion": 0, "total": 0},
            }

        # ── Stage 2: Graph retrieval ──────────────────────────────────────────
        graph_t0 = time.perf_counter()
        context = self.retrieve_subgraph(user_id, intent, entities=parsed)
        graph_ms = (time.perf_counter() - graph_t0) * 1000
        logger.info("graph_retrieved | user=%s | intent=%s | graph_ms=%.0f", user_id, intent, graph_ms)

        # ── Stage 3: Deterministic engine ────────────────────────────────────
        engine_t0 = time.perf_counter()
        math_result = self.execute_reasoning(intent, context, entities=parsed)
        engine_ms = (time.perf_counter() - engine_t0) * 1000

        evidence_payload = self.construct_evidence_payload(intent, math_result, context)

        # ── Stage 4: LLM explanation ──────────────────────────────────────────
        llm_t0 = time.perf_counter()
        prompt = build_financial_explanation_prompt(math_result, question=question, conversation_history=conversation_history)
        llm_result = ask_llm(prompt)
        llm_ms = (time.perf_counter() - llm_t0) * 1000

        total_ms = (time.perf_counter() - pipeline_start) * 1000
        logger.info(
            "pipeline_done | user=%s | intent=%s | nlu_ms=%.0f | graph_ms=%.0f | engine_ms=%.0f | llm_ms=%.0f | total_ms=%.0f",
            user_id, intent, nlu_ms, graph_ms, engine_ms, llm_ms, total_ms,
        )

        return {
            "query": question,
            "intent": intent,
            "entities": parsed,
            "math_result": math_result,
            "evidence": evidence_payload["facts"],
            "explanation": llm_result["content"],
            "latency_breakdown": {
                "nlu_ms": round(nlu_ms, 1),
                "graph_ms": round(graph_ms, 1),
                "engine_ms": round(engine_ms, 1),
                "llm_ms": round(llm_ms, 1),
                "total_ms": round(total_ms, 1),
            },
            "tokens": {
                "prompt": llm_result["prompt_tokens"],
                "completion": llm_result["completion_tokens"],
                "total": llm_result["tokens_used"],
            },
        }
