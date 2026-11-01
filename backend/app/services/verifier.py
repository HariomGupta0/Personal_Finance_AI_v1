"""
Deterministic Numeric and Factual Verifier.

Audits LLM-generated explanations against deterministic financial engine results.
Enforces a two-tier policy:
  - BLOCKING: Unsupported financial metrics in Quick Take, The Numbers, or Smart Insights;
              any decision contradiction or wrong label in any section.
  - ADVISORY: Unsupported metrics in 'What You Should Do Next' (advisory heuristics).

Scope statement:
  claims in Quick Take/Numbers/Insights and all status labels; numbers in next-steps advice are listed as advisory, not blocked
"""

from decimal import Decimal, InvalidOperation
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Named constant: standard 3-month emergency reserve multiplier allowed globally
ALWAYS_ALLOWED = {
    "duration": {Decimal("3")},
}

# Engine vocabulary: exact status, decision, risk, and grade labels emitted by financial_engine.py
ENUM_VOCAB = {
    # Purchase safety decision
    "SAFE",
    "NOT_SAFE",
    # Risk levels
    "LOW",
    "MEDIUM",
    "HIGH",
    "VERY_HIGH",
    "MODERATE",
    "CRITICAL",
    # Runway statuses
    "STRONG",
    "HEALTHY",
    "INSUFFICIENT",
    # Savings statuses
    "EXCELLENT",
    "GOOD",
    "FAIR",
    "POOR",
    # Financial health grades (A, B, C, D only)
    "A",
    "B",
    "C",
    "D",
    # Category spend audit
    "CONFIRMED_SPEND",
    "CONFIRMED_ZERO",
    "DATA_UNAVAILABLE",
    # Spending trends
    "UPWARD",
    "DOWNWARD",
    "STABLE",
    "INSUFFICIENT_DATA",
    # Period comparison
    "VALID",
    "BASELINE_ZERO",
}

MULTI_LETTER_ENUMS = {e for e in ENUM_VOCAB if len(e) > 1}
ANCHOR_WORDS = {"risk", "rating", "status", "level", "health", "buffer"}

MONEY_UNITS = {
    "k": Decimal("1000"),
    "thousand": Decimal("1000"),
    "thousands": Decimal("1000"),
    "lakh": Decimal("100000"),
    "lakhs": Decimal("100000"),
    "lac": Decimal("100000"),
    "lacs": Decimal("100000"),
    "cr": Decimal("10000000"),
    "crore": Decimal("10000000"),
    "crores": Decimal("10000000"),
}

SECTION_PATTERNS = [
    ("Quick Take", r"(?:\*\*|###)?\s*(?:🎯)?\s*(?:\*\*)?\s*The Quick Take(?:\*\*)?"),
    ("The Numbers", r"(?:\*\*|###)?\s*(?:📊)?\s*(?:\*\*)?\s*The Numbers(?:\*\*)?"),
    ("Smart Insights", r"(?:\*\*|###)?\s*(?:💡)?\s*(?:\*\*)?\s*Smart Insights(?:\*\*)?"),
    ("What You Should Do Next", r"(?:\*\*|###)?\s*(?:🚀)?\s*(?:\*\*)?\s*What You Should Do Next(?:\*\*)?"),
]

VERIFICATION_SCOPE = "claims in Quick Take/Numbers/Insights and all status labels; numbers in next-steps advice are listed as advisory, not blocked"


class VerificationResult(dict):
    """Structured dictionary holding verification outcomes with truthy semantics."""

    @property
    def verified(self) -> bool:
        return bool(self.get("verified", False))

    def __bool__(self) -> bool:
        return self.verified


def split_sections(text: str) -> dict[str, str]:
    """
    Split explanation into the 4 standard executive sections.
    Tolerates emoji, markdown bold/header markers, and slight spacing variations.
    If the text cannot be split into all 4 sections, returns {'WHOLE_TEXT': text}.
    """
    if not text or not text.strip():
        return {"WHOLE_TEXT": ""}

    matches = []
    for name, pat in SECTION_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            matches.append((m.start(), m.end(), name))

    matches.sort()
    if len(matches) != 4:
        return {"WHOLE_TEXT": text}

    return {
        "Quick Take": text[matches[0][1]:matches[1][0]].strip(),
        "The Numbers": text[matches[1][1]:matches[2][0]].strip(),
        "Smart Insights": text[matches[2][1]:matches[3][0]].strip(),
        "What You Should Do Next": text[matches[3][1]:].strip(),
    }


def extract_allowed_values(financial_result: dict | Any) -> dict[str, set]:
    """
    Extract all authoritative values from the deterministic financial result / evidence.
    """
    allowed = {
        "money": set(),
        "percent": set(),
        "duration": set(ALWAYS_ALLOWED["duration"]),
        "label": set(),
    }

    def _walk(o):
        if isinstance(o, bool):
            return
        elif isinstance(o, (int, float)):
            d = Decimal(str(o))
            allowed["money"].add(d)
            allowed["percent"].add(d)
            allowed["duration"].add(d)
        elif isinstance(o, str):
            # Check for allowed status words / letters
            for word in re.findall(r"\b[A-Za-z0-9_+-]+\b", o):
                up = word.upper()
                if up in ENUM_VOCAB:
                    allowed["label"].add(up)
            # Check for currency amounts
            for m in re.findall(r"₹\s*([0-9,]+(?:\.[0-9]+)?)", o):
                try:
                    allowed["money"].add(Decimal(m.replace(",", "")))
                except InvalidOperation:
                    pass
            # Check for percentages
            for m in re.findall(r"([0-9.]+)\s*%", o):
                try:
                    allowed["percent"].add(Decimal(m))
                except InvalidOperation:
                    pass
            # Check for durations
            for m in re.findall(r"\b([0-9.]+)\s*(?:‑|-|\s*)months?\b", o, re.IGNORECASE):
                try:
                    allowed["duration"].add(Decimal(m))
                except InvalidOperation:
                    pass
            # Generic numbers (e.g. 90.0 / 100)
            for m in re.findall(r"\b([0-9]+(?:\.[0-9]+)?)\b", o.replace(",", "")):
                try:
                    d = Decimal(m)
                    allowed["money"].add(d)
                    allowed["percent"].add(d)
                    allowed["duration"].add(d)
                except InvalidOperation:
                    pass
        elif isinstance(o, dict):
            for k, v in o.items():
                if k in ("decision", "risk_level", "grade", "status", "trend_direction"):
                    if isinstance(v, str):
                        allowed["label"].add(v.upper())
                _walk(v)
        elif isinstance(o, list):
            for item in o:
                _walk(item)

    if hasattr(financial_result, "model_dump") and callable(financial_result.model_dump):
        _walk(financial_result.model_dump())
    elif isinstance(financial_result, dict):
        _walk(financial_result)

    return allowed


def matches_with_tolerance(shown_str: str, allowed_set: set[Decimal]) -> bool:
    """
    Check if shown percent or duration matches an allowed value within:
      |shown - allowed| <= 0.5 * 10^(-d)
    where d is the number of decimal digits written in shown_str.
    """
    if "." in shown_str:
        d = len(shown_str.split(".")[1])
    else:
        d = 0
    tolerance = Decimal("0.5") * (Decimal("10") ** (-d))

    try:
        val = Decimal(shown_str)
        return any(abs(val - allowed) <= tolerance for allowed in allowed_set)
    except InvalidOperation:
        return False


def extract_money_tokens(text: str) -> list[tuple[str, Decimal]]:
    """
    Extract currency amounts supporting INR prefix, rupees/rs suffix,
    k/thousand/lakh/lac/crore/cr multipliers, leading minus, and ranges.
    Returns list of (found_string, Decimal_value).
    """
    results = []
    p1 = re.compile(
        r"(?P<prefix_sign>-)?(?:\bINR\b|₹|\bRs\.?)\s*(?P<inner_sign>-)?\s*(?P<num>[0-9,]+(?:\.[0-9]+)?)\s*(?P<unit>(?:thousand|thousands|k|lakhs?|lacs?|crores?|cr)\b)?(?:\s*(?:rupees?|\brs\.?)\b)?",
        re.IGNORECASE,
    )
    p2 = re.compile(
        r"(?P<prefix_sign>-)?\b(?P<num>[0-9,]+(?:\.[0-9]+)?)\s*(?P<unit>(?:thousand|thousands|k|lakhs?|lacs?|crores?|cr)\b)?\s*(?:rupees?|\brs\.?)\b",
        re.IGNORECASE,
    )
    spans = []
    for m in p1.finditer(text):
        spans.append(m.span())
        matched_str = m.group(0).strip()
        num_str = m.group("num").replace(",", "")
        sign = "-" if (m.group("prefix_sign") or m.group("inner_sign")) else ""
        unit = (m.group("unit") or "").lower()
        multiplier = MONEY_UNITS.get(unit, Decimal("1"))
        try:
            val = Decimal(sign + num_str) * multiplier
            results.append((matched_str, val))
        except InvalidOperation:
            pass

    for m in p2.finditer(text):
        start, end = m.span()
        if any(s <= start and end <= e for s, e in spans):
            continue
        matched_str = m.group(0).strip()
        num_str = m.group("num").replace(",", "")
        sign = "-" if m.group("prefix_sign") else ""
        unit = (m.group("unit") or "").lower()
        multiplier = MONEY_UNITS.get(unit, Decimal("1"))
        try:
            val = Decimal(sign + num_str) * multiplier
            results.append((matched_str, val))
        except InvalidOperation:
            pass

    return results


def verify_explanation(
    explanation_text: str,
    financial_result: dict | Any,
    intent: str | None = None,
) -> VerificationResult:
    """
    Verify explanation text against deterministic financial results.

    Returns VerificationResult containing:
      - verified: bool (True if violations is empty)
      - violations: list of blocking items {type, found, section, reason}
      - advisory: list of non-blocking items in next-steps advice {type, found, section}
      - advisory_count: count of advisory items
      - scope: VERIFICATION_SCOPE
    """
    if not explanation_text or "AI explanation temporarily unavailable" in explanation_text:
        return VerificationResult({
            "verified": False,
            "violations": [{
                "type": "LLM_ERROR",
                "found": "_DEFAULT_FALLBACK_TEXT",
                "section": "ALL",
                "reason": "LLM service failed after exhausted retries; fallback text returned",
            }],
            "advisory": [],
            "advisory_count": 0,
            "scope": VERIFICATION_SCOPE,
            "llm_error": True,
        })
    if not explanation_text or not explanation_text.strip():
        return VerificationResult({
            "verified": False,
            "violations": [
                {
                    "type": "empty_explanation",
                    "found": "",
                    "section": "WHOLE_TEXT",
                    "reason": "Explanation text is empty or whitespace",
                }
            ],
            "advisory": [],
            "advisory_count": 0,
            "scope": VERIFICATION_SCOPE,
        })

    allowed = extract_allowed_values(financial_result)
    sections = split_sections(explanation_text)

    violations = []
    advisory = []

    # Check for direct contradictions (always blocking in any section)
    text_lower = explanation_text.lower()
    decision = financial_result.get("decision") if isinstance(financial_result, dict) else None
    risk_level = financial_result.get("risk_level") if isinstance(financial_result, dict) else None

    # Helper to check if match is negated within the same sentence
    def _is_negated_in_sentence(text_full: str, match_start: int, match_end: int) -> bool:
        pre = text_full[:match_start]
        delims = [pre.rfind(d) for d in (".", "!", "?", ";", "\n")]
        sent_start = max(delims) + 1 if any(d != -1 for d in delims) else 0

        post = text_full[match_end:]
        delims_post = [post.find(d) for d in (".", "!", "?", ";", "\n") if post.find(d) != -1]
        sent_end = match_end + min(delims_post) if delims_post else len(text_full)

        sentence = text_full[sent_start:sent_end]
        return bool(re.search(r"\b(not|n't|never|unsafe|isn't)\b", sentence, re.IGNORECASE))

    # Decision contradiction checks (PURCHASE_SAFETY and general)
    if decision == "NOT_SAFE":
        contra_patterns = [
            r"\bdecision\s*(?:is|:)?\s*safe\b",
            r"\b(?:this\s+)?purchase\s+is\s+(?:completely\s+|entirely\s+)?safe\b",
            r"\b(?:completely\s+|entirely\s+)?safe\s+(?:to\s+(?:purchase|buy)|move)\b",
            r"\bcan\s+(?:safely\s+)?(?:purchase|buy)\b",
            r"\brisk\s*(?:is|:)?\s*low\b",
        ]
        for pat in contra_patterns:
            m = re.search(pat, text_lower)
            if m:
                if not _is_negated_in_sentence(text_lower, m.start(), m.end()):
                    violations.append({
                        "type": "CONTRADICTION",
                        "found": m.group(0),
                        "section": "WHOLE_TEXT",
                        "reason": "Claimed SAFE/LOW risk when decision is NOT_SAFE",
                    })

    elif decision == "SAFE":
        contra_patterns = [
            r"\bdecision\s*(?:is|:)?\s*not safe\b",
            r"\b(?:this\s+)?purchase\s+is\s+not\s+safe\b",
            r"\bunsafe\s+to\s+(?:purchase|buy)\b",
            r"\brisk\s*(?:is|:)?\s*high\b",
            r"\brisk\s*(?:is|:)?\s*very high\b",
        ]
        for pat in contra_patterns:
            m = re.search(pat, text_lower)
            if m:
                violations.append({
                    "type": "CONTRADICTION",
                    "found": m.group(0),
                    "section": "WHOLE_TEXT",
                    "reason": "Claimed NOT_SAFE/HIGH risk when decision is SAFE",
                })

    if risk_level in ("HIGH", "VERY_HIGH"):
        for m in re.finditer(r"\blow[\s\u2011\-]risk\b|\brisk\s*(?:is|:)?\s*low\b", text_lower):
            start = max(0, m.start() - 30)
            prefix = text_lower[start:m.start()]
            if not any(neg in prefix for neg in ("not", "n't", "never", "get you to", "reach", "aim for", "toward")):
                violations.append({
                    "type": "CONTRADICTION",
                    "found": m.group(0),
                    "section": "WHOLE_TEXT",
                    "reason": f"Claimed LOW risk when decision risk level is {risk_level}",
                })

    # Grade pattern: Grade X, grade of X, Health Grade: X, grade: X (X in A-D)
    grade_pattern = re.compile(
        r"\b(?:health\s+grade\s*[:\-]?|grade\s+(?:of\s+)?|grade\s*[:\-])\s*([A-D])\b",
        re.IGNORECASE,
    )

    # Evaluate each section
    for sec_name, sec_text in sections.items():
        is_advisory_section = (sec_name == "What You Should Do Next")

        # Strip markdown bold, italic, code markers before extraction
        clean_sec = re.sub(r"[*_`]", "", sec_text)

        # 1. Currency Amounts: Supporting INR prefix, suffix, units, minus, ranges
        money_matches = extract_money_tokens(clean_sec)
        for matched_str, dec_val in money_matches:
            matches = any(dec_val == a for a in allowed["money"])
            if not matches:
                item = {
                    "type": "unsupported_amount",
                    "found": matched_str,
                    "section": sec_name,
                }
                if is_advisory_section:
                    advisory.append(item)
                else:
                    item["reason"] = f"Amount {matched_str} not found in evidence"
                    violations.append(item)

        # 2. Percentages: XX%
        for m in re.findall(r"([0-9.]+)\s*%", clean_sec):
            matches = matches_with_tolerance(m, allowed["percent"])
            if not matches:
                item = {
                    "type": "unsupported_percent",
                    "found": f"{m}%",
                    "section": sec_name,
                }
                if is_advisory_section:
                    advisory.append(item)
                else:
                    item["reason"] = f"Percentage {m}% not found in evidence (within tolerance)"
                    violations.append(item)

        # 3. Durations: X month(s)
        for m in re.findall(r"\b([0-9.]+)\s*(?:‑|-|\s*)months?\b", clean_sec, re.IGNORECASE):
            matches = matches_with_tolerance(m, allowed["duration"])
            if not matches:
                item = {
                    "type": "unsupported_duration",
                    "found": f"{m} months",
                    "section": sec_name,
                }
                if is_advisory_section:
                    advisory.append(item)
                else:
                    item["reason"] = f"Duration {m} months not found in evidence (within tolerance)"
                    violations.append(item)

        # 4. Grade Check (A-D)
        for gm in grade_pattern.finditer(clean_sec):
            found_grade = gm.group(1).upper()
            found_token = gm.group(0).strip()
            evidence_grade = None
            if isinstance(financial_result, dict):
                evidence_grade = financial_result.get("grade")
            if evidence_grade and isinstance(evidence_grade, str):
                if found_grade != evidence_grade.upper():
                    violations.append({
                        "type": "WRONG_LABEL",
                        "found": found_token,
                        "section": sec_name,
                        "reason": f"Grade '{found_grade}' does not match evidence grade '{evidence_grade}'",
                    })
            elif any(g in allowed["label"] for g in ("A", "B", "C", "D")):
                if found_grade not in allowed["label"]:
                    violations.append({
                        "type": "WRONG_LABEL",
                        "found": found_token,
                        "section": sec_name,
                        "reason": f"Grade '{found_grade}' does not match evidence",
                    })

        # 5. Enum / Label checks
        # A: Check uppercase whole tokens matching MULTI_LETTER_ENUMS
        for wm in re.finditer(r"\b[A-Z_]{2,}\b", clean_sec):
            w = wm.group(0)
            if w in MULTI_LETTER_ENUMS and w not in allowed["label"]:
                violations.append({
                    "type": "WRONG_LABEL",
                    "found": w,
                    "section": sec_name,
                    "reason": f"Status label {w} does not match engine evidence",
                })

        # B: Check case-insensitive risk/status phrases with anchor words within 2 tokens
        proximity_patterns = [
            r"\b(low|medium|high|very\s+high|moderate|critical)\s+(?:risk|rating|level)\b",
            r"\b(?:risk|rating|level|status|health|buffer)\s*(?:is|:)?\s*(low|medium|high|very\s+high|moderate|critical|strong|healthy|insufficient|excellent|good|fair|poor)\b",
            r"\b(strong|healthy|insufficient|excellent|good|fair|poor)\s+(?:status|health|buffer)\b",
        ]
        for pat in proximity_patterns:
            for pm in re.finditer(pat, clean_sec, re.IGNORECASE):
                matched_phrase = pm.group(0)
                val_word = (pm.group(1) if pm.lastindex else matched_phrase).upper().replace(" ", "_")
                if val_word in MULTI_LETTER_ENUMS and val_word not in allowed["label"]:
                    violations.append({
                        "type": "WRONG_LABEL",
                        "found": matched_phrase,
                        "section": sec_name,
                        "reason": f"Status phrase '{matched_phrase}' ({val_word}) does not match engine evidence",
                    })

    verified = (len(violations) == 0)

    return VerificationResult({
        "verified": verified,
        "violations": violations,
        "advisory": advisory,
        "advisory_count": len(advisory),
        "scope": VERIFICATION_SCOPE,
        "llm_error": False,
    })


def build_retry_feedback(violations: list[dict]) -> str:
    """
    Format a concise, authoritative correction prompt listing ONLY blocking violations.
    """
    items = []
    for v in violations:
        found = v.get("found", "")
        reason = v.get("reason", "")
        sec = v.get("section", "")
        items.append(f"- Section [{sec}]: {reason} (found: {found})")

    violation_list = "\n".join(items)
    return (
        f"\nCORRECTION REQUIRED: Your previous explanation contained the following factual errors:\n"
        f"{violation_list}\n"
        f"Rewrite your explanation immediately. Use ONLY exact numbers that appear in <financial_evidence>. "
        f"Do not introduce unverified amounts, benchmarks, or derived calculations in any section."
    )
