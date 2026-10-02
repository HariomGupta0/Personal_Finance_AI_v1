"""
Image-based financial document extractor.

Accepts a JPEG/PNG/WebP/GIF image and attempts to extract structured
transaction information using Groq's vision-capable model.

Rules:
  - Never invent values that are not visible in the image.
  - If a field is not clearly legible, return null for that field.
  - If the transaction status is not clearly "SUCCESS" or equivalent,
    set status to "UNKNOWN" and add a warning.
  - The extracted result MUST be reviewed by the user before persistence.
  - Groq API key is reused from the existing llm_service configuration.
"""

from __future__ import annotations

import base64
import json
import re
from typing import Optional

from groq import Groq  # imported at module level so tests can mock it

SUPPORTED_MIME_TYPES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG":      "image/png",
    b"RIFF":         "image/webp",   # WebP starts with RIFF....WEBP
    b"GIF8":         "image/gif",
}

VISION_MODEL = "llama-3.2-11b-vision-preview"  # Groq's vision model

EXTRACTION_PROMPT = """You are a financial document parser. Examine the image carefully and extract transaction information.

STRICT RULES:
1. Only extract values that are clearly visible in the image.
2. If a field is not visible or is ambiguous, set it to null — do NOT guess or invent.
3. For transaction_status: only set "SUCCESS" if the image explicitly shows success/completed status. Otherwise set "UNKNOWN".
4. For direction: "expense" means money went OUT from the user; "income" means money came IN; "refund" means a reversal/return; "unknown" if unclear.
5. Return ONLY valid JSON. No markdown, no prose.

Return this exact JSON schema:
{
  "date": "<YYYY-MM-DD or null>",
  "amount": <positive number or null>,
  "currency": "<INR|USD|EUR|GBP|... or null>",
  "merchant_or_recipient": "<string or null>",
  "direction": "<expense|income|refund|unknown>",
  "transaction_status": "<SUCCESS|FAILED|PENDING|UNKNOWN>",
  "reference_id": "<string or null>",
  "source_type": "image",
  "confidence": "<high|medium|low>",
  "warnings": ["<any concerns about legibility or interpretation>"]
}"""


def _detect_mime(content: bytes) -> str:
    """Return MIME type based on magic bytes."""
    for magic, mime in SUPPORTED_MIME_TYPES.items():
        if content[:len(magic)] == magic:
            return mime
    # WebP needs extra check (bytes 8-12 == WEBP)
    if len(content) >= 12 and content[8:12] == b"WEBP":
        return "image/webp"
    raise ValueError(
        "Unsupported image format. Accepted formats: JPEG, PNG, WebP, GIF."
    )


def _base64_encode_image(content: bytes) -> str:
    return base64.b64encode(content).decode("ascii")


def extract_from_image(content: bytes) -> dict:
    """
    Extract financial transaction fields from an image.

    Parameters
    ----------
    content : bytes
        Raw image bytes (JPEG/PNG/WebP/GIF).

    Returns
    -------
    dict with keys matching the JSON schema above, plus:
        extraction_success : bool
        raw_response       : str  (for debugging, not logged to user)

    Raises
    ------
    ValueError if the file is not a supported image format.
    """
    mime_type = _detect_mime(content)  # raises ValueError for unsupported formats

    from backend.config import GROQ_API_KEY

    client = Groq(api_key=GROQ_API_KEY, timeout=30.0)

    b64 = _base64_encode_image(content)

    try:
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{b64}",
                            },
                        },
                        {
                            "type": "text",
                            "text": EXTRACTION_PROMPT,
                        },
                    ],
                }
            ],
            max_tokens=512,
        )
        raw_response = response.choices[0].message.content or ""
    except Exception as exc:
        return _fallback_result(
            warnings=[f"Vision API call failed: {str(exc)[:200]}. Please enter transaction details manually."],
            raw_response="",
        )

    # Parse JSON from response
    cleaned = re.sub(r"^```json\s*", "", raw_response, flags=re.MULTILINE)
    cleaned = re.sub(r"```$", "", cleaned, flags=re.MULTILINE).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return _fallback_result(
            warnings=["Could not parse extraction response. Please enter transaction details manually."],
            raw_response=raw_response,
        )

    # Validate and sanitise extracted fields
    result = _sanitise_extraction(data)
    result["raw_response"] = raw_response  # kept for debug, not surfaced to user
    result["extraction_success"] = True
    result["source_type"] = "image"
    return result


def _sanitise_extraction(data: dict) -> dict:
    """Validate extracted fields; null out anything that looks invented."""
    warnings = list(data.get("warnings") or [])

    # Amount must be positive or null
    amount = data.get("amount")
    if amount is not None:
        try:
            amount = float(amount)
            if amount <= 0:
                amount = None
                warnings.append("Extracted amount was zero or negative — set to null for manual review.")
        except (TypeError, ValueError):
            amount = None
            warnings.append("Amount could not be parsed — set to null for manual review.")

    # Direction
    direction = str(data.get("direction") or "unknown").lower()
    if direction not in ("expense", "income", "refund", "unknown"):
        direction = "unknown"
        warnings.append("Transaction direction is ambiguous — please confirm.")

    # Status
    status = str(data.get("transaction_status") or "UNKNOWN").upper()
    if status not in ("SUCCESS", "FAILED", "PENDING", "UNKNOWN"):
        status = "UNKNOWN"
    if status != "SUCCESS":
        warnings.append(
            f"Transaction status is '{status}' — do not record unless you have confirmed the payment completed."
        )

    # Confidence
    confidence = str(data.get("confidence") or "low").lower()
    if confidence not in ("high", "medium", "low"):
        confidence = "low"
    if confidence == "low":
        warnings.append("Extraction confidence is low — all fields require manual verification.")

    # Date
    raw_date = data.get("date")
    date_iso: Optional[str] = None
    if raw_date:
        # Accept ISO date or try to parse
        if re.match(r"^\d{4}-\d{2}-\d{2}$", str(raw_date)):
            date_iso = str(raw_date)
        else:
            warnings.append(f"Date '{raw_date}' is in an unrecognised format — please enter manually.")

    # Map direction to tx_type for the pipeline
    direction_to_type = {
        "expense": "EXPENSE",
        "income": "INCOME",
        "refund": "INCOME",  # stored as INCOME; description/source_type signals refund
        "unknown": None,
    }

    return {
        "date": date_iso,
        "amount": amount,
        "currency": data.get("currency"),
        "description": data.get("merchant_or_recipient"),
        "direction": direction,
        "type": direction_to_type.get(direction),
        "transaction_status": status,
        "source_ref": data.get("reference_id"),
        "confidence": confidence,
        "warnings": warnings,
        "extraction_success": False,  # overwritten by caller on success
    }


def _fallback_result(warnings: list[str], raw_response: str) -> dict:
    return {
        "date": None,
        "amount": None,
        "currency": None,
        "description": None,
        "direction": "unknown",
        "type": None,
        "transaction_status": "UNKNOWN",
        "source_ref": None,
        "confidence": "low",
        "warnings": warnings,
        "extraction_success": False,
        "source_type": "image",
        "raw_response": raw_response,
    }
