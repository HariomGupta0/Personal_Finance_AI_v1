"""
CLI Runner for Personal Finance AI Assistant Automated Evaluation Suite.
"""
import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.evaluation.evaluator import run_evaluation_suite


def main():
    parser = argparse.ArgumentParser(description="Run Automated Evaluation Suite")
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="evaluation_report.json",
        help="Path for machine-readable JSON evaluation report (default: evaluation_report.json)",
    )
    args = parser.parse_args()

    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = PROJECT_ROOT / out_path

    print("==================================================================")
    print(" AUTOMATED EVALUATION SUITE: PERSONAL FINANCE AI ASSISTANT")
    print("==================================================================")
    rep = run_evaluation_suite(output_path=str(out_path))

    print(f" Total Tests Evaluated:  {rep['total_tests']}")
    print(f" Tests Passed:           {rep['passed_tests']}")
    print(f" Tests Failed:           {rep['failed_tests']}")
    print(f" Empirical Accuracy:     {rep['accuracy_percent']}%")
    print("------------------------------------------------------------------")
    print(" DIMENSION BREAKDOWN:")
    for dim_name, d_stat in rep["dimension_breakdown"].items():
        print(f"  • {dim_name:35s}: {d_stat['passed']}/{d_stat['total']} passed ({d_stat['accuracy_percent']}%)")
    print("==================================================================")
    print(f" Machine-readable report saved to: {out_path}\n")

    if rep["failed_tests"] > 0:
        print("FAILURES DETECTED:")
        for ev in rep["evaluations"]:
            if not ev["passed"]:
                print(f"  [{ev['test_id']}] {ev['name']}: {ev['failure_reason']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
