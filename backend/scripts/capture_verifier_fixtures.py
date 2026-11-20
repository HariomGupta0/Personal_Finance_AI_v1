import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.rag.graph_rag import GraphRAG
from backend.app.services.prompt_builder import _serialize_financial_result
from backend.config import GROQ_API_KEY, LLM_MODEL

QUESTIONS = [
    {
        "id": "q1_purchase_safety",
        "question": "Can I afford a 15000 purchase?",
        "note": "Standard purchase safety check",
    },
    {
        "id": "q2_savings_rate",
        "question": "What is my savings rate?",
        "note": "Standard savings rate calculation",
    },
    {
        "id": "q3_category_expense",
        "question": "What did I spend on food last month?",
        "note": "Category expense query",
    },
    {
        "id": "q4_emergency_runway",
        "question": "How many months can I survive?",
        "note": "Nearest supported phrasing for EMERGENCY_RUNWAY_ANALYSIS ('How long can I survive on my savings?' hits 'my savings' keyword and parses as SAVINGS_ANALYSIS)",
    },
    {
        "id": "q4_survive_savings_literal",
        "question": "How long can I survive on my savings?",
        "note": "Literal phrasing requested by user (parses to SAVINGS_ANALYSIS due to 'my savings')",
    },
    {
        "id": "q5_debt_to_income",
        "question": "What is my debt to income ratio?",
        "note": "Debt analysis query",
    },
    {
        "id": "q6_financial_health",
        "question": "How is my financial health?",
        "note": "Comprehensive financial health score",
    },
    {
        "id": "q7_period_comparison",
        "question": "Compare my spending this month and last month",
        "note": "Month-over-month comparison",
    },
]


async def capture_all_fixtures() -> None:
    if not GROQ_API_KEY or not GROQ_API_KEY.strip():
        raise RuntimeError("GROQ_API_KEY is not set or empty. Cannot capture real LLM fixtures.")

    fixtures_dir = REPO_ROOT / "backend" / "tests" / "fixtures" / "verifier"
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    rag = GraphRAG()

    print(f"Starting capture of {len(QUESTIONS)} fixtures using model: {LLM_MODEL}")
    for item in QUESTIONS:
        q_id = item["id"]
        q_text = item["question"]
        print(f"\nProcessing [{q_id}]: {q_text!r}...")

        # Execute full real pipeline
        api_res = await rag.process_query_async(
            question=q_text,
            user_id="U001",
            prompt_version="v1.1",
        )

        # Build exact serialized evidence string that was inserted into the prompt
        math_res = api_res["math_result"]
        evidence_payload_facts = api_res.get("evidence", [])
        source_identifiers = api_res.get("source_identifiers", [])
        graph_paths = api_res.get("graph_paths", [])

        evidence_for_prompt = dict(math_res)
        evidence_for_prompt["_source_identifiers"] = source_identifiers
        evidence_for_prompt["_graph_paths"] = graph_paths
        evidence_for_prompt["_grounded_facts"] = [
            {
                "label": fact["label"],
                "value": fact["value"],
                "source": fact["source"],
                "node_ids": fact.get("source_node_ids", []),
            }
            for fact in evidence_payload_facts
        ]
        evidence_string = _serialize_financial_result(evidence_for_prompt)

        raw_llm_text = api_res.get("explanation", "")
        timestamp = datetime.now(timezone.utc).isoformat()

        fixture_data = {
            "question": q_text,
            "intent": api_res.get("intent"),
            "model": LLM_MODEL,
            "timestamp": timestamp,
            "math_result": math_res,
            "evidence_string": evidence_string,
            "llm_raw_text": raw_llm_text,
            "api_response": api_res,
            "metadata_note": item["note"],
        }

        out_path = fixtures_dir / f"{q_id}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(fixture_data, f, indent=2, ensure_ascii=False, default=str)

        print(f"  -> Saved {out_path.name} (intent={api_res.get('intent')}, explanation_len={len(raw_llm_text)})")

    print("\nAll verifier fixtures captured successfully!")


if __name__ == "__main__":
    asyncio.run(capture_all_fixtures())
