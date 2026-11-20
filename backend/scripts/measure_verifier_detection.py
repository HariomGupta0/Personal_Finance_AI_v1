"""
Deterministic Verifier Detection Rate Benchmark.

Runs controlled mutations across all 8 real fixtures in backend/tests/fixtures/verifier/
without making any external LLM calls.

Mutations evaluated:
  - amount +1
  - amount +1000
  - amount x10
  - percent +1 point
  - duration changed
  - status label flipped
  - grade changed
  - safe/not-safe flipped
  - invented amount in Smart Insights (should be caught BLOCKING)
  - invented amount in What You Should Do Next (should be caught ADVISORY)
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

from decimal import Decimal
import json
from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.services.verifier import verify_explanation, split_sections

FIXTURES_DIR = REPO_ROOT / "backend" / "tests" / "fixtures" / "verifier"


def run_detection_benchmark():
    fixtures = []
    for p in sorted(FIXTURES_DIR.glob("q*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        ev = json.loads(d["evidence_string"]) if "evidence_string" in d else d.get("math_result", {})
        fixtures.append({
            "name": p.name,
            "raw_text": d["llm_raw_text"],
            "evidence": ev,
            "intent": d.get("intent"),
        })

    mutation_types = [
        "amount +1",
        "amount +1000",
        "amount x10",
        "percent +1 point",
        "duration changed",
        "status label flipped",
        "grade changed",
        "safe/not-safe flipped",
        "invented amount in Smart Insights",
        "invented amount in What You Should Do Next",
    ]

    stats = {
        m: {"generated": 0, "caught_blocking": 0, "caught_advisory": 0, "missed": 0, "misses": []}
        for m in mutation_types
    }

    for f in fixtures:
        raw = f["raw_text"]
        ev = f["evidence"]
        intent = f["intent"]
        baseline_res = verify_explanation(raw, ev, intent=intent)
        base_violation_types = {(v.get("type"), v.get("found")) for v in baseline_res["violations"]}
        base_advisory_types = {(a.get("type"), a.get("found")) for a in baseline_res["advisory"]}

        def eval_mut(mtype, mutated_text, target_sentence, expect_advisory=False):
            stats[mtype]["generated"] += 1
            res = verify_explanation(mutated_text, ev, intent=intent)

            new_violations = [
                v for v in res["violations"]
                if (v.get("type"), v.get("found")) not in base_violation_types
            ]
            new_advisories = [
                a for a in res["advisory"]
                if (a.get("type"), a.get("found")) not in base_advisory_types
            ]

            if expect_advisory:
                if new_advisories:
                    stats[mtype]["caught_advisory"] += 1
                elif new_violations:
                    stats[mtype]["caught_blocking"] += 1
                else:
                    stats[mtype]["missed"] += 1
                    stats[mtype]["misses"].append((f["name"], target_sentence))
            else:
                if new_violations:
                    stats[mtype]["caught_blocking"] += 1
                elif new_advisories:
                    stats[mtype]["caught_advisory"] += 1
                else:
                    stats[mtype]["missed"] += 1
                    stats[mtype]["misses"].append((f["name"], target_sentence))

        # 1. amount +1
        m_amt = re.search(r"₹\s*([0-9,]+)", raw)
        if m_amt:
            amt_str = m_amt.group(1)
            amt_int = int(amt_str.replace(",", ""))
            mut_amt = f"₹{amt_int + 1:,}"
            mut_text = raw[:m_amt.start()] + mut_amt + raw[m_amt.end():]
            sent = raw[max(0, m_amt.start() - 30):min(len(raw), m_amt.end() + 30)].strip()
            eval_mut("amount +1", mut_text, sent)

        # 2. amount +1000
        if m_amt:
            amt_str = m_amt.group(1)
            amt_int = int(amt_str.replace(",", ""))
            mut_amt = f"₹{amt_int + 1000:,}"
            mut_text = raw[:m_amt.start()] + mut_amt + raw[m_amt.end():]
            sent = raw[max(0, m_amt.start() - 30):min(len(raw), m_amt.end() + 30)].strip()
            eval_mut("amount +1000", mut_text, sent)

        # 3. amount x10 (if 0, change to 10,000)
        if m_amt:
            amt_str = m_amt.group(1)
            amt_int = int(amt_str.replace(",", ""))
            mut_val = (amt_int * 10) if amt_int > 0 else 10000
            mut_amt = f"₹{mut_val:,}"
            mut_text = raw[:m_amt.start()] + mut_amt + raw[m_amt.end():]
            sent = raw[max(0, m_amt.start() - 30):min(len(raw), m_amt.end() + 30)].strip()
            eval_mut("amount x10", mut_text, sent)

        # 4. percent +1 point
        m_pct = re.search(r"([0-9.]+)\s*%", raw)
        if m_pct:
            pct_val = float(m_pct.group(1))
            mut_pct = f"{pct_val + 1.0:.1f}%"
            mut_text = raw[:m_pct.start()] + mut_pct + raw[m_pct.end():]
            sent = raw[max(0, m_pct.start() - 30):min(len(raw), m_pct.end() + 30)].strip()
            eval_mut("percent +1 point", mut_text, sent)

        # 5. duration changed
        m_dur = re.search(r"\b([0-9.]+)\s*(?:‑|-|\s*)months?\b", raw, re.IGNORECASE)
        if m_dur:
            dur_val = float(m_dur.group(1))
            mut_dur = f"{dur_val + 4.0:.1f} months"
            mut_text = raw[:m_dur.start()] + mut_dur + raw[m_dur.end():]
            sent = raw[max(0, m_dur.start() - 30):min(len(raw), m_dur.end() + 30)].strip()
            eval_mut("duration changed", mut_text, sent)

        # 6. status label flipped
        if "HIGH" in raw:
            mut_text = raw.replace("HIGH", "LOW")
            eval_mut("status label flipped", mut_text, "Risk level: LOW")
        elif "INSUFFICIENT" in raw:
            mut_text = raw.replace("INSUFFICIENT", "STRONG")
            eval_mut("status label flipped", mut_text, "Buffer health: STRONG")
        elif "SAFE" in raw:
            mut_text = raw.replace("SAFE", "NOT_SAFE")
            eval_mut("status label flipped", mut_text, "Decision: NOT_SAFE")

        # 7. grade changed
        m_grd = re.search(r"\bGrade\s+([A-D])\b", raw, re.IGNORECASE)
        if m_grd:
            cur_grd = m_grd.group(1).upper()
            flipped_grd = "B" if cur_grd == "A" else "A"
            mut_text = raw[:m_grd.start()] + f"Grade {flipped_grd}" + raw[m_grd.end():]
            sent = raw[max(0, m_grd.start() - 30):min(len(raw), m_grd.end() + 30)].strip()
            eval_mut("grade changed", mut_text, sent)
        elif ev.get("grade"):
            mut_text = raw.replace("### The Quick Take\n", "### The Quick Take\nYou earned a Grade F on your report.\n")
            eval_mut("grade changed", mut_text, "You earned a Grade F on your report.")

        # 8. safe/not-safe flipped
        dec = ev.get("decision")
        if dec == "NOT_SAFE":
            mut_text = raw.replace("not a financially safe move", "this purchase is completely safe")
            if mut_text == raw:
                mut_text = raw + "\nThis purchase is safe.\n"
            eval_mut("safe/not-safe flipped", mut_text, "this purchase is completely safe")
        elif dec == "SAFE":
            mut_text = raw + "\nThis purchase is not safe.\n"
            eval_mut("safe/not-safe flipped", mut_text, "this purchase is not safe")

        # 9. invented amount in Smart Insights
        sec_m = re.search(r"(?:\*\*|###)?\s*(?:💡)?\s*(?:\*\*)?\s*Smart Insights(?:\*\*)?", raw, re.IGNORECASE)
        if sec_m:
            insert_pos = sec_m.end()
            mut_text = raw[:insert_pos] + "\n- You have an unverified surplus of ₹99,876 this month.\n" + raw[insert_pos:]
            eval_mut("invented amount in Smart Insights", mut_text, "- You have an unverified surplus of ₹99,876 this month.")

        # 10. invented amount in What You Should Do Next
        sec_next = re.search(r"(?:\*\*|###)?\s*(?:🚀)?\s*(?:\*\*)?\s*What You Should Do Next(?:\*\*)?", raw, re.IGNORECASE)
        if sec_next:
            insert_pos = sec_next.end()
            mut_text = raw[:insert_pos] + "\n1. Consider setting aside ₹99,876 for emergency reserves.\n" + raw[insert_pos:]
            eval_mut("invented amount in What You Should Do Next", mut_text, "1. Consider setting aside ₹99,876 for emergency reserves.", expect_advisory=True)

    # Print Report Table
    print("=" * 95)
    print("VERIFIER DETECTION BENCHMARK REPORT (CONTROLLED MUTATIONS)")
    print("=" * 95)
    print(
        f"{'Mutation Type':<42} | {'Generated':<10} | {'Blocking':<10} | {'Advisory':<10} | {'Missed':<8}"
    )
    print("-" * 95)

    total_gen = sum(s["generated"] for s in stats.values())
    total_blk = sum(s["caught_blocking"] for s in stats.values())
    total_adv = sum(s["caught_advisory"] for s in stats.values())
    total_mis = sum(s["missed"] for s in stats.values())

    for mtype in mutation_types:
        s = stats[mtype]
        print(
            f"{mtype:<42} | {s['generated']:<10} | {s['caught_blocking']:<10} | {s['caught_advisory']:<10} | {s['missed']:<8}"
        )

    print("-" * 95)
    print(
        f"{'TOTAL':<42} | {total_gen:<10} | {total_blk:<10} | {total_adv:<10} | {total_mis:<8}"
    )
    print("=" * 95)

    if total_mis > 0:
        print("\nMISSED MUTATIONS LIST:")
        for mtype in mutation_types:
            for fname, sent in stats[mtype]["misses"]:
                print(f"  - [{mtype}] in {fname}: \"{sent}\"")
    else:
        print("\nMISSED MUTATIONS LIST: None (100% detection rate)")


if __name__ == "__main__":
    run_detection_benchmark()
