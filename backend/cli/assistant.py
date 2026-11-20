import sys

# Ensure UTF-8 output encoding on Windows consoles
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from backend.app.database.neo4j_service import Neo4jService
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
from backend.app.nlu.question_parser import parse_question
from backend.app.services.response_generator import generate_explanation


def run_assistant(user_id: str = "U001"):
    db = Neo4jService()
    conversation_history: list[dict] = []
    print("=" * 65)
    print(f" Personal Finance AI Assistant (CLI) — User: {user_id}")
    print(" Multi-turn enabled. Type 'exit' or 'quit' to end session.")
    print("=" * 65)

    try:
        while True:
            try:
                question = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nSession ended.")
                break

            if not question:
                continue

            if question.lower() in ["exit", "quit", "q"]:
                print("Goodbye!")
                break

            # Parse question with conversation history for contextual follow-ups
            parsed = parse_question(question, conversation_history=conversation_history)

            # Check if clarification is required (e.g. missing or ambiguous amount/date)
            if parsed.get("needs_clarification"):
                clarification_msg = parsed.get("clarification_message") or "Could you please clarify your request?"
                print(f"\nAssistant [Clarification Required]:\n{clarification_msg}")
                conversation_history.append({"role": "user", "content": question})
                conversation_history.append({"role": "assistant", "content": clarification_msg})
                continue

            intent = parsed.get("intent")
            response = ""

            # Always recalculate using current authorized financial data from the database
            if intent == "PURCHASE_SAFETY":
                context = db.get_purchase_context(user_id)
                amount = parsed.get("amount")
                if amount is None:
                    response = "Please provide an exact purchase amount to evaluate affordability."
                else:
                    result = check_purchase_safety(context, amount)
                    response = generate_explanation(result)

            elif intent == "SAVINGS_ANALYSIS":
                context = db.get_savings_context(user_id)
                result = calculate_savings_rate(context, reporting_date=parsed.get("reporting_date"))
                response = generate_explanation(result)

            elif intent == "EMERGENCY_FUND_ANALYSIS":
                context = db.get_emergency_fund_context(user_id)
                result = calculate_emergency_fund(context, reporting_date=parsed.get("reporting_date"))
                response = generate_explanation(result)

            elif intent == "EMERGENCY_RUNWAY_ANALYSIS":
                context = db.get_emergency_fund_context(user_id)
                result = calculate_emergency_runway(context)
                response = generate_explanation(result)

            elif intent == "EXPENSE_BREAKDOWN":
                context = db.get_financial_context(user_id)
                result = calculate_category_expenses(context, reporting_date=parsed.get("reporting_date"))
                response = generate_explanation(result)

            elif intent == "CATEGORY_EXPENSE":
                context = db.get_financial_context(user_id)
                target_cat = parsed.get("category", "General")
                all_cat_stats = calculate_category_expenses(context, reporting_date=parsed.get("reporting_date"))
                matching_cat = next((c for c in all_cat_stats["categories"] if c["category"].lower() == target_cat.lower()), None)
                cat_result = {
                    "category": target_cat,
                    "amount": matching_cat["amount"] if matching_cat else 0.0,
                    "percentage": matching_cat["percentage"] if matching_cat else 0.0,
                    "total_expenses": all_cat_stats["total_expenses"],
                }
                response = generate_explanation(cat_result)

            elif intent == "DEBT_ANALYSIS":
                context = db.get_purchase_context(user_id)
                result = calculate_debt_burden(context)
                response = generate_explanation(result)

            elif intent == "FINANCIAL_HEALTH":
                context = db.get_summary_context(user_id)
                result = calculate_comprehensive_health(context)
                response = generate_explanation(result)

            elif intent == "FINANCIAL_SUMMARY":
                context = db.get_summary_context(user_id)
                result = generate_financial_summary(context, reporting_date=parsed.get("reporting_date"))
                response = generate_explanation(result)

            else:
                response = (
                    "I'm sorry, I couldn't understand that financial question. "
                    "You can ask about purchase affordability, savings rate, emergency fund, "
                    "emergency runway, expenses breakdown, debt, or financial health."
                )

            print("\nFinancial Assistant:")
            print(response)

            # Update conversation history (keep last 6 turns)
            conversation_history.append({"role": "user", "content": question})
            conversation_history.append({"role": "assistant", "content": response[:500]})
            conversation_history = conversation_history[-6:]

    finally:
        db.close()


if __name__ == "__main__":
    run_assistant()
