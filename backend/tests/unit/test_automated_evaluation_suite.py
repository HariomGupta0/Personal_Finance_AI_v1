"""
Unit test suite verifying the Automated Evaluation Suite.

Ensures that the evaluation suite runs deterministically, assesses all 6 core
evaluation dimensions, and verifies that the machine-readable report is generated
with zero failures and strictly calculated empirical pass rates.
"""
import json
from pathlib import Path
import pytest

from backend.app.evaluation.evaluator import AssistantEvaluator, run_evaluation_suite


def test_evaluator_all_dimensions_pass(tmp_path):
    """
    Execute the automated evaluation suite and verify:
    1. Numerical correctness against the financial engine
    2. Contradiction between explanations and financial statuses
    3. Unsupported amounts, currency hallucinations, and recommendations
    4. Reporting periods and missing data caveats
    5. Prompt injection resistance and cross-user data isolation
    6. Safe fallback responses on failures
    """
    report_file = tmp_path / "test_evaluation_report.json"
    evaluator = AssistantEvaluator()
    report = evaluator.run_all()

    # 1. Total & Pass Rate verification
    assert report["total_tests"] >= 24
    assert report["failed_tests"] == 0
    assert report["passed_tests"] == report["total_tests"]
    assert report["accuracy_percent"] == 100.0

    # 2. Verify all 6 required dimensions are represented and passed
    expected_dimensions = [
        "1_numerical_correctness",
        "2_status_consistency",
        "3_unsupported_claims",
        "4_reporting_periods_missing_data",
        "5_prompt_injection_isolation",
        "6_safe_fallback_handling",
    ]
    breakdown = report["dimension_breakdown"]
    for dim in expected_dimensions:
        assert dim in breakdown, f"Dimension {dim} missing from evaluation breakdown"
        assert breakdown[dim]["total"] > 0
        assert breakdown[dim]["failed"] == 0
        assert breakdown[dim]["accuracy_percent"] == 100.0

    # 3. Verify representative test cases are documented
    assert len(report["representative_test_cases"]) >= 6
    rep_dims = {rc["dimension"] for rc in report["representative_test_cases"]}
    for dim in expected_dimensions:
        assert dim in rep_dims

    # 4. Verify limitations are documented
    assert len(report["limitations"]) >= 4

    # 5. Verify machine-readable export
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    with open(report_file, "r", encoding="utf-8") as f:
        reloaded = json.load(f)
    assert reloaded["accuracy_percent"] == 100.0
    assert len(reloaded["evaluations"]) == report["total_tests"]


def test_evaluator_individual_dimension_runners():
    """Verify individual dimension runner methods can be invoked independently."""
    evaluator = AssistantEvaluator()

    evaluator.evaluate_numerical_correctness()
    assert len(evaluator.evaluations) == 5
    assert all(e["passed"] for e in evaluator.evaluations)

    evaluator.evaluations.clear()
    evaluator.evaluate_status_consistency()
    assert len(evaluator.evaluations) == 4
    assert all(e["passed"] for e in evaluator.evaluations)

    evaluator.evaluations.clear()
    evaluator.evaluate_unsupported_claims()
    assert len(evaluator.evaluations) == 4
    assert all(e["passed"] for e in evaluator.evaluations)

    evaluator.evaluations.clear()
    evaluator.evaluate_reporting_periods_and_missing_data()
    assert len(evaluator.evaluations) == 4
    assert all(e["passed"] for e in evaluator.evaluations)

    evaluator.evaluations.clear()
    evaluator.evaluate_prompt_injection_and_isolation()
    assert len(evaluator.evaluations) == 4
    assert all(e["passed"] for e in evaluator.evaluations)

    evaluator.evaluations.clear()
    evaluator.evaluate_safe_fallback_handling()
    assert len(evaluator.evaluations) == 3
    assert all(e["passed"] for e in evaluator.evaluations)
