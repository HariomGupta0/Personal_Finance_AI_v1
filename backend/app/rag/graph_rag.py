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
    generate_financial_summary
)
from backend.app.services.response_generator import generate_explanation

class GraphRAG:

    def __init__(self, db=None):
        self.db = db or Neo4jService()

    def retrieve_subgraph(self, user_id, intent, entities=None):
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

    def execute_reasoning(self, intent, context, entities=None):
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
            matching_cat = next((c for c in all_cat_stats["categories"] if c["category"].lower() == target_cat.lower()), None)
            return {
                "requested_category": target_cat,
                "category_spent": matching_cat["amount"] if matching_cat else 0.0,
                "percentage_of_total": matching_cat["percentage"] if matching_cat else 0.0,
                "total_expenses": all_cat_stats["total_expenses"],
                "all_categories": all_cat_stats["categories"]
            }

        elif intent == "DEBT_ANALYSIS":
            return calculate_debt_burden(context)

        elif intent == "FINANCIAL_HEALTH":
            return calculate_comprehensive_health(context)

        elif intent == "FINANCIAL_SUMMARY":
            return generate_financial_summary(context)

        else:
            return generate_financial_summary(context)

    def construct_evidence_payload(self, intent, reasoning_result, context):
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
                {"label": "Recommended 3-Month Emergency Buffer", "value": f"{sym}{ev.get('emergency_requirement', 0):,}", "source": "Emergency Fund Formula"}
            ]

        elif intent == "SAVINGS_ANALYSIS":
            evidence_items = [
                {"label": "Total Monthly Income", "value": f"{sym}{reasoning_result.get('total_income', 0):,}", "source": "Income.amount"},
                {"label": "Total Monthly Expenses", "value": f"{sym}{reasoning_result.get('total_expenses', 0):,}", "source": "Transaction.amount"},
                {"label": "Net Monthly Savings", "value": f"{sym}{reasoning_result.get('savings', 0):,}", "source": "Deterministic Math"},
                {"label": "Savings Rate", "value": f"{reasoning_result.get('savings_rate', 0)}%", "source": "Savings Formula"}
            ]

        elif intent == "EMERGENCY_RUNWAY_ANALYSIS":
            evidence_items = [
                {"label": "Current Liquid Balance", "value": f"{sym}{reasoning_result.get('current_balance', 0):,}", "source": "Account.balance"},
                {"label": "Monthly Expenses", "value": f"{sym}{reasoning_result.get('monthly_expenses', 0):,}", "source": "Transaction.amount"},
                {"label": "Months of Runway", "value": f"{reasoning_result.get('runway_months', 0)} months", "source": "Runway Formula"},
                {"label": "Buffer Health Status", "value": reasoning_result.get("status", "INSUFFICIENT"), "source": "Health Classifier"}
            ]

        elif intent == "EXPENSE_BREAKDOWN":
            evidence_items = [
                {"label": "Total Monthly Expenses", "value": f"{sym}{reasoning_result.get('total_expenses', 0):,}", "source": "Ledger Sum"},
                {"label": "Highest Spending Category", "value": f"{reasoning_result.get('top_category', 'None')} ({sym}{reasoning_result.get('top_amount', 0):,})", "source": "Category Analytics"}
            ]

        elif intent == "DEBT_ANALYSIS":
            evidence_items = [
                {"label": "Total Outstanding Loan Principal", "value": f"{sym}{reasoning_result.get('total_outstanding_debt', 0):,}", "source": "Loan.outstanding"},
                {"label": "Pending Monthly EMI", "value": f"{sym}{reasoning_result.get('monthly_emi', 0):,}", "source": "EMI.amount"},
                {"label": "Debt-to-Income (DTI) Ratio", "value": f"{reasoning_result.get('dti_ratio', 0)}%", "source": "DTI Formula"},
                {"label": "Debt Risk Assessment", "value": reasoning_result.get("assessment", "Healthy"), "source": "Risk Classifier"}
            ]

        elif intent == "FINANCIAL_HEALTH":
            evidence_items = [
                {"label": "Overall Financial Health Score", "value": f"{reasoning_result.get('health_score', 0)} / 100", "source": "Composite Scoring Model"},
                {"label": "Financial Grade", "value": f"Grade {reasoning_result.get('grade', 'B')}", "source": "Grading Engine"},
                {"label": "Savings Rate", "value": f"{reasoning_result.get('savings_rate', 0)}%", "source": "Savings Model"},
                {"label": "Emergency Runway", "value": f"{reasoning_result.get('runway_months', 0)} months", "source": "Runway Model"},
                {"label": "DTI Ratio", "value": f"{reasoning_result.get('dti_ratio', 0)}%", "source": "Debt Model"}
            ]

        return {
            "intent": intent,
            "facts": evidence_items,
            "raw_result": reasoning_result
        }

    def process_query(self, question, user_id="U001"):
        """
        Complete GraphRAG pipeline:
        NLU -> Targeted Subgraph Retrieval -> Deterministic Math -> Grounded Evidence -> LLM Explanation.
        """
        parsed = parse_question(question)
        intent = parsed["intent"]

        if intent == "UNKNOWN":
            return {
                "query": question,
                "intent": "UNKNOWN",
                "decision": None,
                "math_result": None,
                "evidence": [],
                "explanation": "I'm sorry, I couldn't understand that financial question. You can ask about purchase affordability (e.g. 'Can I spend ₹15000 on a phone?'), savings rate, emergency runway, expenses breakdown, or financial health."
            }

        context = self.retrieve_subgraph(user_id, intent, entities=parsed)
        math_result = self.execute_reasoning(intent, context, entities=parsed)
        evidence_payload = self.construct_evidence_payload(intent, math_result, context)
        explanation = generate_explanation(math_result, question=question)

        return {
            "query": question,
            "intent": intent,
            "entities": parsed,
            "math_result": math_result,
            "evidence": evidence_payload["facts"],
            "explanation": explanation
        }
