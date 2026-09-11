import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from fastapi.testclient import TestClient
from backend.main import app
from backend.scripts.seed_db import seed_database
from backend.config import APP_PASSWORD, APP_USERNAME

client = TestClient(app)

def test_all_api_endpoints():
    print("==================================================")
    print(" RUNNING PHASE 9: FASTAPI REST BACKEND TESTS")
    print("==================================================")

    seed_database()

    if not APP_PASSWORD:
        raise RuntimeError("APP_PASSWORD must be configured before running API integration tests")
    login = client.post("/api/auth/login", json={"username": APP_USERNAME, "password": APP_PASSWORD})
    assert login.status_code == 200

    # 0. Test User Sign-Up
    test_username = "test_user_reg"
    signup_res = client.post("/api/auth/signup", json={
        "username": test_username,
        "password": "strongPassword123",
        "name": "Test User",
        "initial_balance": 35000.0
    })
    assert signup_res.status_code == 201
    assert signup_res.json()["username"] == test_username
    print("  - POST /api/auth/signup -> 201 Created [OK]")

    # Test Duplicate User Sign-Up Prevention
    dup_res = client.post("/api/auth/signup", json={
        "username": test_username,
        "password": "strongPassword123"
    })
    assert dup_res.status_code == 400
    print("  - POST /api/auth/signup (Duplicate) -> 400 Bad Request [OK]")

    # Re-login as demo user for subsequent data tests
    login = client.post("/api/auth/login", json={"username": APP_USERNAME, "password": APP_PASSWORD})
    assert login.status_code == 200

    # 1. Health Check
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "ONLINE"
    print("  - GET / -> 200 ONLINE [OK]")

    # 2. Finance Summary
    res = client.get("/api/finance/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["income"] == 60000
    assert data["expenses"] == 21000
    assert data["savings_rate"] == 65.0
    print(f"  - GET /api/finance/summary -> 200 (Savings Rate: {data['savings_rate']}%) [OK]")

    # 3. Expenses Breakdown
    res = client.get("/api/finance/expenses")
    assert res.status_code == 200
    exp_data = res.json()
    assert exp_data["total_expenses"] == 21000
    assert exp_data["top_category"] == "Housing"
    print(f"  - GET /api/finance/expenses -> 200 (Top Category: {exp_data['top_category']}) [OK]")

    # 4. Savings
    res = client.get("/api/finance/savings")
    assert res.status_code == 200
    assert res.json()["savings"] == 39000
    print("  - GET /api/finance/savings -> 200 [OK]")

    # 5. Emergency Fund & Runway
    res = client.get("/api/finance/emergency-fund")
    assert res.status_code == 200
    ef_data = res.json()
    assert ef_data["recommended_fund"] == 63000
    assert ef_data["runway_months"] == 2.14
    print(f"  - GET /api/finance/emergency-fund -> 200 (Runway: {ef_data['runway_months']} months) [OK]")

    # 6. Debt & DTI
    res = client.get("/api/finance/debt")
    assert res.status_code == 200
    debt_data = res.json()
    assert debt_data["total_outstanding_debt"] == 150000
    assert debt_data["dti_ratio"] == 16.67
    print(f"  - GET /api/finance/debt -> 200 (DTI: {debt_data['dti_ratio']}%) [OK]")

    # 7. Financial Health
    res = client.get("/api/finance/health")
    assert res.status_code == 200
    health_data = res.json()
    assert health_data["health_score"] > 0
    print(f"  - GET /api/finance/health -> 200 (Health Score: {health_data['health_score']}/100 Grade: {health_data['grade']}) [OK]")

    # 8. Transactions List
    res = client.get("/api/transactions")
    assert res.status_code == 200
    tx_list = res.json()["transactions"]
    assert len(tx_list) == 4
    print(f"  - GET /api/transactions -> 200 (Count: {len(tx_list)}) [OK]")

    # 9. Create Transaction (NL and Structured)
    res = client.post("/api/transactions", json={
        "natural_language_input": "I spent ₹1500 on dinner with friends today"
    })
    assert res.status_code == 200
    created_tx = res.json()["transaction"]
    assert created_tx["amount"] == 1500.0
    print(f"  - POST /api/transactions (NL) -> 200 (Recorded: ₹{created_tx['amount']}) [OK]")

    # Delete the created transaction
    del_res = client.delete(f"/api/transactions/{created_tx['transaction_id']}")
    assert del_res.status_code == 200
    print(f"  - DELETE /api/transactions/{created_tx['transaction_id']} -> 200 [OK]")

    # 10. Assistant Query via GraphRAG
    res = client.post("/api/assistant/query", json={
        "question": "Can I spend ₹15000 on a phone?"
    })
    assert res.status_code == 200
    ai_data = res.json()
    assert ai_data["intent"] == "PURCHASE_SAFETY"
    assert ai_data["math_result"]["decision"] == "NOT_SAFE"
    assert len(ai_data["evidence"]) >= 3
    assert len(ai_data["explanation"]) > 20
    print(f"  - POST /api/assistant/query -> 200 (Decision: {ai_data['math_result']['decision']}, Evidence items: {len(ai_data['evidence'])}) [OK]")

    print("\n==================================================")
    print(" ALL FASTAPI REST BACKEND TESTS PASSED (100%)!")
    print("==================================================")

if __name__ == "__main__":
    test_all_api_endpoints()
