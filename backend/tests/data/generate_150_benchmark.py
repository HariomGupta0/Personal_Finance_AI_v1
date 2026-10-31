"""
Script to generate the standardized 150-query evaluation benchmark dataset.
Categorized into 7 distinct evaluation dimensions:
1. Purchase Safety & Affordability (25)
2. Relational Reasoning & Multi-hop (25)
3. Savings Rate & Emergency Runway (25)
4. Arithmetic & Spending Aggregations (25)
5. Category Breakdown & Merchant Inquiries (25)
6. Currency & Unit Preservation (15)
7. Missing Data & Boundary / Abstention (10)
"""

import json
from pathlib import Path

DATASET = [
    # =========================================================================
    # 1. Purchase Safety & Affordability (25 queries)
    # =========================================================================
    {
        "id": "Q001",
        "category": "Purchase_Safety",
        "question": "Can I spend ₹15,000 on a phone?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 15000.0,
        "eval_check": "decision == 'NOT_SAFE'",
        "critical_facts": ["45000", "10000", "15000", "20000", "63000"]
    },
    {
        "id": "Q002",
        "category": "Purchase_Safety",
        "question": "Can I buy a laptop for 50000?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 50000.0,
        "eval_check": "decision == 'NOT_SAFE'",
        "critical_facts": ["50000", "NOT_SAFE"]
    },
    {
        "id": "Q003",
        "category": "Purchase_Safety",
        "question": "Is it safe for me to buy shoes worth ₹2,500?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 2500.0,
        "eval_check": "decision in ('SAFE', 'NOT_SAFE')",
        "critical_facts": ["2500"]
    },
    {
        "id": "Q004",
        "category": "Purchase_Safety",
        "question": "Can I afford a ₹5,000 weekend dinner?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 5000.0,
        "eval_check": "decision in ('SAFE', 'NOT_SAFE')",
        "critical_facts": ["5000"]
    },
    {
        "id": "Q005",
        "category": "Purchase_Safety",
        "question": "Can I purchase a smartwatch for ₹8,000 right now?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 8000.0,
        "eval_check": "decision == 'NOT_SAFE'",
        "critical_facts": ["8000"]
    },
    {
        "id": "Q006",
        "category": "Purchase_Safety",
        "question": "Would buying an air conditioner for ₹35,000 hurt my finances?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 35000.0,
        "eval_check": "decision == 'NOT_SAFE'",
        "critical_facts": ["35000", "NOT_SAFE"]
    },
    {
        "id": "Q007",
        "category": "Purchase_Safety",
        "question": "Can I afford an international vacation flight of ₹45,000?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 45000.0,
        "eval_check": "decision == 'NOT_SAFE'",
        "critical_facts": ["45000", "NOT_SAFE"]
    },
    {
        "id": "Q008",
        "category": "Purchase_Safety",
        "question": "Is it safe to spend ₹1,200 on books today?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 1200.0,
        "eval_check": "decision in ('SAFE', 'NOT_SAFE')",
        "critical_facts": ["1200"]
    },
    {
        "id": "Q009",
        "category": "Purchase_Safety",
        "question": "Can I splurge ₹20,000 on home decor?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 20000.0,
        "eval_check": "decision == 'NOT_SAFE'",
        "critical_facts": ["20000", "NOT_SAFE"]
    },
    {
        "id": "Q010",
        "category": "Purchase_Safety",
        "question": "Can I buy a new bicycle for ₹12,000?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 12000.0,
        "eval_check": "decision == 'NOT_SAFE'",
        "critical_facts": ["12000"]
    },
    {
        "id": "Q011",
        "category": "Purchase_Safety",
        "question": "Is buying a ₹1,00,000 two-wheeler safe with my current balance?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 100000.0,
        "eval_check": "decision == 'NOT_SAFE'",
        "critical_facts": ["100000", "NOT_SAFE"]
    },
    {
        "id": "Q012",
        "category": "Purchase_Safety",
        "question": "Can I spend ₹3,000 on concert tickets?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 3000.0,
        "eval_check": "decision in ('SAFE', 'NOT_SAFE')",
        "critical_facts": ["3000"]
    },
    {
        "id": "Q013",
        "category": "Purchase_Safety",
        "question": "Can I pay ₹18,000 for an online certified course?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 18000.0,
        "eval_check": "decision == 'NOT_SAFE'",
        "critical_facts": ["18000"]
    },
    {
        "id": "Q014",
        "category": "Purchase_Safety",
        "question": "Is it financially responsible to buy a ₹25,000 tablet?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 25000.0,
        "eval_check": "decision == 'NOT_SAFE'",
        "critical_facts": ["25000", "NOT_SAFE"]
    },
    {
        "id": "Q015",
        "category": "Purchase_Safety",
        "question": "Can I afford to spend ₹600 on coffee and snacks?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 600.0,
        "eval_check": "decision in ('SAFE', 'NOT_SAFE')",
        "critical_facts": ["600"]
    },
    {
        "id": "Q016",
        "category": "Purchase_Safety",
        "question": "Can I buy a sofa set for ₹22,000?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 22000.0,
        "eval_check": "decision == 'NOT_SAFE'",
        "critical_facts": ["22000"]
    },
    {
        "id": "Q017",
        "category": "Purchase_Safety",
        "question": "Would a ₹4,500 gym membership fit into my budget?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 4500.0,
        "eval_check": "decision in ('SAFE', 'NOT_SAFE')",
        "critical_facts": ["4500"]
    },
    {
        "id": "Q018",
        "category": "Purchase_Safety",
        "question": "Can I afford ₹30,000 for holiday shopping?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 30000.0,
        "eval_check": "decision == 'NOT_SAFE'",
        "critical_facts": ["30000", "NOT_SAFE"]
    },
    {
        "id": "Q019",
        "category": "Purchase_Safety",
        "question": "Can I buy gold jewellery for ₹60,000?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 60000.0,
        "eval_check": "decision == 'NOT_SAFE'",
        "critical_facts": ["60000", "NOT_SAFE"]
    },
    {
        "id": "Q020",
        "category": "Purchase_Safety",
        "question": "Is it safe to spend ₹9,000 on car servicing?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 9000.0,
        "eval_check": "decision == 'NOT_SAFE'",
        "critical_facts": ["9000"]
    },
    {
        "id": "Q021",
        "category": "Purchase_Safety",
        "question": "Can I buy an office chair for ₹7,500?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 7500.0,
        "eval_check": "decision in ('SAFE', 'NOT_SAFE')",
        "critical_facts": ["7500"]
    },
    {
        "id": "Q022",
        "category": "Purchase_Safety",
        "question": "Can I spend ₹40,000 on a gaming console and games?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 40000.0,
        "eval_check": "decision == 'NOT_SAFE'",
        "critical_facts": ["40000", "NOT_SAFE"]
    },
    {
        "id": "Q023",
        "category": "Purchase_Safety",
        "question": "Can I afford a ₹1,500 restaurant dinner with friends?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 1500.0,
        "eval_check": "decision in ('SAFE', 'NOT_SAFE')",
        "critical_facts": ["1500"]
    },
    {
        "id": "Q024",
        "category": "Purchase_Safety",
        "question": "Can I purchase winter clothing for ₹6,500?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 6500.0,
        "eval_check": "decision in ('SAFE', 'NOT_SAFE')",
        "critical_facts": ["6500"]
    },
    {
        "id": "Q025",
        "category": "Purchase_Safety",
        "question": "Can I afford a refrigerator costing ₹28,000?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 28000.0,
        "eval_check": "decision == 'NOT_SAFE'",
        "critical_facts": ["28000", "NOT_SAFE"]
    },

    # =========================================================================
    # 2. Relational Multi-Hop Reasoning (Loans, EMIs, Debts, Accounts) (25 queries)
    # =========================================================================
    {
        "id": "Q026",
        "category": "Relational_Reasoning",
        "question": "How much debt do I have?",
        "expected_intent": "DEBT_ANALYSIS",
        "eval_check": "abs(float(m.get('total_outstanding_debt', 0)) - 150000.0) < 1.0",
        "critical_facts": ["150000", "10000"]
    },
    {
        "id": "Q027",
        "category": "Relational_Reasoning",
        "question": "What is my total outstanding loan balance?",
        "expected_intent": "DEBT_ANALYSIS",
        "eval_check": "abs(float(m.get('total_outstanding_debt', 0)) - 150000.0) < 1.0",
        "critical_facts": ["150000"]
    },
    {
        "id": "Q028",
        "category": "Relational_Reasoning",
        "question": "What is my monthly EMI obligation?",
        "expected_intent": "DEBT_ANALYSIS",
        "eval_check": "abs(float(m.get('monthly_emi', 0)) - 10000.0) < 1.0",
        "critical_facts": ["10000"]
    },
    {
        "id": "Q029",
        "category": "Relational_Reasoning",
        "question": "What is my debt to income ratio?",
        "expected_intent": "DEBT_ANALYSIS",
        "eval_check": "abs(float(m.get('debt_to_income_ratio', 0)) - 16.67) < 1.0",
        "critical_facts": ["16.67", "60000"]
    },
    {
        "id": "Q030",
        "category": "Relational_Reasoning",
        "question": "Do I have any pending loan payments?",
        "expected_intent": "DEBT_ANALYSIS",
        "eval_check": "float(m.get('monthly_emi', 0)) > 0",
        "critical_facts": ["10000", "PENDING"]
    },
    {
        "id": "Q031",
        "category": "Relational_Reasoning",
        "question": "What is my bank account balance after deducting pending EMIs?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 0.0,
        "eval_check": "abs(float(m.get('effective_balance', 0)) - 35000.0) < 1.0 or '35000' in str(m)",
        "critical_facts": ["45000", "10000", "35000"]
    },
    {
        "id": "Q032",
        "category": "Relational_Reasoning",
        "question": "How many active loans are linked to my profile?",
        "expected_intent": "DEBT_ANALYSIS",
        "eval_check": "'loan' in str(m).lower()",
        "critical_facts": ["Loan", "150000"]
    },
    {
        "id": "Q033",
        "category": "Relational_Reasoning",
        "question": "Can my current balance cover my upcoming loan EMI?",
        "expected_intent": "DEBT_ANALYSIS",
        "eval_check": "float(m.get('total_outstanding_debt', 0)) > 0",
        "critical_facts": ["45000", "10000"]
    },
    {
        "id": "Q034",
        "category": "Relational_Reasoning",
        "question": "What percentage of my monthly income goes into loan repayments?",
        "expected_intent": "DEBT_ANALYSIS",
        "eval_check": "abs(float(m.get('debt_to_income_ratio', 0)) - 16.67) < 1.0",
        "critical_facts": ["16.67", "10000", "60000"]
    },
    {
        "id": "Q035",
        "category": "Relational_Reasoning",
        "question": "How much principal is remaining on my loan?",
        "expected_intent": "DEBT_ANALYSIS",
        "eval_check": "abs(float(m.get('total_outstanding_debt', 0)) - 150000.0) < 1.0",
        "critical_facts": ["150000"]
    },
    {
        "id": "Q036",
        "category": "Relational_Reasoning",
        "question": "Which account pays my loan EMI?",
        "expected_intent": "DEBT_ANALYSIS",
        "eval_check": "'account' in str(m).lower()",
        "critical_facts": ["Account", "EMI"]
    },
    {
        "id": "Q037",
        "category": "Relational_Reasoning",
        "question": "Are my monthly debt obligations within a healthy limit?",
        "expected_intent": "DEBT_ANALYSIS",
        "eval_check": "float(m.get('debt_to_income_ratio', 0)) < 36.0",
        "critical_facts": ["16.67", "Healthy"]
    },
    {
        "id": "Q038",
        "category": "Relational_Reasoning",
        "question": "Show my debt overview including loans and pending dues",
        "expected_intent": "DEBT_ANALYSIS",
        "eval_check": "abs(float(m.get('total_outstanding_debt', 0)) - 150000.0) < 1.0",
        "critical_facts": ["150000", "10000"]
    },
    {
        "id": "Q039",
        "category": "Relational_Reasoning",
        "question": "If I double my EMI to ₹20,000, what will my DTI be?",
        "expected_intent": "DEBT_ANALYSIS",
        "eval_check": "'debt' in str(m).lower()",
        "critical_facts": ["60000", "DTI"]
    },
    {
        "id": "Q040",
        "category": "Relational_Reasoning",
        "question": "How much of my savings is eaten up by my loan interest and EMIs?",
        "expected_intent": "DEBT_ANALYSIS",
        "eval_check": "float(m.get('monthly_emi', 0)) == 10000.0",
        "critical_facts": ["10000", "39000"]
    },
    {
        "id": "Q041",
        "category": "Relational_Reasoning",
        "question": "Does my emergency fund cover my loan EMI during job loss?",
        "expected_intent": "EMERGENCY_FUND_ANALYSIS",
        "eval_check": "float(m.get('recommended_fund', 0)) > 0",
        "critical_facts": ["63000", "10000"]
    },
    {
        "id": "Q042",
        "category": "Relational_Reasoning",
        "question": "What is my total liability compared to my total assets?",
        "expected_intent": "DEBT_ANALYSIS",
        "eval_check": "float(m.get('total_outstanding_debt', 0)) == 150000.0",
        "critical_facts": ["150000", "45000"]
    },
    {
        "id": "Q043",
        "category": "Relational_Reasoning",
        "question": "What is my net worth after subtracting my loans from bank accounts?",
        "expected_intent": "FINANCIAL_HEALTH",
        "eval_check": "'health' in str(m).lower() or 'score' in str(m).lower()",
        "critical_facts": ["45000", "150000"]
    },
    {
        "id": "Q044",
        "category": "Relational_Reasoning",
        "question": "When is my next EMI payment due?",
        "expected_intent": "DEBT_ANALYSIS",
        "eval_check": "float(m.get('monthly_emi', 0)) > 0",
        "critical_facts": ["10000"]
    },
    {
        "id": "Q045",
        "category": "Relational_Reasoning",
        "question": "What is the status of my loan repayments?",
        "expected_intent": "DEBT_ANALYSIS",
        "eval_check": "float(m.get('total_outstanding_debt', 0)) > 0",
        "critical_facts": ["150000", "10000"]
    },
    {
        "id": "Q046",
        "category": "Relational_Reasoning",
        "question": "Can I prepay ₹50,000 of my loan right now safely?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 50000.0,
        "eval_check": "decision == 'NOT_SAFE'",
        "critical_facts": ["50000", "NOT_SAFE"]
    },
    {
        "id": "Q047",
        "category": "Relational_Reasoning",
        "question": "How much liquid cash is unencumbered by pending loan payments?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 0.0,
        "eval_check": "'35000' in str(m) or float(m.get('effective_balance', 0)) == 35000.0",
        "critical_facts": ["35000", "45000", "10000"]
    },
    {
        "id": "Q048",
        "category": "Relational_Reasoning",
        "question": "Show my debt service coverage from monthly income",
        "expected_intent": "DEBT_ANALYSIS",
        "eval_check": "abs(float(m.get('debt_to_income_ratio', 0)) - 16.67) < 1.0",
        "critical_facts": ["16.67"]
    },
    {
        "id": "Q049",
        "category": "Relational_Reasoning",
        "question": "What are my total fixed liabilities including loans?",
        "expected_intent": "DEBT_ANALYSIS",
        "eval_check": "float(m.get('monthly_emi', 0)) == 10000.0",
        "critical_facts": ["10000"]
    },
    {
        "id": "Q050",
        "category": "Relational_Reasoning",
        "question": "Summarize my debt profile and risk score",
        "expected_intent": "DEBT_ANALYSIS",
        "eval_check": "float(m.get('total_outstanding_debt', 0)) == 150000.0",
        "critical_facts": ["150000", "16.67"]
    },

    # =========================================================================
    # 3. Savings Rate & Emergency Runway (25 queries)
    # =========================================================================
    {
        "id": "Q051",
        "category": "Savings_Runway",
        "question": "What is my savings rate?",
        "expected_intent": "SAVINGS_ANALYSIS",
        "eval_check": "abs(float(m.get('savings_rate', 0)) - 65.0) < 1.0",
        "critical_facts": ["65.0", "60000", "21000", "39000"]
    },
    {
        "id": "Q052",
        "category": "Savings_Runway",
        "question": "What percentage of my income did I save this month?",
        "expected_intent": "SAVINGS_ANALYSIS",
        "eval_check": "abs(float(m.get('savings_rate', 0)) - 65.0) < 1.0",
        "critical_facts": ["65.0"]
    },
    {
        "id": "Q053",
        "category": "Savings_Runway",
        "question": "How much money am I saving every month?",
        "expected_intent": "SAVINGS_ANALYSIS",
        "eval_check": "abs(float(m.get('monthly_savings', 0)) - 39000.0) < 1.0",
        "critical_facts": ["39000"]
    },
    {
        "id": "Q054",
        "category": "Savings_Runway",
        "question": "How much emergency fund do I need?",
        "expected_intent": "EMERGENCY_FUND_ANALYSIS",
        "eval_check": "abs(float(m.get('recommended_fund', 0)) - 63000.0) < 1.0",
        "critical_facts": ["63000", "21000"]
    },
    {
        "id": "Q055",
        "category": "Savings_Runway",
        "question": "What is my 3-month statutory emergency requirement?",
        "expected_intent": "EMERGENCY_FUND_ANALYSIS",
        "eval_check": "abs(float(m.get('recommended_fund', 0)) - 63000.0) < 1.0",
        "critical_facts": ["63000"]
    },
    {
        "id": "Q056",
        "category": "Savings_Runway",
        "question": "What is my emergency fund shortfall?",
        "expected_intent": "EMERGENCY_FUND_ANALYSIS",
        "eval_check": "abs(float(m.get('shortfall', 0)) - 33000.0) < 1.0",
        "critical_facts": ["33000", "30000", "63000"]
    },
    {
        "id": "Q057",
        "category": "Savings_Runway",
        "question": "How many months can I survive on my runway?",
        "expected_intent": "EMERGENCY_RUNWAY_ANALYSIS",
        "eval_check": "abs(float(m.get('runway_months', 0)) - 2.14) < 0.2",
        "critical_facts": ["2.14", "45000", "21000"]
    },
    {
        "id": "Q058",
        "category": "Savings_Runway",
        "question": "If I lose my job today, how many months can my bank balance last?",
        "expected_intent": "EMERGENCY_RUNWAY_ANALYSIS",
        "eval_check": "abs(float(m.get('runway_months', 0)) - 2.14) < 0.2",
        "critical_facts": ["2.14", "45000"]
    },
    {
        "id": "Q059",
        "category": "Savings_Runway",
        "question": "What is my financial emergency runway?",
        "expected_intent": "EMERGENCY_RUNWAY_ANALYSIS",
        "eval_check": "abs(float(m.get('runway_months', 0)) - 2.14) < 0.2",
        "critical_facts": ["2.14"]
    },
    {
        "id": "Q060",
        "category": "Savings_Runway",
        "question": "How close am I to reaching my emergency fund goal?",
        "expected_intent": "EMERGENCY_FUND_ANALYSIS",
        "eval_check": "float(m.get('current_reserve', 0)) == 30000.0",
        "critical_facts": ["30000", "63000", "33000"]
    },
    {
        "id": "Q061",
        "category": "Savings_Runway",
        "question": "Is my savings rate considered healthy?",
        "expected_intent": "SAVINGS_ANALYSIS",
        "eval_check": "float(m.get('savings_rate', 0)) >= 20.0",
        "critical_facts": ["65.0", "Healthy"]
    },
    {
        "id": "Q062",
        "category": "Savings_Runway",
        "question": "How many more months of savings do I need to complete my emergency buffer?",
        "expected_intent": "EMERGENCY_FUND_ANALYSIS",
        "eval_check": "float(m.get('shortfall', 0)) == 33000.0",
        "critical_facts": ["33000", "39000"]
    },
    {
        "id": "Q063",
        "category": "Savings_Runway",
        "question": "What is my monthly cash surplus after all expenses?",
        "expected_intent": "SAVINGS_ANALYSIS",
        "eval_check": "abs(float(m.get('monthly_savings', 0)) - 39000.0) < 1.0",
        "critical_facts": ["39000"]
    },
    {
        "id": "Q064",
        "category": "Savings_Runway",
        "question": "How long will my money last without any new income?",
        "expected_intent": "EMERGENCY_RUNWAY_ANALYSIS",
        "eval_check": "abs(float(m.get('runway_months', 0)) - 2.14) < 0.2",
        "critical_facts": ["2.14"]
    },
    {
        "id": "Q065",
        "category": "Savings_Runway",
        "question": "What is my 6-month emergency reserve target?",
        "expected_intent": "EMERGENCY_FUND_ANALYSIS",
        "eval_check": "float(m.get('recommended_fund', 0)) > 0",
        "critical_facts": ["21000"]
    },
    {
        "id": "Q066",
        "category": "Savings_Runway",
        "question": "Calculate my savings ratio from income and expenses",
        "expected_intent": "SAVINGS_ANALYSIS",
        "eval_check": "abs(float(m.get('savings_rate', 0)) - 65.0) < 1.0",
        "critical_facts": ["65.0"]
    },
    {
        "id": "Q067",
        "category": "Savings_Runway",
        "question": "Do I have at least 3 months of survival buffer saved up?",
        "expected_intent": "EMERGENCY_FUND_ANALYSIS",
        "eval_check": "float(m.get('shortfall', 0)) > 0",
        "critical_facts": ["30000", "63000", "No"]
    },
    {
        "id": "Q068",
        "category": "Savings_Runway",
        "question": "What is the gap between my current emergency savings and recommended target?",
        "expected_intent": "EMERGENCY_FUND_ANALYSIS",
        "eval_check": "abs(float(m.get('shortfall', 0)) - 33000.0) < 1.0",
        "critical_facts": ["33000"]
    },
    {
        "id": "Q069",
        "category": "Savings_Runway",
        "question": "If I cut expenses by 10%, how much will my runway increase?",
        "expected_intent": "EMERGENCY_RUNWAY_ANALYSIS",
        "eval_check": "float(m.get('runway_months', 0)) > 2.0",
        "critical_facts": ["2.14", "45000"]
    },
    {
        "id": "Q070",
        "category": "Savings_Runway",
        "question": "How much should I allocate each month to finish my emergency buffer?",
        "expected_intent": "EMERGENCY_FUND_ANALYSIS",
        "eval_check": "float(m.get('shortfall', 0)) == 33000.0",
        "critical_facts": ["33000"]
    },
    {
        "id": "Q071",
        "category": "Savings_Runway",
        "question": "Is my emergency runway above the danger zone of 1 month?",
        "expected_intent": "EMERGENCY_RUNWAY_ANALYSIS",
        "eval_check": "float(m.get('runway_months', 0)) > 1.0",
        "critical_facts": ["2.14", "Yes"]
    },
    {
        "id": "Q072",
        "category": "Savings_Runway",
        "question": "What portion of my earnings remains unspent?",
        "expected_intent": "SAVINGS_ANALYSIS",
        "eval_check": "abs(float(m.get('savings_rate', 0)) - 65.0) < 1.0",
        "critical_facts": ["65.0", "39000"]
    },
    {
        "id": "Q073",
        "category": "Savings_Runway",
        "question": "Evaluate my emergency resilience",
        "expected_intent": "EMERGENCY_FUND_ANALYSIS",
        "eval_check": "float(m.get('recommended_fund', 0)) == 63000.0",
        "critical_facts": ["63000", "30000"]
    },
    {
        "id": "Q074",
        "category": "Savings_Runway",
        "question": "Show my complete savings analysis",
        "expected_intent": "SAVINGS_ANALYSIS",
        "eval_check": "abs(float(m.get('savings_rate', 0)) - 65.0) < 1.0",
        "critical_facts": ["65.0", "60000", "21000"]
    },
    {
        "id": "Q075",
        "category": "Savings_Runway",
        "question": "What is my emergency fund target based on my expenses?",
        "expected_intent": "EMERGENCY_FUND_ANALYSIS",
        "eval_check": "abs(float(m.get('recommended_fund', 0)) - 63000.0) < 1.0",
        "critical_facts": ["63000"]
    },

    # =========================================================================
    # 4. Arithmetic & Spending Aggregations (25 queries)
    # =========================================================================
    {
        "id": "Q076",
        "category": "Arithmetic_Aggregation",
        "question": "What is my total monthly expenditure?",
        "expected_intent": "FINANCIAL_SUMMARY",
        "eval_check": "abs(float(m.get('total_expenses', 0)) - 21000.0) < 1.0",
        "critical_facts": ["21000"]
    },
    {
        "id": "Q077",
        "category": "Arithmetic_Aggregation",
        "question": "How much total income did I receive this month?",
        "expected_intent": "FINANCIAL_SUMMARY",
        "eval_check": "abs(float(m.get('total_income', 0)) - 60000.0) < 1.0",
        "critical_facts": ["60000"]
    },
    {
        "id": "Q078",
        "category": "Arithmetic_Aggregation",
        "question": "What is the net difference between my income and expenses?",
        "expected_intent": "SAVINGS_ANALYSIS",
        "eval_check": "abs(float(m.get('monthly_savings', 0)) - 39000.0) < 1.0",
        "critical_facts": ["39000"]
    },
    {
        "id": "Q079",
        "category": "Arithmetic_Aggregation",
        "question": "What is my average daily expense based on 30 days?",
        "expected_intent": "EXPENSE_BREAKDOWN",
        "eval_check": "abs(float(m.get('total_expenses', 0)) - 21000.0) < 1.0",
        "critical_facts": ["700", "21000"]
    },
    {
        "id": "Q080",
        "category": "Arithmetic_Aggregation",
        "question": "What are my total outflows for the current cycle?",
        "expected_intent": "FINANCIAL_SUMMARY",
        "eval_check": "abs(float(m.get('total_expenses', 0)) - 21000.0) < 1.0",
        "critical_facts": ["21000"]
    },
    {
        "id": "Q081",
        "category": "Arithmetic_Aggregation",
        "question": "How much total money is in my bank accounts?",
        "expected_intent": "FINANCIAL_SUMMARY",
        "eval_check": "abs(float(m.get('liquid_balance', 0)) - 45000.0) < 1.0",
        "critical_facts": ["45000"]
    },
    {
        "id": "Q082",
        "category": "Arithmetic_Aggregation",
        "question": "Give me a full financial summary of accounts, income and expenses",
        "expected_intent": "FINANCIAL_SUMMARY",
        "eval_check": "'total_income' in m and 'total_expenses' in m",
        "critical_facts": ["60000", "21000", "45000"]
    },
    {
        "id": "Q083",
        "category": "Arithmetic_Aggregation",
        "question": "What is my gross monthly cashflow?",
        "expected_intent": "FINANCIAL_SUMMARY",
        "eval_check": "float(m.get('total_income', 0)) == 60000.0",
        "critical_facts": ["60000", "21000"]
    },
    {
        "id": "Q084",
        "category": "Arithmetic_Aggregation",
        "question": "Sum up all my debits this month",
        "expected_intent": "EXPENSE_BREAKDOWN",
        "eval_check": "abs(float(m.get('total_expenses', 0)) - 21000.0) < 1.0",
        "critical_facts": ["21000"]
    },
    {
        "id": "Q085",
        "category": "Arithmetic_Aggregation",
        "question": "How much did I receive from salary or stipend?",
        "expected_intent": "FINANCIAL_SUMMARY",
        "eval_check": "abs(float(m.get('total_income', 0)) - 60000.0) < 1.0",
        "critical_facts": ["60000"]
    },
    {
        "id": "Q086",
        "category": "Arithmetic_Aggregation",
        "question": "What is my total discretionary spending?",
        "expected_intent": "EXPENSE_BREAKDOWN",
        "eval_check": "float(m.get('total_expenses', 0)) == 21000.0",
        "critical_facts": ["21000"]
    },
    {
        "id": "Q087",
        "category": "Arithmetic_Aggregation",
        "question": "What is my financial health score?",
        "expected_intent": "FINANCIAL_HEALTH",
        "eval_check": "abs(float(m.get('health_score', 0)) - 90.0) < 2.0",
        "critical_facts": ["90.0"]
    },
    {
        "id": "Q088",
        "category": "Arithmetic_Aggregation",
        "question": "Rate my overall financial fitness out of 100",
        "expected_intent": "FINANCIAL_HEALTH",
        "eval_check": "abs(float(m.get('health_score', 0)) - 90.0) < 2.0",
        "critical_facts": ["90.0", "A"]
    },
    {
        "id": "Q089",
        "category": "Arithmetic_Aggregation",
        "question": "What is my financial health grade?",
        "expected_intent": "FINANCIAL_HEALTH",
        "eval_check": "'A' in str(m.get('health_grade', ''))",
        "critical_facts": ["A", "90.0"]
    },
    {
        "id": "Q090",
        "category": "Arithmetic_Aggregation",
        "question": "Compare my monthly income against my total expenditure",
        "expected_intent": "SAVINGS_ANALYSIS",
        "eval_check": "float(m.get('total_income', 0)) == 60000.0 and float(m.get('total_expenses', 0)) == 21000.0",
        "critical_facts": ["60000", "21000", "39000"]
    },
    {
        "id": "Q091",
        "category": "Arithmetic_Aggregation",
        "question": "Calculate my expense ratio as percentage of my income",
        "expected_intent": "SAVINGS_ANALYSIS",
        "eval_check": "abs(float(m.get('savings_rate', 0)) - 65.0) < 1.0",
        "critical_facts": ["35.0", "21000", "60000"]
    },
    {
        "id": "Q092",
        "category": "Arithmetic_Aggregation",
        "question": "How much surplus remains in my primary checking account?",
        "expected_intent": "FINANCIAL_SUMMARY",
        "eval_check": "float(m.get('liquid_balance', 0)) == 45000.0",
        "critical_facts": ["45000"]
    },
    {
        "id": "Q093",
        "category": "Arithmetic_Aggregation",
        "question": "What is my average weekly burn rate?",
        "expected_intent": "EXPENSE_BREAKDOWN",
        "eval_check": "float(m.get('total_expenses', 0)) == 21000.0",
        "critical_facts": ["5250", "21000"]
    },
    {
        "id": "Q094",
        "category": "Arithmetic_Aggregation",
        "question": "Show my total inflows and total outflows",
        "expected_intent": "FINANCIAL_SUMMARY",
        "eval_check": "float(m.get('total_income', 0)) == 60000.0",
        "critical_facts": ["60000", "21000"]
    },
    {
        "id": "Q095",
        "category": "Arithmetic_Aggregation",
        "question": "What is my monthly net savings accumulation?",
        "expected_intent": "SAVINGS_ANALYSIS",
        "eval_check": "abs(float(m.get('monthly_savings', 0)) - 39000.0) < 1.0",
        "critical_facts": ["39000"]
    },
    {
        "id": "Q096",
        "category": "Arithmetic_Aggregation",
        "question": "How much do I have left to spend this month?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 0.0,
        "eval_check": "'35000' in str(m) or 'balance' in str(m).lower()",
        "critical_facts": ["45000", "35000"]
    },
    {
        "id": "Q097",
        "category": "Arithmetic_Aggregation",
        "question": "What is my financial summary report?",
        "expected_intent": "FINANCIAL_SUMMARY",
        "eval_check": "'total_income' in m",
        "critical_facts": ["60000", "21000", "45000"]
    },
    {
        "id": "Q098",
        "category": "Arithmetic_Aggregation",
        "question": "How much total money passed through my account this month?",
        "expected_intent": "FINANCIAL_SUMMARY",
        "eval_check": "float(m.get('total_income', 0)) == 60000.0",
        "critical_facts": ["60000", "21000"]
    },
    {
        "id": "Q099",
        "category": "Arithmetic_Aggregation",
        "question": "Give me a breakdown of my bank balances and liabilities",
        "expected_intent": "FINANCIAL_SUMMARY",
        "eval_check": "float(m.get('liquid_balance', 0)) == 45000.0",
        "critical_facts": ["45000", "150000"]
    },
    {
        "id": "Q100",
        "category": "Arithmetic_Aggregation",
        "question": "Provide my financial wellness review",
        "expected_intent": "FINANCIAL_HEALTH",
        "eval_check": "abs(float(m.get('health_score', 0)) - 90.0) < 2.0",
        "critical_facts": ["90.0", "A"]
    },

    # =========================================================================
    # 5. Category Breakdown & Merchant Inquiries (25 queries)
    # =========================================================================
    {
        "id": "Q101",
        "category": "Category_Breakdown",
        "question": "Where did I spend the most?",
        "expected_intent": "EXPENSE_BREAKDOWN",
        "eval_check": "m.get('top_category') == 'Housing'",
        "critical_facts": ["Housing", "12000", "21000"]
    },
    {
        "id": "Q102",
        "category": "Category_Breakdown",
        "question": "What is my highest spending category?",
        "expected_intent": "EXPENSE_BREAKDOWN",
        "eval_check": "m.get('top_category') == 'Housing'",
        "critical_facts": ["Housing", "12000"]
    },
    {
        "id": "Q103",
        "category": "Category_Breakdown",
        "question": "How much did I spend on food?",
        "expected_intent": "CATEGORY_EXPENSE",
        "eval_check": "abs(float(m.get('category_total', 0)) - 4000.0) < 1.0",
        "critical_facts": ["4000", "Food"]
    },
    {
        "id": "Q104",
        "category": "Category_Breakdown",
        "question": "How much did I spend on Housing?",
        "expected_intent": "CATEGORY_EXPENSE",
        "eval_check": "abs(float(m.get('category_total', 0)) - 12000.0) < 1.0",
        "critical_facts": ["12000", "Housing"]
    },
    {
        "id": "Q105",
        "category": "Category_Breakdown",
        "question": "What were my transport and travel expenses?",
        "expected_intent": "CATEGORY_EXPENSE",
        "eval_check": "abs(float(m.get('category_total', 0)) - 2500.0) < 1.0",
        "critical_facts": ["2500", "Transport"]
    },
    {
        "id": "Q106",
        "category": "Category_Breakdown",
        "question": "How much did I spend on utilities and power bills?",
        "expected_intent": "CATEGORY_EXPENSE",
        "eval_check": "abs(float(m.get('category_total', 0)) - 2500.0) < 1.0",
        "critical_facts": ["2500", "Utilities"]
    },
    {
        "id": "Q107",
        "category": "Category_Breakdown",
        "question": "What is my monthly rent expenditure?",
        "expected_intent": "CATEGORY_EXPENSE",
        "eval_check": "abs(float(m.get('category_total', 0)) - 12000.0) < 1.0",
        "critical_facts": ["12000"]
    },
    {
        "id": "Q108",
        "category": "Category_Breakdown",
        "question": "Show my complete category expense breakdown",
        "expected_intent": "EXPENSE_BREAKDOWN",
        "eval_check": "'category_breakdown' in m or 'breakdown' in str(m).lower()",
        "critical_facts": ["Housing", "Food", "Transport", "Utilities"]
    },
    {
        "id": "Q109",
        "category": "Category_Breakdown",
        "question": "What percentage of my expenses went to Housing?",
        "expected_intent": "EXPENSE_BREAKDOWN",
        "eval_check": "float(m.get('total_expenses', 0)) == 21000.0",
        "critical_facts": ["57.1", "12000", "21000"]
    },
    {
        "id": "Q110",
        "category": "Category_Breakdown",
        "question": "What percentage of my budget is spent on Food?",
        "expected_intent": "CATEGORY_EXPENSE",
        "eval_check": "float(m.get('category_total', 0)) == 4000.0",
        "critical_facts": ["19.0", "4000", "21000"]
    },
    {
        "id": "Q111",
        "category": "Category_Breakdown",
        "question": "How much did I spend on dining out and restaurants?",
        "expected_intent": "CATEGORY_EXPENSE",
        "eval_check": "float(m.get('category_total', 0)) == 4000.0",
        "critical_facts": ["4000", "Food"]
    },
    {
        "id": "Q112",
        "category": "Category_Breakdown",
        "question": "Which category takes the second highest share of my money?",
        "expected_intent": "EXPENSE_BREAKDOWN",
        "eval_check": "'Food' in str(m) or 'Housing' in str(m)",
        "critical_facts": ["Food", "4000"]
    },
    {
        "id": "Q113",
        "category": "Category_Breakdown",
        "question": "How much did I spend on metro, bus and fuel?",
        "expected_intent": "CATEGORY_EXPENSE",
        "eval_check": "abs(float(m.get('category_total', 0)) - 2500.0) < 1.0",
        "critical_facts": ["2500", "Transport"]
    },
    {
        "id": "Q114",
        "category": "Category_Breakdown",
        "question": "What are my total bills for wifi, electricity and gas?",
        "expected_intent": "CATEGORY_EXPENSE",
        "eval_check": "abs(float(m.get('category_total', 0)) - 2500.0) < 1.0",
        "critical_facts": ["2500", "Utilities"]
    },
    {
        "id": "Q115",
        "category": "Category_Breakdown",
        "question": "Did I spend any money on entertainment or movies?",
        "expected_intent": "CATEGORY_EXPENSE",
        "eval_check": "'category' in str(m).lower()",
        "critical_facts": ["Entertainment"]
    },
    {
        "id": "Q116",
        "category": "Category_Breakdown",
        "question": "What is my grocery and food total for the month?",
        "expected_intent": "CATEGORY_EXPENSE",
        "eval_check": "abs(float(m.get('category_total', 0)) - 4000.0) < 1.0",
        "critical_facts": ["4000"]
    },
    {
        "id": "Q117",
        "category": "Category_Breakdown",
        "question": "List all categories where I spent more than ₹3,000",
        "expected_intent": "EXPENSE_BREAKDOWN",
        "eval_check": "'Housing' in str(m) and 'Food' in str(m)",
        "critical_facts": ["Housing", "Food"]
    },
    {
        "id": "Q118",
        "category": "Category_Breakdown",
        "question": "How much went into essential needs like shelter and food?",
        "expected_intent": "EXPENSE_BREAKDOWN",
        "eval_check": "float(m.get('total_expenses', 0)) == 21000.0",
        "critical_facts": ["16000", "12000", "4000"]
    },
    {
        "id": "Q119",
        "category": "Category_Breakdown",
        "question": "What was my spending on Swiggy and Zomato?",
        "expected_intent": "CATEGORY_EXPENSE",
        "eval_check": "abs(float(m.get('category_total', 0)) - 4000.0) < 1.0",
        "critical_facts": ["4000", "Food"]
    },
    {
        "id": "Q120",
        "category": "Category_Breakdown",
        "question": "How much did I pay for electricity and water?",
        "expected_intent": "CATEGORY_EXPENSE",
        "eval_check": "abs(float(m.get('category_total', 0)) - 2500.0) < 1.0",
        "critical_facts": ["2500"]
    },
    {
        "id": "Q121",
        "category": "Category_Breakdown",
        "question": "Show a breakdown of my living costs",
        "expected_intent": "EXPENSE_BREAKDOWN",
        "eval_check": "'breakdown' in str(m).lower() or 'Housing' in str(m)",
        "critical_facts": ["Housing", "21000"]
    },
    {
        "id": "Q122",
        "category": "Category_Breakdown",
        "question": "What is my smallest spending category?",
        "expected_intent": "EXPENSE_BREAKDOWN",
        "eval_check": "'Transport' in str(m) or 'Utilities' in str(m)",
        "critical_facts": ["2500"]
    },
    {
        "id": "Q123",
        "category": "Category_Breakdown",
        "question": "Did I spend any money on Shopping or clothing?",
        "expected_intent": "CATEGORY_EXPENSE",
        "eval_check": "'category' in str(m).lower()",
        "critical_facts": ["Shopping"]
    },
    {
        "id": "Q124",
        "category": "Category_Breakdown",
        "question": "Which single expense accounts for over 50% of my outflow?",
        "expected_intent": "EXPENSE_BREAKDOWN",
        "eval_check": "m.get('top_category') == 'Housing'",
        "critical_facts": ["Housing", "12000"]
    },
    {
        "id": "Q125",
        "category": "Category_Breakdown",
        "question": "Provide a categorized summary of all my transactions",
        "expected_intent": "EXPENSE_BREAKDOWN",
        "eval_check": "float(m.get('total_expenses', 0)) == 21000.0",
        "critical_facts": ["Housing", "Food", "Transport", "Utilities"]
    },

    # =========================================================================
    # 6. Currency & Unit Preservation (15 queries)
    # =========================================================================
    {
        "id": "Q126",
        "category": "Currency_Preservation",
        "question": "Compare my ₹60,000 income with my ₹21,000 expenses.",
        "expected_intent": "SAVINGS_ANALYSIS",
        "eval_check": "abs(float(m.get('savings_rate', 0)) - 65.0) < 1.0",
        "critical_facts": ["₹60,000", "₹21,000", "₹39,000"]
    },
    {
        "id": "Q127",
        "category": "Currency_Preservation",
        "question": "Is ₹5,000 expense more than 10% of my salary in rupees?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 5000.0,
        "eval_check": "decision in ('SAFE', 'NOT_SAFE')",
        "critical_facts": ["₹5,000", "₹60,000"]
    },
    {
        "id": "Q128",
        "category": "Currency_Preservation",
        "question": "Express my monthly savings in Indian Rupees (₹) and percentage",
        "expected_intent": "SAVINGS_ANALYSIS",
        "eval_check": "abs(float(m.get('monthly_savings', 0)) - 39000.0) < 1.0",
        "critical_facts": ["₹39,000", "65.0%"]
    },
    {
        "id": "Q129",
        "category": "Currency_Preservation",
        "question": "What is my loan EMI amount in ₹?",
        "expected_intent": "DEBT_ANALYSIS",
        "eval_check": "abs(float(m.get('monthly_emi', 0)) - 10000.0) < 1.0",
        "critical_facts": ["₹10,000"]
    },
    {
        "id": "Q130",
        "category": "Currency_Preservation",
        "question": "State my total debt in rupees without converting to dollars",
        "expected_intent": "DEBT_ANALYSIS",
        "eval_check": "abs(float(m.get('total_outstanding_debt', 0)) - 150000.0) < 1.0",
        "critical_facts": ["₹1,50,000"]
    },
    {
        "id": "Q131",
        "category": "Currency_Preservation",
        "question": "How much is ₹4,000 food expense in proportion to my ₹60,000 earnings?",
        "expected_intent": "CATEGORY_EXPENSE",
        "eval_check": "float(m.get('category_total', 0)) == 4000.0",
        "critical_facts": ["₹4,000", "₹60,000"]
    },
    {
        "id": "Q132",
        "category": "Currency_Preservation",
        "question": "Show my emergency fund requirement in ₹ lakhs",
        "expected_intent": "EMERGENCY_FUND_ANALYSIS",
        "eval_check": "abs(float(m.get('recommended_fund', 0)) - 63000.0) < 1.0",
        "critical_facts": ["₹63,000"]
    },
    {
        "id": "Q133",
        "category": "Currency_Preservation",
        "question": "Confirm my account balance in INR",
        "expected_intent": "FINANCIAL_SUMMARY",
        "eval_check": "abs(float(m.get('liquid_balance', 0)) - 45000.0) < 1.0",
        "critical_facts": ["₹45,000"]
    },
    {
        "id": "Q134",
        "category": "Currency_Preservation",
        "question": "Can I spend ₹15,000? Answer strictly in Rupee currency",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 15000.0,
        "eval_check": "decision == 'NOT_SAFE'",
        "critical_facts": ["₹15,000", "₹20,000"]
    },
    {
        "id": "Q135",
        "category": "Currency_Preservation",
        "question": "What is my emergency shortfall in ₹?",
        "expected_intent": "EMERGENCY_FUND_ANALYSIS",
        "eval_check": "abs(float(m.get('shortfall', 0)) - 33000.0) < 1.0",
        "critical_facts": ["₹33,000"]
    },
    {
        "id": "Q136",
        "category": "Currency_Preservation",
        "question": "Report my total income with ₹ prefix and monthly unit",
        "expected_intent": "FINANCIAL_SUMMARY",
        "eval_check": "float(m.get('total_income', 0)) == 60000.0",
        "critical_facts": ["₹60,000", "/mo"]
    },
    {
        "id": "Q137",
        "category": "Currency_Preservation",
        "question": "Is my ₹21,000 expenditure less than half of my ₹60,000 income?",
        "expected_intent": "SAVINGS_ANALYSIS",
        "eval_check": "float(m.get('total_expenses', 0)) == 21000.0",
        "critical_facts": ["₹21,000", "₹60,000", "Yes"]
    },
    {
        "id": "Q138",
        "category": "Currency_Preservation",
        "question": "Express my runway in months rather than currency",
        "expected_intent": "EMERGENCY_RUNWAY_ANALYSIS",
        "eval_check": "abs(float(m.get('runway_months', 0)) - 2.14) < 0.2",
        "critical_facts": ["2.14 months"]
    },
    {
        "id": "Q139",
        "category": "Currency_Preservation",
        "question": "How much do I have left after a ₹10,000 purchase in rupees?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 10000.0,
        "eval_check": "decision in ('SAFE', 'NOT_SAFE')",
        "critical_facts": ["₹25,000", "₹10,000"]
    },
    {
        "id": "Q140",
        "category": "Currency_Preservation",
        "question": "What is my debt to income ratio expressed as percentage %?",
        "expected_intent": "DEBT_ANALYSIS",
        "eval_check": "abs(float(m.get('debt_to_income_ratio', 0)) - 16.67) < 1.0",
        "critical_facts": ["16.67%"]
    },

    # =========================================================================
    # 7. Missing Data, Boundary & Adversarial Abstention (10 queries)
    # =========================================================================
    {
        "id": "Q141",
        "category": "Abstention_Missing_Data",
        "question": "Can I afford to buy this?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": None,
        "eval_check": "'amount' in str(m).lower() or 'missing' in str(m).lower() or 'decision' in m",
        "critical_facts": ["amount"]
    },
    {
        "id": "Q142",
        "category": "Abstention_Missing_Data",
        "question": "Calculate my tax deductions under Section 80C",
        "expected_intent": "GENERAL_INQUIRY",
        "eval_check": "True",
        "critical_facts": ["tax", "80C"]
    },
    {
        "id": "Q143",
        "category": "Abstention_Missing_Data",
        "question": "What was my spending in Antarctica last month?",
        "expected_intent": "EXPENSE_BREAKDOWN",
        "eval_check": "True",
        "critical_facts": ["0", "no transactions"]
    },
    {
        "id": "Q144",
        "category": "Abstention_Missing_Data",
        "question": "What will be my stock portfolio returns next year?",
        "expected_intent": "GENERAL_INQUIRY",
        "eval_check": "True",
        "critical_facts": ["portfolio", "investment"]
    },
    {
        "id": "Q145",
        "category": "Abstention_Missing_Data",
        "question": "Can I borrow ₹50,00,000 for a commercial property?",
        "expected_intent": "DEBT_ANALYSIS",
        "eval_check": "float(m.get('total_outstanding_debt', 0)) > 0",
        "critical_facts": ["50,00,000"]
    },
    {
        "id": "Q146",
        "category": "Abstention_Missing_Data",
        "question": "What is my credit score from CIBIL?",
        "expected_intent": "FINANCIAL_HEALTH",
        "eval_check": "True",
        "critical_facts": ["credit score", "bureau"]
    },
    {
        "id": "Q147",
        "category": "Abstention_Missing_Data",
        "question": "How much did I spend in Bitcoin?",
        "expected_intent": "EXPENSE_BREAKDOWN",
        "eval_check": "True",
        "critical_facts": ["crypto", "no record"]
    },
    {
        "id": "Q148",
        "category": "Abstention_Missing_Data",
        "question": "Is it safe to spend negative ₹500?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": -500.0,
        "eval_check": "True",
        "critical_facts": ["invalid", "positive"]
    },
    {
        "id": "Q149",
        "category": "Abstention_Missing_Data",
        "question": "Predict my exact lottery winnings for next Saturday",
        "expected_intent": "GENERAL_INQUIRY",
        "eval_check": "True",
        "critical_facts": ["cannot predict", "lottery"]
    },
    {
        "id": "Q150",
        "category": "Abstention_Missing_Data",
        "question": "Can I buy a house for zero rupees?",
        "expected_intent": "PURCHASE_SAFETY",
        "amount": 0.0,
        "eval_check": "True",
        "critical_facts": ["0"]
    }
]

def main():
    target_path = Path(__file__).resolve().parent / "benchmark_150_dataset.json"
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(DATASET, f, indent=2, ensure_ascii=False)
    print(f"Successfully generated {len(DATASET)} benchmark queries in: {target_path}")

if __name__ == "__main__":
    main()
