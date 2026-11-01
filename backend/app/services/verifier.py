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

    if decision == "NOT_SAFE":
        contra_patterns = [
            r"\bdecision\s*(?:is|:)?\s*safe\b",
            r"\bpurchase is safe\b",
            r"\bcompletely safe to purchase\b",
            r"\brisk\s*(?:is|:)?\s*low\b",
        ]
        for pat in contra_patterns:
            m = re.search(pat, text_lower)
            if m:
                start = max(0, m.start() - 20)
                prefix = text_lower[start:m.start()]
                if "not" not in prefix and "n't" not in prefix and "never" not in prefix:
                    violations.append({
                        "type": "CONTRADICTION",
                        "found": m.group(0),
                        "section": "WHOLE_TEXT",
                        "reason": "Claimed SAFE/LOW risk when decision is NOT_SAFE",
                    })

    elif decision == "SAFE":
        contra_patterns = [
            r"\bdecision\s*(?:is|:)?\s*not safe\b",
            r"\bpurchase is not safe\b",
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
        if re.search(r"\blow risk\b", text_lower) and not re.search(r"\bnot\s+low risk\b", text_lower):
            violations.append({
                "type": "CONTRADICTION",
                "found": "low risk",
                "section": "WHOLE_TEXT",
                "reason": f"Claimed LOW risk when decision risk level is {risk_level}",
            })

    # Evaluate each section
    for sec_name, sec_text in sections.items():
        is_advisory_section = (sec_name == "What You Should Do Next")

        # Strip markdown bold, italic, code markers before extraction
        clean_sec = re.sub(r"[*_`]", "", sec_text)

        # 1. Currency Amounts: ₹... (Money NEVER uses tolerance)
        for m in re.findall(r"(?:₹|Rs\.?)\s*([0-9,]+(?:\.[0-9]+)?)", clean_sec):
            clean_m = m.replace(",", "")
            try:
                dec_val = Decimal(clean_m)
                matches = any(dec_val == a for a in allowed["money"])
            except InvalidOperation:
                matches = False

            if not matches:
                item = {
                    "type": "unsupported_amount",
                    "found": f"₹{m}",
                    "section": sec_name,
                }
                if is_advisory_section:
                    advisory.append(item)
                else:
                    item["reason"] = f"Amount ₹{m} not found in evidence"
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

        # 4. Enum / Label checks (Wrong labels are ALWAYS blocking)
        # Check capitalized engine enums appearing in prose
        for word in re.findall(r"\b(SAFE|NOT_SAFE|HIGH|MEDIUM|LOW|VERY_HIGH|MODERATE|CRITICAL|EXCELLENT|GOOD|FAIR|POOR)\b", clean_sec):
            if word in ENUM_VOCAB and word not in allowed["label"]:
                # Only flag if it acts as a conflicting status indicator
                violations.append({
                    "type": "WRONG_LABEL",
                    "found": word,
                    "section": sec_name,
                    "reason": f"Status label {word} does not match engine evidence",
                })

    verified = (len(violations) == 0)

    return VerificationResult({
        "verified": verified,
        "violations": violations,
        "advisory": advisory,
        "advisory_count": len(advisory),
        "scope": VERIFICATION_SCOPE,
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
