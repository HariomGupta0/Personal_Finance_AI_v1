"""
Unit tests for the Numeric Verifier using real captured pipeline fixtures.

Verifies:
  1. Exact assertions on all 8 real fixtures (verified bool, blocking violations, advisory list).
  2. Byte-identical stability of Prompt v1.1 against pre-change snapshot.
  3. Prompt v1.2 difference strictly restricted to Rule 7.
  4. Pipeline retry / fallback handling on blocking violations.
"""

from decimal import Decimal
import json
from pathlib import Path
import pytest

from backend.app.services.verifier import (
    verify_explanation,
    ALWAYS_ALLOWED,
    ENUM_VOCAB,
    VERIFICATION_SCOPE,
)
from backend.app.services.prompt_builder import (
    build_financial_explanation_prompt,
    PROMPT_REGISTRY,
)
from backend.app.services.response_generator import build_deterministic_fallback

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "verifier"


def test_constants_definitions():
    """Verify named constant ALWAYS_ALLOWED and ENUM_VOCAB vocabulary definitions."""
    assert ALWAYS_ALLOWED["duration"] == {Decimal("3")}
    assert "SAFE" in ENUM_VOCAB
    assert "NOT_SAFE" in ENUM_VOCAB
    assert "HIGH" in ENUM_VOCAB
    assert "LOW" in ENUM_VOCAB
    assert "A" in ENUM_VOCAB
    assert "D" in ENUM_VOCAB
    # Confirm only A, B, C, D are grades
    for letter in ("A+", "A-", "B+", "F"):
        assert letter not in ENUM_VOCAB


def test_q1_purchase_safety():
    with open(FIXTURES_DIR / "q1_purchase_safety.json", "r", encoding="utf-8") as f:
        d = json.load(f)
    ev_obj = json.loads(d["evidence_string"])
    res = verify_explanation(d["llm_raw_text"], ev_obj, intent=d["intent"])

    assert res.verified is True
    assert res["verified"] is True
    assert res["violations"] == []
    assert res["advisory_count"] == 1
    assert res["advisory"] == [
        {
            "type": "unsupported_amount",
            "found": "₹5,000",
            "section": "What You Should Do Next",
        }
    ]
    assert res["scope"] == VERIFICATION_SCOPE


def test_q2_savings_rate():
    with open(FIXTURES_DIR / "q2_savings_rate.json", "r", encoding="utf-8") as f:
        d = json.load(f)
    ev_obj = json.loads(d["evidence_string"])
    res = verify_explanation(d["llm_raw_text"], ev_obj, intent=d["intent"])

    assert res.verified is False
    assert res["verified"] is False
    assert len(res["violations"]) == 2
    assert res["violations"][0]["type"] == "unsupported_percent"
    assert res["violations"][0]["found"] == "30%"
    assert res["violations"][0]["section"] == "Smart Insights"
    assert res["violations"][1]["type"] == "unsupported_percent"
    assert res["violations"][1]["found"] == "35%"
    assert res["violations"][1]["section"] == "Smart Insights"
    assert res["advisory"] == []
    assert res["advisory_count"] == 0


def test_q3_category_expense():
    with open(FIXTURES_DIR / "q3_category_expense.json", "r", encoding="utf-8") as f:
        d = json.load(f)
    ev_obj = json.loads(d["evidence_string"])
    res = verify_explanation(d["llm_raw_text"], ev_obj, intent=d["intent"])

    assert res.verified is True
    assert res["verified"] is True
    assert res["violations"] == []
    assert res["advisory_count"] == 1
    assert res["advisory"] == [
        {
            "type": "unsupported_percent",
            "found": "15%",
            "section": "What You Should Do Next",
        }
    ]


def test_q4_emergency_runway():
    with open(FIXTURES_DIR / "q4_emergency_runway.json", "r", encoding="utf-8") as f:
        d = json.load(f)
    ev_obj = json.loads(d["evidence_string"])
    res = verify_explanation(d["llm_raw_text"], ev_obj, intent=d["intent"])

    assert res.verified is True
    assert res["verified"] is True
    assert res["violations"] == []
    assert res["advisory_count"] == 1
    assert res["advisory"] == [
        {
            "type": "unsupported_amount",
            "found": "₹63,000",
            "section": "What You Should Do Next",
        }
    ]


def test_q4_survive_savings_literal():
    with open(FIXTURES_DIR / "q4_survive_savings_literal.json", "r", encoding="utf-8") as f:
        d = json.load(f)
    ev_obj = json.loads(d["evidence_string"])
    res = verify_explanation(d["llm_raw_text"], ev_obj, intent=d["intent"])

    assert res.verified is False
    assert res["verified"] is False
    assert len(res["violations"]) == 1
    assert res["violations"][0]["type"] == "unsupported_duration"
    assert res["violations"][0]["found"] == "1.86 months"
    assert res["violations"][0]["section"] == "Smart Insights"
    assert res["advisory_count"] == 4
    advisory_founds = [a["found"] for a in res["advisory"]]
    assert "₹63,000" in advisory_founds
    assert "₹126,000" in advisory_founds
    assert "6 months" in advisory_founds


def test_q5_debt_to_income():
    with open(FIXTURES_DIR / "q5_debt_to_income.json", "r", encoding="utf-8") as f:
        d = json.load(f)
    ev_obj = json.loads(d["evidence_string"])
    res = verify_explanation(d["llm_raw_text"], ev_obj, intent=d["intent"])

    assert res.verified is False
    assert res["verified"] is False
    assert len(res["violations"]) == 1
    assert res["violations"][0]["type"] == "unsupported_percent"
    assert res["violations"][0]["found"] == "83%"
    assert res["violations"][0]["section"] == "Smart Insights"
    assert res["advisory_count"] == 1
    assert res["advisory"][0]["type"] == "unsupported_duration"
    assert res["advisory"][0]["found"] == "6 months"
    assert res["advisory"][0]["section"] == "What You Should Do Next"


def test_q6_financial_health():
    with open(FIXTURES_DIR / "q6_financial_health.json", "r", encoding="utf-8") as f:
        d = json.load(f)
    ev_obj = json.loads(d["evidence_string"])
    res = verify_explanation(d["llm_raw_text"], ev_obj, intent=d["intent"])

    assert res.verified is True
    assert res["verified"] is True
    assert res["violations"] == []
    assert res["advisory_count"] == 2
    advisory_founds = [a["found"] for a in res["advisory"]]
    assert "₹50,000" in advisory_founds
    assert "5%" in advisory_founds


def test_q7_period_comparison():
    with open(FIXTURES_DIR / "q7_period_comparison.json", "r", encoding="utf-8") as f:
        d = json.load(f)
    ev_obj = json.loads(d["evidence_string"])
    res = verify_explanation(d["llm_raw_text"], ev_obj, intent=d["intent"])

    assert res.verified is False
    assert res["verified"] is False
    assert len(res["violations"]) == 1
    assert res["violations"][0]["type"] == "unsupported_percent"
    assert res["violations"][0]["found"] == "33%"
    assert res["violations"][0]["section"] == "Smart Insights"
    assert res["advisory_count"] == 0


def test_prompt_v1_1_snapshot_byte_identical_and_v1_2_diff():
    """Confirm v1.1 is byte-identical to pre-change snapshot, and v1.2 differs only by Rule 7."""
    snapshot_path = FIXTURES_DIR / "prompt_v11_snapshot.json"
    with open(snapshot_path, "r", encoding="utf-8") as f:
        snapshot = json.load(f)

    rule7 = (
        "7. NUMBERS: Use ONLY numbers that appear in <financial_evidence>, written exactly as they appear. "
        "Never introduce new numbers, percentages, benchmarks, targets, or ranges, and never compute derived "
        "values (sums, differences, complements, multiples, runway) in any section, including next steps. "
        "Use qualitative wording instead.\n"
    )

    for fname, sdata in snapshot.items():
        fp = FIXTURES_DIR / fname
        with open(fp, "r", encoding="utf-8") as f:
            d = json.load(f)
        ev_obj = json.loads(d["evidence_string"])
        q = sdata["question"]

        rendered_v11 = build_financial_explanation_prompt(ev_obj, question=q, version="v1.1")
        assert rendered_v11 == sdata["prompt_v1_1"], f"v1.1 prompt changed for {fname}"

        rendered_v12 = build_financial_explanation_prompt(ev_obj, question=q, version="v1.2")
        assert rule7 in rendered_v12, f"Rule 7 missing in v1.2 for {fname}"

        normalized_v12 = rendered_v12.replace(rule7, "")
        assert normalized_v12 == rendered_v11, f"v1.2 differs by more than Rule 7 for {fname}"


def test_fallback_replaces_blocking_violation():
    """Verify that when a blocking violation occurs, deterministic fallback passes verifier."""
    # Using math result from q2 (savings rate)
    with open(FIXTURES_DIR / "q2_savings_rate.json", "r", encoding="utf-8") as f:
        d = json.load(f)
    math_res = d["math_result"]
    ev_obj = json.loads(d["evidence_string"])

    # Fallback response
    fallback_text = build_deterministic_fallback(math_res)
    fallback_ver = verify_explanation(fallback_text, ev_obj, intent="SAVINGS_ANALYSIS")

    assert fallback_ver.verified is True
    assert fallback_ver["violations"] == []
