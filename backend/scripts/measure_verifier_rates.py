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
from backend.app.services.llm_service import _DEFAULT_FALLBACK_TEXT

QUESTIONS_BY_INTENT = [
    ("PURCHASE_SAFETY", "Can I afford a 15000 purchase?"),
    ("SAVINGS_ANALYSIS", "What is my savings rate?"),
    ("CATEGORY_EXPENSE", "What did I spend on food last month?"),
    ("EMERGENCY_RUNWAY_ANALYSIS", "How many months can I survive?"),
    ("DEBT_ANALYSIS", "What is my debt to income ratio?"),
    ("FINANCIAL_HEALTH", "How is my financial health?"),
    ("PERIOD_COMPARISON", "Compare my spending this month and last month"),
]


def display_summary_tables(runs: list[dict], versions: list[str]) -> None:
    print("\n" + "=" * 125)
    print("MEASUREMENT SUMMARY TABLE")
    print("=" * 125)
    print(
        f"{'Version':<8} | {'Total Runs':<10} | {'1st-Attempt Clean':<18} | {'Final Verified':<14} | {'Verifier Fallbacks':<18} | {'LLM Errors':<10} | {'Mean Advisory':<13} | {'Mean Tokens':<11} | {'Models Seen'}"
    )
    print("-" * 125)

    for version in versions:
        v_runs = [r for r in runs if r.get("version") == version]
        total = len(v_runs)
        if total == 0:
            continue

        clean_1st = sum(1 for r in v_runs if r.get("first_attempt_blocking") == 0 and not r.get("llm_errored"))
        clean_1st_rate = (clean_1st / total) * 100.0

        final_ver = sum(1 for r in v_runs if r.get("verified"))
        final_ver_rate = (final_ver / total) * 100.0

        llm_err_count = sum(1 for r in v_runs if r.get("llm_errored"))
        verifier_fallbacks = sum(1 for r in v_runs if r.get("fallback_used") and not r.get("llm_errored"))
        verifier_fallback_rate = (verifier_fallbacks / total) * 100.0

        mean_advisory = sum(r.get("first_attempt_advisory", 0) for r in v_runs) / total
        mean_tokens = sum(r.get("tokens", 0) for r in v_runs) / total
        models_seen = ", ".join(sorted({r.get("model", "") for r in v_runs if r.get("model") and r.get("model") != "ERROR"})) or "none"

        row_str = (
            f"{version:<8} | {total:<10} | {clean_1st_rate:>16.1f}% | {final_ver_rate:>12.1f}% | "
            f"{verifier_fallback_rate:>16.1f}% | {llm_err_count:>10} | {mean_advisory:>13.2f} | {mean_tokens:>11.1f} | {models_seen}"
        )
        print(row_str)

    print("=" * 125)

    # Print Per-Intent Table
    print("\n" + "=" * 125)
    print("PER-INTENT MEASUREMENT TABLE")
    print("=" * 125)
    print(
        f"{'Intent':<26} | {'Version':<7} | {'Runs':<4} | {'1st Clean %':<11} | {'Verifier FB %':<13} | {'LLM Errors':<10} | {'Mean Tokens':<11} | {'Models Seen'}"
    )
    print("-" * 125)

    for intent, _ in QUESTIONS_BY_INTENT:
        for version in versions:
            iv_runs = [r for r in runs if r.get("intent") == intent and r.get("version") == version]
            total = len(iv_runs)
            if total == 0:
                continue
            clean_1st = sum(1 for r in iv_runs if r.get("first_attempt_blocking") == 0 and not r.get("llm_errored"))
            clean_1st_rate = (clean_1st / total) * 100.0
            verifier_fallbacks = sum(1 for r in iv_runs if r.get("fallback_used") and not r.get("llm_errored"))
            verifier_fb_rate = (verifier_fallbacks / total) * 100.0
            llm_err_count = sum(1 for r in iv_runs if r.get("llm_errored"))
            mean_tokens = sum(r.get("tokens", 0) for r in iv_runs) / total
            models_seen = ", ".join(sorted({r.get("model", "") for r in iv_runs if r.get("model") and r.get("model") != "ERROR"})) or "none"

            print(
                f"{intent:<26} | {version:<7} | {total:<4} | {clean_1st_rate:>9.1f}% | {verifier_fb_rate:>11.1f}% | "
                f"{llm_err_count:>10} | {mean_tokens:>11.1f} | {models_seen}"
            )

    print("=" * 125)


async def run_measurements(
    out_path: Path,
    repeats: int,
    versions: list[str],
    sleep_delay: float = 2.0,
) -> None:
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
    print(f"  Sleep delay: {sleep_delay}s")
    print(f"  Total planned runs: {len(QUESTIONS_BY_INTENT) * len(versions) * repeats}")
    print(f"  Output destination: {resolved_out}\n")

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
                        model_name = api_res.get("model", "")
                        explanation = api_res.get("explanation", "").strip()

                        is_llm_error = (
                            tokens == 0
                            or not model_name
                            or explanation == _DEFAULT_FALLBACK_TEXT.strip()
                            or api_res.get("llm_error") is not None
                        )

                        record = {
                            "question": question,
                            "intent": intent,
                            "version": version,
                            "repeat": rep,
                            "model": model_name,
                            "first_attempt_blocking": api_res.get("first_attempt_blocking", 0),
                            "first_attempt_advisory": api_res.get("first_attempt_advisory", 0),
                            "attempts": api_res.get("attempts", 1),
                            "fallback_used": api_res.get("fallback_used", False),
                            "verified": api_res.get("verified", False),
                            "llm_errored": is_llm_error,
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
                            "model": "ERROR",
                            "first_attempt_blocking": 999,
                            "first_attempt_advisory": 0,
                            "attempts": 1,
                            "fallback_used": True,
                            "verified": False,
                            "llm_errored": True,
                            "tokens": 0,
                            "latency": round(latency, 1),
                            "error": str(exc),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }

                    runs.append(record)
                    f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
                    f_out.flush()

                    status_sym = "PASS" if record["verified"] else "FAIL"
                    fb_sym = " [FALLBACK]" if record["fallback_used"] else ""
                    err_sym = " [LLM_ERR]" if record["llm_errored"] else ""
                    print(
                        f"  [{version}][{intent[:14]:14}] rep {rep}/{repeats} -> "
                        f"verified={status_sym}{fb_sym}{err_sym} | "
                        f"model={record.get('model', '')} | "
                        f"blocking={record['first_attempt_blocking']} | "
                        f"advisory={record['first_attempt_advisory']} | "
                        f"tokens={record['tokens']} | "
                        f"latency={record['latency']}ms"
                    )
                    await asyncio.sleep(sleep_delay)

    display_summary_tables(runs, versions)
    print(f"Results written to: {resolved_out}")


def main():
    parser = argparse.ArgumentParser(description="Measure verifier rates across prompt versions.")
    parser.add_argument("--out", help="Path for output JSON lines file (must be outside repo)")
    parser.add_argument("--analyze-only", help="Analyze existing JSON lines file without running queries")
    parser.add_argument("--repeats", type=int, default=5, help="Number of repeats per question (default 5)")
    parser.add_argument("--versions", default="v1.1,v1.2", help="Comma-separated prompt versions (default 'v1.1,v1.2')")
    parser.add_argument("--sleep", type=float, default=2.0, help="Delay in seconds between requests (default 2.0)")

    args = parser.parse_args()
    versions = [v.strip() for v in args.versions.split(",") if v.strip()]

    if args.analyze_only:
        p = Path(args.analyze_only)
        records = []
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                tokens = r.get("tokens", 0)
                explanation = r.get("explanation", "").strip() or r.get("content", "").strip()
                if "model" in r:
                    model = r.get("model", "")
                else:
                    model = "llama-3.3-70b-versatile" if tokens > 0 else ""
                r["model"] = model

                is_llm_error = (
                    tokens == 0
                    or not model
                    or model == "ERROR"
                    or explanation == _DEFAULT_FALLBACK_TEXT.strip()
                    or bool(r.get("error"))
                    or bool(r.get("llm_errored"))
                )
                r["llm_errored"] = is_llm_error
                records.append(r)
        display_summary_tables(records, versions)
        return

    if not args.out:
        parser.error("--out is required when not using --analyze-only")
    asyncio.run(run_measurements(Path(args.out), args.repeats, versions, sleep_delay=args.sleep))


if __name__ == "__main__":
    main()
