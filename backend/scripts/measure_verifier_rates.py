import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.rag.graph_rag import GraphRAG

QUESTIONS_BY_INTENT = [
    ("PURCHASE_SAFETY", "Can I afford a 15000 purchase?"),
    ("SAVINGS_ANALYSIS", "What is my savings rate?"),
    ("CATEGORY_EXPENSE", "What did I spend on food last month?"),
    ("EMERGENCY_RUNWAY_ANALYSIS", "How many months can I survive?"),
    ("DEBT_ANALYSIS", "What is my debt to income ratio?"),
    ("FINANCIAL_HEALTH", "How is my financial health?"),
    ("PERIOD_COMPARISON", "Compare my spending this month and last month"),
]


async def run_measurements(out_path: Path, repeats: int, versions: list[str]) -> None:
    # Ensure out_path is outside repository
    resolved_out = out_path.resolve()
    if REPO_ROOT in resolved_out.parents or resolved_out == REPO_ROOT:
        raise ValueError(f"--out path ({resolved_out}) must be outside repository root ({REPO_ROOT})")

    resolved_out.parent.mkdir(parents=True, exist_ok=True)

    rag = GraphRAG()
    runs = []

    print(f"Beginning measurement run:")
    print(f"  Intents: {len(QUESTIONS_BY_INTENT)}")
    print(f"  Versions: {versions}")
    print(f"  Repeats per version: {repeats}")
    print(f"  Total planned runs: {len(QUESTIONS_BY_INTENT) * len(versions) * repeats}")
    print(f"  Output destination: {resolved_out}\n")

    # Open file for appending JSON lines
    with open(resolved_out, "w", encoding="utf-8") as f_out:
        for version in versions:
            print(f"=== Measuring Prompt Version: {version} ===")
            for intent, question in QUESTIONS_BY_INTENT:
                for rep in range(1, repeats + 1):
                    start_t = time.perf_counter()
                    try:
                        api_res = await rag.process_query_async(
                            question=question,
                            user_id="U001",
                            prompt_version=version,
                        )
                        latency = (time.perf_counter() - start_t) * 1000
                        tokens = api_res.get("tokens", {}).get("total", 0)

                        record = {
                            "question": question,
                            "intent": intent,
                            "version": version,
                            "repeat": rep,
                            "first_attempt_blocking": api_res.get("first_attempt_blocking", 0),
                            "first_attempt_advisory": api_res.get("first_attempt_advisory", 0),
                            "attempts": api_res.get("attempts", 1),
                            "fallback_used": api_res.get("fallback_used", False),
                            "verified": api_res.get("verified", False),
                            "tokens": tokens,
                            "latency": round(latency, 1),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    except Exception as exc:
                        latency = (time.perf_counter() - start_t) * 1000
                        record = {
                            "question": question,
                            "intent": intent,
                            "version": version,
                            "repeat": rep,
                            "first_attempt_blocking": 999,
                            "first_attempt_advisory": 0,
                            "attempts": 1,
                            "fallback_used": True,
                            "verified": False,
                            "tokens": 0,
                            "latency": round(latency, 1),
                            "error": str(exc),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }

                    runs.append(record)
                    f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
                    f_out.flush()

                    status_sym = "✓" if record["verified"] else "✗"
                    fb_sym = " [FALLBACK]" if record["fallback_used"] else ""
                    print(
                        f"  [{version}][{intent[:14]:14}] rep {rep}/{repeats} -> "
                        f"verified={status_sym}{fb_sym} | "
                        f"blocking={record['first_attempt_blocking']} | "
                        f"advisory={record['first_attempt_advisory']} | "
                        f"tokens={record['tokens']} | "
                        f"latency={record['latency']}ms"
                    )
                    # Short delay between requests to stay well within Groq rate limits
                    await asyncio.sleep(0.3)

    # Compute and print summary table
    print("\n" + "=" * 95)
    print("MEASUREMENT SUMMARY TABLE")
    print("=" * 95)
    print(
        f"{'Version':<10} | {'Total Runs':<10} | {'1st-Attempt Clean':<18} | {'Final Verified':<14} | {'Fallback Rate':<14} | {'Mean Advisory':<14} | {'Mean Tokens':<12}"
    )
    print("-" * 95)

    summary_rows = []
    for version in versions:
        v_runs = [r for r in runs if r["version"] == version]
        total = len(v_runs)
        if total == 0:
            continue

        clean_1st = sum(1 for r in v_runs if r["first_attempt_blocking"] == 0)
        clean_1st_rate = (clean_1st / total) * 100.0

        final_ver = sum(1 for r in v_runs if r["verified"])
        final_ver_rate = (final_ver / total) * 100.0

        fallbacks = sum(1 for r in v_runs if r["fallback_used"])
        fallback_rate = (fallbacks / total) * 100.0

        mean_advisory = sum(r["first_attempt_advisory"] for r in v_runs) / total
        mean_tokens = sum(r["tokens"] for r in v_runs) / total

        row_str = (
            f"{version:<10} | {total:<10} | {clean_1st_rate:>16.1f}% | {final_ver_rate:>12.1f}% | "
            f"{fallback_rate:>12.1f}% | {mean_advisory:>14.2f} | {mean_tokens:>12.1f}"
        )
        print(row_str)
        summary_rows.append({
            "version": version,
            "total_runs": total,
            "first_attempt_clean_rate": clean_1st_rate,
            "final_verified_rate": final_ver_rate,
            "fallback_rate": fallback_rate,
            "mean_advisory": mean_advisory,
            "mean_tokens": mean_tokens,
        })

    print("=" * 95)
    print(f"Results written to: {resolved_out}")


def main():
    parser = argparse.ArgumentParser(description="Measure verifier rates across prompt versions.")
    parser.add_argument("--out", required=True, help="Path for output JSON lines file (must be outside repo)")
    parser.add_argument("--repeats", type=int, default=5, help="Number of repeats per question (default 5)")
    parser.add_argument("--versions", default="v1.1,v1.2", help="Comma-separated prompt versions (default 'v1.1,v1.2')")

    args = parser.parse_args()
    versions = [v.strip() for v in args.versions.split(",") if v.strip()]
    asyncio.run(run_measurements(Path(args.out), args.repeats, versions))


if __name__ == "__main__":
    main()
