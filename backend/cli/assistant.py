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
    generate_financial_summary
)
from backend.app.nlu.question_parser import parse_question
from backend.app.services.response_generator import generate_explanation

def run_assistant():
    db = Neo4jService()
    try:
        question = input("Ask your financial question: ").strip()
        if not question:
            print("No question entered.")
            return

        parsed = parse_question(question)
        print("\nParsed Question:")
        print(parsed)

        if parsed["intent"] == "PURCHASE_SAFETY":
            context = db.get_purchase_context("U001")
            amount = parsed["amount"]
            if amount is None:
                print("Please provide a purchase amount.")
            else:
                result = check_purchase_safety(context, amount)
                response = generate_explanation(result)
                print("\nFinancial Assistant:")
                print(response)

        elif parsed["intent"] == "SAVINGS_ANALYSIS":
            context = db.get_savings_context("U001")
            result = calculate_savings_rate(context)
            response = generate_explanation(result)
            print("\nFinancial Assistant:")
            print(response)

        elif parsed["intent"] == "EMERGENCY_FUND_ANALYSIS":
            context = db.get_emergency_fund_context("U001")
            result = calculate_emergency_fund(context)
            response = generate_explanation(result)
            print("\nFinancial Assistant:")
            print(response)

        elif parsed["intent"] == "FINANCIAL_SUMMARY":
            context = db.get_summary_context("U001")
            result = generate_financial_summary(context)
            response = generate_explanation(result)
            print("\nFinancial Assistant:")
            print(response)

        else:
            print("I don't understand this question yet.")
    finally:
        db.close()

if __name__ == "__main__":
    run_assistant()
