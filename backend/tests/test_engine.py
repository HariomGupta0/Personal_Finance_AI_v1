from backend.app.database.neo4j_service import Neo4jService
from backend.app.engine.financial_engine import (
    check_purchase_safety,
    calculate_savings_rate,
    calculate_emergency_fund
)

db = Neo4jService()

context = db.get_financial_context("U001")

savings = calculate_savings_rate(context)

print("\n--- Savings Analysis ---")
print(f"Income: ₹{savings['total_income']}")
print(f"Expenses: ₹{savings['total_expenses']}")
print(f"Savings: ₹{savings['savings']}")
print(f"Savings Rate: {savings['savings_rate']}%")

emergency = calculate_emergency_fund(context)

print("\n--- Emergency Fund Analysis ---")
print(f"Monthly Expenses: ₹{emergency['monthly_expenses']}")
print(f"Recommended Fund: ₹{emergency['recommended_fund']}")
print(f"Current Fund: ₹{emergency['current_fund']}")
print(f"Shortfall: ₹{emergency['shortfall']}")

for amount in [5000, 15000, 30000]:
    result = check_purchase_safety(context, amount)
    print(f"\nPurchase: ₹{amount}")
    print(f"Decision: {result['decision']}")
    print(f"Risk Level: {result['risk_level']}")
    print(f"Reason: {result['reason']}")

db.close()
