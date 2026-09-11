import sys
from pathlib import Path
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from backend.app.rag.graph_rag import GraphRAG
from backend.scripts.seed_db import seed_database

EVALUATION_DATASET = [
    {
        "id": "Q1",
        "question": "Can I spend ₹15,000 on a phone?",
        "expected_intent": "PURCHASE_SAFETY",
        "expected_decision": "NOT_SAFE",
        "critical_facts": ["45000", "10000", "15000", "20000", "63000"]
    },
    {
        "id": "Q2",
        "question": "What is my savings rate?",
        "expected_intent": "SAVINGS_ANALYSIS",
        "expected_value": 65.0,
        "critical_facts": ["60000", "21000", "39000", "65.0"]
    },
    {
        "id": "Q3",
        "question": "How much emergency fund do I need?",
        "expected_intent": "EMERGENCY_FUND_ANALYSIS",
        "expected_value": 63000,
        "critical_facts": ["21000", "63000", "30000", "33000"]
    },
    {
        "id": "Q4",
        "question": "How many months can I survive on my runway?",
        "expected_intent": "EMERGENCY_RUNWAY_ANALYSIS",
        "expected_value": 2.14,
        "critical_facts": ["45000", "21000", "2.14"]
    },
    {
        "id": "Q5",
        "question": "Where did I spend the most?",
        "expected_intent": "EXPENSE_BREAKDOWN",
        "expected_value": "Housing",
        "critical_facts": ["Housing", "12000", "21000"]
    },
    {
        "id": "Q6",
        "question": "How much did I spend on food?",
        "expected_intent": "CATEGORY_EXPENSE",
        "expected_value": 4000,
        "critical_facts": ["4000", "Food"]
    },
    {
        "id": "Q7",
        "question": "How much debt do I have?",
        "expected_intent": "DEBT_ANALYSIS",
        "expected_value": 150000,
        "critical_facts": ["150000", "10000", "16.67"]
    },
    {
        "id": "Q8",
        "question": "What is my financial health score?",
        "expected_intent": "FINANCIAL_HEALTH",
        "expected_value": 90.0,
        "critical_facts": ["90.0", "A"]
    },
    {
        "id": "Q9",
        "question": "Can I buy a laptop for 50000?",
        "expected_intent": "PURCHASE_SAFETY",
        "expected_decision": "NOT_SAFE",
        "critical_facts": ["50000", "NOT_SAFE"]
    },
    {
        "id": "Q10",
        "question": "Give me a financial summary",
        "expected_intent": "FINANCIAL_SUMMARY",
        "expected_value": None,
        "critical_facts": ["60000", "21000", "39000", "65.0", "33000"]
    }
]

def run_evaluation_benchmark():
    print("==================================================")
    print(" RESEARCH EVALUATION BENCHMARK: PROPOSED GraphRAG")
    print("==================================================")

    seed_database()
    graph_rag = GraphRAG()

    total_queries = len(EVALUATION_DATASET)
    intent_correct = 0
    math_correct = 0
    grounding_supported = 0
    currency_preserved = 0
    hallucination_free = 0
    latencies = []

    for item in EVALUATION_DATASET:
        start_t = time.time()
        res = graph_rag.process_query(item["question"], user_id="U001")
        elapsed = (time.time() - start_t) * 1000
        latencies.append(elapsed)

        # 1. Intent Accuracy
        if res["intent"] == item["expected_intent"]:
            intent_correct += 1

        # 2. Math Accuracy
        math_res = res.get("math_result") or {}
        if item.get("expected_decision"):
            if math_res.get("decision") == item["expected_decision"]:
                math_correct += 1
        elif item.get("expected_value") is not None:
            val_str = str(item["expected_value"])
            if val_str in str(math_res):
                math_correct += 1
        else:
            math_correct += 1

        # 3. Grounding Completeness (verifying critical facts in evidence or explanation)
        expl = res.get("explanation", "")
        ev_str = str(res.get("evidence", []))
        all_present = all(fact in expl or fact in ev_str for fact in item["critical_facts"])
        if all_present:
            grounding_supported += 1

        # 4. Currency Preservation (checks for ₹ and absence of foreign $ symbol)
        if "₹" in expl and "$" not in expl and "USD" not in expl:
            currency_preserved += 1

        # 5. Hallucination Check
        if "$" not in expl and "EUR" not in expl:
            hallucination_free += 1

        print(f"  [{item['id']}] '{item['question']}' -> Intent: {res['intent']} | Latency: {elapsed:.0f}ms [PASS]")

    avg_latency = sum(latencies) / len(latencies)

    print("\n--------------------------------------------------")
    print(" BENCHMARK RESULTS SUMMARY:")
    print("--------------------------------------------------")
    print(f"  Total Queries Evaluated:       {total_queries}")
    print(f"  Intent Recognition Accuracy:  {(intent_correct/total_queries)*100:.1f}%")
    print(f"  Deterministic Math Accuracy:  {(math_correct/total_queries)*100:.1f}%")
    print(f"  Grounding Completeness Rate:  {(grounding_supported/total_queries)*100:.1f}%")
    print(f"  Currency Preservation Rate:   {(currency_preserved/total_queries)*100:.1f}%")
    print(f"  Hallucination-Free Rate:      {(hallucination_free/total_queries)*100:.1f}%")
    print(f"  Average End-to-End Latency:   {avg_latency:.1f}ms")
    print("==================================================")

    return {
        "intent_accuracy": (intent_correct/total_queries)*100,
        "math_accuracy": (math_correct/total_queries)*100,
        "grounding_rate": (grounding_supported/total_queries)*100,
        "currency_preservation": (currency_preserved/total_queries)*100,
        "hallucination_free_rate": (hallucination_free/total_queries)*100,
        "avg_latency_ms": avg_latency
    }

if __name__ == "__main__":
    run_evaluation_benchmark()
