"""
Automated Evaluation Suite for Personal Finance AI Assistant.

Provides deterministic benchmarking, contradiction detection, hallucination checks,
missing data caveat verification, prompt injection defense, and fallback resilience.
"""
from backend.app.evaluation.synthetic_dataset import SYNTHETIC_PROFILES
from backend.app.evaluation.evaluator import AssistantEvaluator, run_evaluation_suite

__all__ = ["SYNTHETIC_PROFILES", "AssistantEvaluator", "run_evaluation_suite"]
