import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from backend.app.database.neo4j_service import Neo4jService
from backend.app.nlu.transaction_extractor import extract_transaction_rules
from backend.app.services.ingestion_service import IngestionService
from backend.app.engine.financial_engine import calculate_savings_rate
from backend.scripts.seed_db import seed_database

def test_dynamic_graph():
    print("==================================================")
    print(" RUNNING PHASE 1: DYNAMIC KNOWLEDGE GRAPH TESTS")
    print("==================================================")

    seed_database()
    db = Neo4jService()
    ingestion = IngestionService(db=db)

    # 1. Test Natural Language Transaction Extractor
    print("\n[1] Testing Natural Language Transaction Extraction:")
    test_nl_cases = [
        ("I spent ₹5000 on food today", 5000.0, "Food", "EXPENSE"),
        ("Paid 1200 for electricity bill", 1200.0, "Utilities", "EXPENSE"),
        ("Spent 2500 on groceries yesterday", 2500.0, "Food", "EXPENSE"),
        ("Bought a shirt for ₹1800", 1800.0, "Shopping", "EXPENSE"),
        ("Paid ₹400 for movie ticket", 400.0, "Entertainment", "EXPENSE"),
        ("Cab fare of 350", 350.0, "Transport", "EXPENSE"),
        ("Doctor consultation ₹1500", 1500.0, "Healthcare", "EXPENSE"),
        ("Received 60000 salary", 60000.0, "Salary", "INCOME")
    ]

    for text, expected_amt, expected_cat, expected_type in test_nl_cases:
        res = extract_transaction_rules(text)
        assert res is not None, f"Failed to extract transaction from '{text}'"
        assert res["amount"] == expected_amt, f"Expected amount {expected_amt}, got {res['amount']} for '{text}'"
        assert res["category"] == expected_cat, f"Expected category {expected_cat}, got {res['category']} for '{text}'"
        assert res["type"] == expected_type, f"Expected type {expected_type}, got {res['type']} for '{text}'"
        print(f"  - '{text}' -> {res['type']} ₹{res['amount']} [{res['category']}] (Date: {res['date']}) [OK]")

    # 2. Test Dynamic Ingestion & Real-Time Financial Recalculation
    print("\n[2] Testing Dynamic Transaction Ingestion & Impact:")
    ctx_initial = db.get_financial_context("U001")
    assert ctx_initial["accounts"][0]["balance"] == 45000
    assert len(ctx_initial["transactions"]) == 4

    ingest_res = ingestion.ingest_transaction_from_text("I spent ₹5000 on food today", user_id="U001")
    print(f"  - Impact: {ingest_res['impact_summary']}")

    assert ingest_res["status"] == "SUCCESS"
    tx = ingest_res["transaction"]
    assert tx["amount"] == 5000.0
    assert tx["category"] == "Food"
    assert tx["new_balance"] == 40000.0

    after_m = ingest_res["after_metrics"]
    assert after_m["expenses"] == 26000.0
    assert after_m["savings"] == 34000.0
    assert after_m["savings_rate"] == 56.67
    assert after_m["recommended_emergency_fund"] == 78000.0
    assert after_m["emergency_fund_shortfall"] == 48000.0
    print("  -> Dynamic graph updated balance (₹40,000) and recalculated metrics in real time.")

    # 3. Test Dynamic Transaction Update
    print("\n[3] Testing Transaction Update:")
    tx_id = tx["transaction_id"]
    update_res = db.update_transaction("U001", tx_id, amount=2000.0, description="Light dinner", category_name="Food")
    print(f"  - Updated Transaction {tx_id}: amount=₹{update_res['amount']}, new_balance=₹{update_res['new_balance']}")
    assert update_res["amount"] == 2000.0
    assert update_res["new_balance"] == 43000.0

    ctx_after_upd = db.get_financial_context("U001")
    savings_upd = calculate_savings_rate(ctx_after_upd)
    assert savings_upd["total_expenses"] == 23000.0
    assert savings_upd["savings_rate"] == 61.67
    print("  -> Transaction updated and account balance reconciled correctly.")

    # 4. Test Dynamic Transaction Deletion
    print("\n[4] Testing Transaction Deletion:")
    del_res = db.delete_transaction("U001", tx_id)
    print(f"  - Deleted {tx_id}: Restored Balance = ₹{del_res['restored_balance']}")
    assert del_res["restored_balance"] == 45000.0

    ctx_after_del = db.get_financial_context("U001")
    assert len(ctx_after_del["transactions"]) == 4
    assert ctx_after_del["accounts"][0]["balance"] == 45000.0
    savings_restored = calculate_savings_rate(ctx_after_del)
    assert savings_restored["total_expenses"] == 21000.0
    assert savings_restored["savings_rate"] == 65.0
    print("  -> Transaction deleted, account balance and financial metrics restored to baseline.")

    # 5. Test Dynamic Income, Goal, Loan, and EMI
    print("\n[5] Testing Income, Goal, Loan, and EMI Mutations:")
    inc_res = ingestion.ingest_income(user_id="U001", source="Freelance", amount=15000.0, account_id="A001")
    print(f"  - Added Income: {inc_res['impact_summary']}")
    assert inc_res["after_metrics"]["income"] == 75000.0
    assert inc_res["after_metrics"]["savings"] == 54000.0
    assert inc_res["after_metrics"]["savings_rate"] == 72.0

    goal_res = ingestion.ingest_goal(user_id="U001", name="Emergency Fund", target_amount=150000.0, current_amount=40000.0)
    print(f"  - Updated Goal: Target=₹{goal_res['goal']['target_amount']}, Current=₹{goal_res['goal']['current_amount']}")
    assert goal_res["goal"]["target_amount"] == 150000.0
    assert goal_res["goal"]["current_amount"] == 40000.0

    loan_res = db.add_loan(user_id="U001", name="Car Loan", principal=500000.0, outstanding=400000.0)
    assert loan_res["name"] == "Car Loan"
    emi_res = db.add_emi(loan_id=loan_res["id"], amount=12000.0, due_date="2026-09-25", status="PENDING")
    assert emi_res["amount"] == 12000.0
    print(f"  - Created Loan '{loan_res['name']}' with EMI of ₹{emi_res['amount']}")

    emi_upd = db.update_emi_status(emi_res["id"], status="PAID", account_id="A001")
    assert emi_upd["status"] == "PAID"
    print(f"  - Updated EMI status to {emi_upd['status']}")

    # 6. Reset to Clean Baseline
    print("\n[6] Resetting Graph to Clean Baseline:")
    seed_database()
    ctx_final = db.get_financial_context("U001")
    assert ctx_final["accounts"][0]["balance"] == 45000.0
    assert len(ctx_final["transactions"]) == 4
    db.close()

    print("\n==================================================")
    print(" ALL DYNAMIC KNOWLEDGE GRAPH TESTS PASSED (100%)!")
    print("==================================================")

if __name__ == "__main__":
    test_dynamic_graph()
