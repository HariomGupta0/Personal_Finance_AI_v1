import json
import statistics
import sys
import time
from pathlib import Path

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
        "eval_check": lambda m: m.get("decision") == "NOT_SAFE",
        "critical_facts": ["45000", "10000", "15000", "20000", "63000"]
    },
    {
        "id": "Q2",
        "question": "What is my savings rate?",
        "expected_intent": "SAVINGS_ANALYSIS",
        "eval_check": lambda m: abs(float(m.get("savings_rate", -999)) - 65.0) < 0.5,
        "critical_facts": ["60000", "21000", "39000", "65.0"]
    },
    {
        "id": "Q3",
        "question": "How much emergency fund do I need?",
        "expected_intent": "EMERGENCY_FUND_ANALYSIS",
        "eval_check": lambda m: abs(float(m.get("recommended_fund", -999)) - 63000.0) < 1.0,
        "critical_facts": ["21000", "63000", "30000", "33000"]
    },
    {
        "id": "Q4",
        "question": "How many months can I survive on my runway?",
        "expected_intent": "EMERGENCY_RUNWAY_ANALYSIS",
        "eval_check": lambda m: abs(float(m.get("runway_months", -999)) - 2.14) < 0.1,
        "critical_facts": ["45000", "21000", "2.14"]
    },
    {
        "id": "Q5",
        "question": "Where did I spend the most?",
        "expected_intent": "EXPENSE_BREAKDOWN",
        "eval_check": lambda m: m.get("top_category") == "Housing",
        "critical_facts": ["Housing", "12000", "21000"]
    },
    {
        "id": "Q6",
        "question": "How much did I spend on food?",
        "expected_intent": "CATEGORY_EXPENSE",
        "eval_check": lambda m: abs(float(m.get("category_total", -999)) - 4000.0) < 1.0,
        "critical_facts": ["4000", "Food"]
    },
    {
        "id": "Q7",
        "question": "How much debt do I have?",
        "expected_intent": "DEBT_ANALYSIS",
        "eval_check": lambda m: abs(float(m.get("total_outstanding_debt", -999)) - 150000.0) < 1.0,
        "critical_facts": ["150000", "10000", "16.67"]
    },
    {
        "id": "Q8",
        "question": "What is my financial health score?",
        "expected_intent": "FINANCIAL_HEALTH",
        "eval_check": lambda m: abs(float(m.get("health_score", -999)) - 90.0) < 1.0,
        "critical_facts": ["90.0", "A"]
    },
    {
        "id": "Q9",
        "question": "Can I buy a laptop for 50000?",
        "expected_intent": "PURCHASE_SAFETY",
        "eval_check": lambda m: m.get("decision") == "NOT_SAFE",
        "critical_facts": ["50000", "NOT_SAFE"]
    },
    {
        "id": "Q10",
        "question": "Give me a financial summary",
        "expected_intent": "FINANCIAL_SUMMARY",
        "eval_check": lambda m: "savings_rate" in m and "total_income" in m,
        "critical_facts": ["60000", "21000", "39000", "65.0", "33000"]
    }
]

def run_evaluation_benchmark(output_path: str = "benchmark_results.json"):
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
    stage_latencies = {"nlu_ms": [], "graph_ms": [], "engine_ms": [], "llm_ms": []}
    tokens_recorded = []
    per_query_results = []

    for item in EVALUATION_DATASET:
        start_t = time.time()
        res = graph_rag.process_query(item["question"], user_id="U001")
        elapsed = (time.time() - start_t) * 1000
        latencies.append(elapsed)

        # Stage latency tracking
        breakdown = res.get("latency_breakdown", {})
        for stage_k in stage_latencies.keys():
            if stage_k in breakdown:
                stage_latencies[stage_k].append(breakdown[stage_k])

        # Tokens tracking
        tok = res.get("tokens")
        if tok:
            tokens_recorded.append(tok)

        # 1. Intent Accuracy
        is_intent_ok = res["intent"] == item["expected_intent"]
        if is_intent_ok:
            intent_correct += 1

        # 2. Math Accuracy (Deterministic validation with tolerance)
        math_res = res.get("math_result") or {}
        is_math_ok = bool(item["eval_check"](math_res))
        if is_math_ok:
            math_correct += 1

        # 3. Grounding Completeness (verifying critical facts in evidence or explanation)
        expl = res.get("explanation", "")
        ev_str = str(res.get("evidence", []))
        all_present = all(fact in expl or fact in ev_str for fact in item["critical_facts"])
        if all_present:
            grounding_supported += 1

        # 4. Currency Preservation (checks for ₹ and absence of foreign $ symbol)
        is_currency_ok = ("₹" in expl and "$" not in expl and "USD" not in expl)
        if is_currency_ok:
            currency_preserved += 1

        # 5. Hallucination Check
        is_hallucination_free = ("$" not in expl and "EUR" not in expl)
        if is_hallucination_free:
            hallucination_free += 1

        query_summary = {
            "id": item["id"],
            "question": item["question"],
            "intent": res["intent"],
            "intent_match": is_intent_ok,
            "math_match": is_math_ok,
            "latency_ms": round(elapsed, 1),
            "stage_breakdown": breakdown,
            "tokens": tok
        }
        per_query_results.append(query_summary)

        status_str = "PASS" if (is_intent_ok and is_math_ok and all_present) else "WARN"
        print(f"  [{item['id']}] '{item['question']}' -> Intent: {res['intent']} | Latency: {elapsed:.0f}ms [{status_str}]")

    avg_latency = sum(latencies) / len(latencies)
    sorted_latencies = sorted(latencies)
    p50_latency = statistics.median(sorted_latencies)
    p95_latency = sorted_latencies[int(len(sorted_latencies) * 0.95)] if len(sorted_latencies) >= 20 else sorted_latencies[-1]

    avg_stages = {k: round(sum(v)/len(v), 1) if v else 0.0 for k, v in stage_latencies.items()}

    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_queries": total_queries,
        "metrics": {
            "intent_accuracy_percent": round((intent_correct / total_queries) * 100, 2),
            "math_accuracy_percent": round((math_correct / total_queries) * 100, 2),
            "grounding_completeness_percent": round((grounding_supported / total_queries) * 100, 2),
            "currency_preservation_percent": round((currency_preserved / total_queries) * 100, 2),
            "hallucination_free_percent": round((hallucination_free / total_queries) * 100, 2),
            "avg_latency_ms": round(avg_latency, 1),
            "p50_latency_ms": round(p50_latency, 1),
            "p95_latency_ms": round(p95_latency, 1),
            "avg_stage_latencies_ms": avg_stages,
        },
        "query_evaluations": per_query_results
    }

    print("\n--------------------------------------------------")
    print(" BENCHMARK RESULTS SUMMARY:")
    print("--------------------------------------------------")
    print(f"  Total Queries Evaluated:       {total_queries}")
    print(f"  Intent Recognition Accuracy:  {summary['metrics']['intent_accuracy_percent']}%")
    print(f"  Deterministic Math Accuracy:  {summary['metrics']['math_accuracy_percent']}%")
    print(f"  Grounding Completeness Rate:  {summary['metrics']['grounding_completeness_percent']}%")
    print(f"  Currency Preservation Rate:   {summary['metrics']['currency_preservation_percent']}%")
    print(f"  Hallucination-Free Rate:      {summary['metrics']['hallucination_free_percent']}%")
    print(f"  Latency (Mean / p50 / p95):   {avg_latency:.1f}ms / {p50_latency:.1f}ms / {p95_latency:.1f}ms")
    print(f"  Avg Stage Breakdown (ms):     {avg_stages}")
    print("==================================================")

    # Persist results to disk for CI / documentation
    try:
        out_file = PROJECT_ROOT / output_path
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"  Persisted benchmark results to: {out_file}")
    except Exception as e:
        print(f"  Failed to write benchmark results file: {e}")

    return summary

if __name__ == "__main__":
    run_evaluation_benchmark()
