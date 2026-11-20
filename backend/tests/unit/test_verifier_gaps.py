"""
Tests for verifier hardening and gap closures.

Covers:
  2a: Grade check (Grade X, grade of X, Health Grade: X, grade: X with X in A-D)
  2b: Extended money extractor (INR prefix, rupees/rs suffix, k/thousand/lakh/lac/crore/cr, leading minus, ranges)
  2c: Proximity label checks (case-insensitive with anchor words within 2 tokens)
  2d: Decision contradiction detection on PURCHASE_SAFETY
"""

from decimal import Decimal
import json
from pathlib import Path
import pytest

from backend.app.services.verifier import (
    verify_explanation,
    extract_allowed_values,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "verifier"


def test_grade_check_wrong_grade_flags_violation():
    evidence = {"grade": "B", "current_balance": 50000.0}
    text = """
    ### The Quick Take
    You received a Grade A on your financial health check.

    ### The Numbers
    • Balance: ₹50,000

    ### Smart Insights
    Everything looks fine.

    ### What You Should Do Next
    Keep it up.
    """
    res = verify_explanation(text, evidence)
    assert res.verified is False
    violations = [v for v in res["violations"] if v.get("type") == "WRONG_LABEL"]
    assert len(violations) >= 1
    assert any("Grade A" in v.get("found", "") or v.get("found") == "A" for v in violations)


def test_grade_check_correct_grade_passes():
    evidence = {"grade": "A", "current_balance": 50000.0}
    text = """
    ### The Quick Take
    You received a Grade A on your financial health check.

    ### The Numbers
    • Balance: ₹50,000

    ### Smart Insights
    Everything looks fine.

    ### What You Should Do Next
    Keep it up.
    """
    res = verify_explanation(text, evidence)
    assert res.verified is True
    assert not any(v.get("type") == "WRONG_LABEL" for v in res["violations"])


def test_grade_check_plan_a_and_purchase_not_flagged():
    evidence = {"grade": "B", "current_balance": 50000.0, "purchase_amount": 5000.0}
    text = """
    ### The Quick Take
    A purchase of ₹5,000 is under consideration for Plan A.

    ### The Numbers
    • Balance: ₹50,000
    • Purchase: ₹5,000

    ### Smart Insights
    Option A looks reasonable.

    ### What You Should Do Next
    Proceed with Plan A.
    """
    res = verify_explanation(text, evidence)
    assert res.verified is True
    assert not any(v.get("type") == "WRONG_LABEL" for v in res["violations"])


def test_money_extractor_inr_prefix_ok():
    evidence = {"current_balance": 45000.0}
    text = """
    ### The Quick Take
    Your balance is INR 45,000.

    ### The Numbers
    • Balance: INR 45,000

    ### Smart Insights
    Healthy position.

    ### What You Should Do Next
    Save more.
    """
    res = verify_explanation(text, evidence)
    assert res.verified is True
    assert len(res["violations"]) == 0


def test_money_extractor_rupees_suffix_ok():
    evidence = {"current_balance": 45000.0}
    text = """
    ### The Quick Take
    You have 45000 rupees in your account.

    ### The Numbers
    • Balance: 45000 rupees

    ### Smart Insights
    Healthy position.

    ### What You Should Do Next
    Save more.
    """
    res = verify_explanation(text, evidence)
    assert res.verified is True
    assert len(res["violations"]) == 0


def test_money_extractor_lakh_multiplier():
    evidence = {"current_balance": 120000.0}
    text = """
    ### The Quick Take
    You have ₹1.2 lakh saved up.

    ### The Numbers
    • Balance: ₹1.2 lakh

    ### Smart Insights
    Healthy position.

    ### What You Should Do Next
    Save more.
    """
    res = verify_explanation(text, evidence)
    assert res.verified is True
    assert len(res["violations"]) == 0


def test_money_extractor_unsupported_amount_is_violation():
    evidence = {"current_balance": 45000.0}
    text = """
    ### The Quick Take
    You have ₹45,001 in your account.

    ### The Numbers
    • Balance: ₹45,001

    ### Smart Insights
    Healthy position.

    ### What You Should Do Next
    Save more.
    """
    res = verify_explanation(text, evidence)
    assert res.verified is False
    assert any(v.get("type") == "unsupported_amount" for v in res["violations"])


def test_money_extractor_unsupported_rupees_suffix_is_violation():
    evidence = {"current_balance": 40000.0}
    text = """
    ### The Quick Take
    You have 45,000 rupees in your account.

    ### The Numbers
    • Balance: 45,000 rupees

    ### Smart Insights
    Healthy position.

    ### What You Should Do Next
    Save more.
    """
    res = verify_explanation(text, evidence)
    assert res.verified is False
    assert any(v.get("type") == "unsupported_amount" for v in res["violations"])


def test_label_proximity_mutations_high_to_low_risk():
    # Load q1 fixture where risk_level is HIGH
    with open(FIXTURES_DIR / "q1_purchase_safety.json", "r", encoding="utf-8") as f:
        d = json.load(f)
    ev_obj = json.loads(d["evidence_string"])
    raw_text = d["llm_raw_text"]

    # Mutate to say 'low risk' in prose
    mutated_text = raw_text.replace("low‑risk", "low risk").replace("low-risk", "low risk")
    if "low risk" not in mutated_text.lower():
        mutated_text = mutated_text.replace("not a financially safe move", "this is a low risk move")

    res = verify_explanation(mutated_text, ev_obj, intent=d["intent"])
    assert res.verified is False
    assert any(v.get("type") in ("WRONG_LABEL", "CONTRADICTION") for v in res["violations"])


def test_label_proximity_mutations_insufficient_to_strong_runway():
    # Load q4 fixture where buffer health is INSUFFICIENT
    with open(FIXTURES_DIR / "q4_emergency_runway.json", "r", encoding="utf-8") as f:
        d = json.load(f)
    ev_obj = json.loads(d["evidence_string"])
    raw_text = d["llm_raw_text"]

    mutated_text = raw_text.replace("INSUFFICIENT", "STRONG").replace("insufficient", "STRONG")
    res = verify_explanation(mutated_text, ev_obj, intent=d["intent"])
    assert res.verified is False
    wrong_labels = [v for v in res["violations"] if v.get("type") == "WRONG_LABEL"]
    assert len(wrong_labels) >= 1
    assert any("STRONG" in v.get("found", "") for v in wrong_labels)


def test_decision_contradiction_purchase_safety():
    with open(FIXTURES_DIR / "q1_purchase_safety.json", "r", encoding="utf-8") as f:
        d = json.load(f)
    ev_obj = json.loads(d["evidence_string"])
    raw_text = d["llm_raw_text"]

    # In q1, decision is NOT_SAFE. Mutate to say "this purchase is safe"
    mutated = raw_text.replace("it’s not a financially safe move right now.", "this purchase is safe.")
    res = verify_explanation(mutated, ev_obj, intent="PURCHASE_SAFETY")
    assert res.verified is False
    assert any(v.get("type") == "CONTRADICTION" for v in res["violations"])


def test_money_extractor_boundary_false_positives():
    from backend.app.services.verifier import extract_money_tokens

    # Verify extract_money_tokens behavior
    assert extract_money_tokens("₹39,000 keeps growing") == [("₹39,000", Decimal("39000"))]
    assert extract_money_tokens("₹20,000 kept aside") == [("₹20,000", Decimal("20000"))]
    assert extract_money_tokens("₹10,000 credited to you") == [("₹10,000", Decimal("10000"))]
    assert extract_money_tokens("₹5,000 lacking") == [("₹5,000", Decimal("5000"))]
    assert extract_money_tokens("over the years 2 months") == []

    # Verify verify_explanation produces NO violation on each phrase
    evidence = {
        "amounts": [39000, 10000, 5000, 20000],
        "duration": 2,
    }

    phrases = [
        "₹39,000 keeps growing",
        "₹20,000 kept aside",
        "₹10,000 credited to you",
        "₹5,000 lacking",
        "over the years 2 months",
    ]

    for p in phrases:
        text = f"### The Quick Take\n{p}\n\n### The Numbers\n• Details\n\n### Smart Insights\nNote\n\n### What You Should Do Next\nAction"
        res = verify_explanation(text, evidence)
        assert len(res["violations"]) == 0, f"Expected no violation for '{p}', got: {res['violations']}"


def test_money_extractor_valid_units_still_work():
    from backend.app.services.verifier import extract_money_tokens

    tokens1 = extract_money_tokens("₹1.2 lakh")
    assert len(tokens1) == 1 and tokens1[0][1] == Decimal("120000")

    tokens2 = extract_money_tokens("₹2k")
    assert len(tokens2) == 1 and tokens2[0][1] == Decimal("2000")

    tokens3 = extract_money_tokens("₹3 crore")
    assert len(tokens3) == 1 and tokens3[0][1] == Decimal("30000000")

    tokens4 = extract_money_tokens("INR 45,000")
    assert len(tokens4) == 1 and tokens4[0][1] == Decimal("45000")

    tokens5 = extract_money_tokens("45000 rupees")
    assert len(tokens5) == 1 and tokens5[0][1] == Decimal("45000")


def test_contradiction_negation_whole_word_checks():
    evidence = {"decision": "NOT_SAFE"}

    # Must be flagged as CONTRADICTION
    for claimed_safe in [
        "in another case this purchase is safe",
        "an unexpected bill, but this purchase is safe",
    ]:
        text = f"### The Quick Take\n{claimed_safe}.\n\n### The Numbers\n• Info\n\n### Smart Insights\nNote\n\n### What You Should Do Next\nAction"
        res = verify_explanation(text, evidence)
        contra = [v for v in res["violations"] if v.get("type") == "CONTRADICTION"]
        assert len(contra) >= 1, f"Expected CONTRADICTION for '{claimed_safe}', got {res['violations']}"

    # Must NOT be flagged as CONTRADICTION
    for not_claimed_safe in [
        "this purchase is not safe",
        "it would be unsafe to buy",
    ]:
        text = f"### The Quick Take\n{not_claimed_safe}.\n\n### The Numbers\n• Info\n\n### Smart Insights\nNote\n\n### What You Should Do Next\nAction"
        res = verify_explanation(text, evidence)
        contra = [v for v in res["violations"] if v.get("type") == "CONTRADICTION"]
        assert len(contra) == 0, f"Expected no CONTRADICTION for '{not_claimed_safe}', got {contra}"


