import sys

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
from backend.app.services.prompt_builder import build_financial_explanation_prompt

def verify_all():
    print("==================================================")
    print(" PERSONAL FINANCE AI - ENVIRONMENT VERIFICATION")
    print("==================================================")
    
    # 1. Database Connection & Context Fetch
    db = Neo4jService()
    print(f"\n[1] Connected to Neo4j database: '{db.database}'")
    context = db.get_financial_context("U001")
    assert context is not None, "Failed to fetch financial context for U001"
    assert context["user"] == "Rahul", f"Expected user Rahul, got {context['user']}"
    assert len(context["accounts"]) == 1, f"Expected 1 account, got {len(context['accounts'])}"
    assert context["accounts"][0]["balance"] == 45000, f"Expected balance 45000, got {context['accounts'][0]['balance']}"
    assert len(context["transactions"]) == 4, f"Expected 4 transactions, got {len(context['transactions'])}"
    assert len(context["incomes"]) == 1, f"Expected 1 income, got {len(context['incomes'])}"
    assert len(context["loans"]) == 1, f"Expected 1 loan, got {len(context['loans'])}"
    assert len(context["goals"]) == 1, f"Expected 1 goal, got {len(context['goals'])}"
    print("  -> Full financial context verified successfully.")

    # 2. Specialized Context Methods
    purchase_ctx = db.get_purchase_context("U001")
    assert purchase_ctx is not None, "Purchase context is None"
    savings_ctx = db.get_savings_context("U001")
    assert savings_ctx is not None, "Savings context is None"
    emergency_ctx = db.get_emergency_fund_context("U001")
    assert emergency_ctx is not None, "Emergency fund context is None"
    summary_ctx = db.get_summary_context("U001")
    assert summary_ctx is not None, "Summary context is None"
    print("  -> All specialized context methods (purchase, savings, emergency, summary) verified.")

    # 3. Financial Engine Verification
    print("\n[2] Testing Financial Engine Calculations:")
    
    # Savings Rate Test
    savings = calculate_savings_rate(savings_ctx)
    print(f"  - Savings: Income=₹{savings['total_income']}, Expenses=₹{savings['total_expenses']}, Savings=₹{savings['savings']}, Rate={savings['savings_rate']}%")
    assert savings['total_income'] == 60000, f"Expected income 60000, got {savings['total_income']}"
    assert savings['total_expenses'] == 21000, f"Expected expenses 21000, got {savings['total_expenses']}"
    assert savings['savings'] == 39000, f"Expected savings 39000, got {savings['savings']}"
    assert savings['savings_rate'] == 65.0, f"Expected savings rate 65.0, got {savings['savings_rate']}"

    # Emergency Fund Test
    emergency = calculate_emergency_fund(emergency_ctx)
    print(f"  - Emergency Fund: Expenses=₹{emergency['monthly_expenses']}, Recommended=₹{emergency['recommended_fund']}, Current=₹{emergency['current_fund']}, Shortfall=₹{emergency['shortfall']}")
    assert emergency['monthly_expenses'] == 21000, f"Expected monthly expenses 21000, got {emergency['monthly_expenses']}"
    assert emergency['recommended_fund'] == 63000, f"Expected recommended fund 63000, got {emergency['recommended_fund']}"
    assert emergency['current_fund'] == 30000, f"Expected current fund 30000, got {emergency['current_fund']}"
    assert emergency['shortfall'] == 33000, f"Expected shortfall 33000, got {emergency['shortfall']}"

    # Purchase Safety Test (₹15,000)
    safety_15k = check_purchase_safety(purchase_ctx, 15000)
    print(f"  - Purchase ₹15,000: Decision={safety_15k['decision']}, Risk={safety_15k['risk_level']}")
    assert safety_15k['decision'] == "NOT_SAFE", f"Expected NOT_SAFE, got {safety_15k['decision']}"
    assert safety_15k['risk_level'] == "HIGH", f"Expected HIGH risk, got {safety_15k['risk_level']}"
    assert safety_15k['evidence']['balance_after_purchase'] == 20000

    # Purchase Safety Test (₹5,000)
    safety_5k = check_purchase_safety(purchase_ctx, 5000)
    print(f"  - Purchase ₹5,000: Decision={safety_5k['decision']}, Risk={safety_5k['risk_level']}")
    assert safety_5k['decision'] == "NOT_SAFE"
    assert safety_5k['risk_level'] == "MEDIUM"

    # Purchase Safety Test (₹40,000)
    safety_40k = check_purchase_safety(purchase_ctx, 40000)
    print(f"  - Purchase ₹40,000: Decision={safety_40k['decision']}, Risk={safety_40k['risk_level']}")
    assert safety_40k['decision'] == "NOT_SAFE"
    assert safety_40k['risk_level'] == "VERY_HIGH"

    # Summary Generation
    summary = generate_financial_summary(context)
    print(f"  - Summary: {summary}")
    assert summary['income'] == 60000
    assert summary['expenses'] == 21000
    assert summary['emergency_fund_shortfall'] == 33000

    # 4. Question Parser Verification
    print("\n[3] Testing Question Parser:")
    test_queries = [
        ("Can I spend ₹15,000 on a phone?", "PURCHASE_SAFETY", 15000),
        ("Can I buy a laptop for 50000?", "PURCHASE_SAFETY", 50000),
        ("How much am I saving?", "SAVINGS_ANALYSIS", None),
        ("What is my savings rate?", "SAVINGS_ANALYSIS", None),
        ("How much should my emergency fund be?", "EMERGENCY_FUND_ANALYSIS", None),
        ("How much emergency reserve do I need?", "EMERGENCY_FUND_ANALYSIS", None),
        ("Tell me something about my finances", "FINANCIAL_SUMMARY", None),
        ("How is my financial health?", "FINANCIAL_HEALTH", None),
        ("What is my financial situation?", "FINANCIAL_SUMMARY", None),
        ("Give me a financial summary", "FINANCIAL_SUMMARY", None),
        ("How are my overall finances?", "FINANCIAL_SUMMARY", None)
    ]
    for q, expected_intent, expected_amt in test_queries:
        res = parse_question(q)
        assert res["intent"] == expected_intent, f"Query '{q}' parsed as {res['intent']}, expected {expected_intent}"
        assert res["amount"] == expected_amt, f"Query '{q}' amount parsed as {res['amount']}, expected {expected_amt}"
        print(f"  - '{q}' -> {res['intent']} (Amount: {res['amount']}) [OK]")

    # 5. Prompt Builder
    print("\n[4] Testing Prompt Builder:")
    prompt = build_financial_explanation_prompt(safety_15k)
    assert "₹" in prompt
    assert "NOT_SAFE" in prompt
    assert "HIGH" in prompt
    print("  -> Prompt builder produced valid structured prompt with strict ₹ rules.")

    db.close()
    print("\n==================================================")
    print(" ALL BASELINE VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    verify_all()
