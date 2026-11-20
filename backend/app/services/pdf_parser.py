"""
PDF bank statement parser using pypdf.

Extracts tabular transaction data from Indian bank PDF statements
(e.g., HDFC, SBI, ICICI, Axis).
Supports password-protected statements (e.g. PAN or DOB) via in-memory decryption.
"""

from __future__ import annotations

import io
import re
from typing import List, Optional, Tuple
import pypdf


class PDFPasswordRequiredError(Exception):
    pass


class PDFIncorrectPasswordError(Exception):
    pass


class PDFParseError(Exception):
    pass


# Common Indian bank date patterns:
# DD/MM/YYYY, DD-MM-YYYY, DD/MM/YY, DD-MM-YY, DD Mon YYYY
DATE_REGEX = re.compile(
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})\b",
    re.IGNORECASE,
)

# Number with optional commas and decimals: e.g. 1,250.00 or 450.50 or 50000
AMOUNT_REGEX = re.compile(r"\b\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?\b")


def extract_text_from_pdf(content: bytes, password: Optional[str] = None) -> str:
    """
    Decrypts (if needed) and extracts all text lines from a bank statement PDF.
    """
    stream = io.BytesIO(content)
    try:
        reader = pypdf.PdfReader(stream)
    except Exception as exc:
        raise PDFParseError(f"Invalid or corrupted PDF file: {exc}")

    if reader.is_encrypted:
        if not password:
            raise PDFPasswordRequiredError(
                "PDF statement is password protected. Please provide the statement password (usually PAN, DOB, or Mobile)."
            )
        try:
            # pypdf decrypt returns an int or DecryptionResult enum
            decrypt_result = reader.decrypt(password)
            if not decrypt_result:
                raise PDFIncorrectPasswordError("Incorrect PDF password.")
        except PDFIncorrectPasswordError:
            raise
        except Exception as exc:
            raise PDFIncorrectPasswordError(f"Failed to decrypt PDF: {exc}")

    full_text = []
    for page_idx, page in enumerate(reader.pages):
        try:
            page_text = page.extract_text() or ""
            if page_text:
                full_text.append(page_text)
        except Exception:
            continue

    if not full_text:
        raise PDFParseError("No readable text found in PDF. Scanned image-only PDFs are not supported.")

    return "\n".join(full_text)


def _format_csv_row(txn_date: str, remaining: str) -> Optional[str]:
    # Ignore header text lines that accidentally match dates
    lower_rem = remaining.lower()
    if any(k in lower_rem for k in ["statement period", "account number", "closing balance", "txn date", "value date"]):
        return None

    amounts = AMOUNT_REGEX.findall(remaining)
    if not amounts:
        return None

    desc_part = remaining
    for amt in amounts:
        desc_part = desc_part.replace(amt, "", 1)

    desc = re.sub(r"\s+", " ", desc_part).strip(" -|;,■")
    if not desc or len(desc) < 2:
        desc = "Bank Transaction"

    clean_desc = desc.replace('"', '""')
    debit = ""
    credit = ""
    balance = ""

    lower_line = f"{desc} {remaining}".lower()
    if len(amounts) == 1:
        amt_val = amounts[0]
        if any(k in lower_line for k in ["cr", "credit", "deposit", "salary", "refund"]):
            credit = amt_val
        else:
            debit = amt_val
    elif len(amounts) == 2:
        # Often [Txn Amount, Balance]
        amt_val = amounts[0]
        balance = amounts[1]
        if any(k in lower_line for k in ["cr", "credit", "deposit", "refund", "salary"]):
            credit = amt_val
        else:
            debit = amt_val
    elif len(amounts) >= 3:
        # Often [Debit, Credit, Balance]
        debit = amounts[0]
        credit = amounts[1]
        balance = amounts[2]

    return f'"{txn_date}","{clean_desc}","{debit}","{credit}","{balance}"'


def convert_pdf_text_to_csv(text: str) -> str:
    """
    Heuristically extracts transaction table rows from extracted text and
    formats them into a clean CSV string suitable for parse_csv.
    Supports both single-line tabular rows and multi-line column extractions.
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    # Strategy 1: Single-line row matches
    csv_rows: List[str] = ["Date,Description,Debit,Credit,Balance"]
    for line in lines:
        if any(k in line.lower() for k in ["statement period", "account number", "balance as on"]):
            continue
        date_match = DATE_REGEX.search(line)
        if not date_match:
            continue

        txn_date = date_match.group(1)
        remaining = (line[:date_match.start()] + " " + line[date_match.end():]).strip()
        row = _format_csv_row(txn_date, remaining)
        if row:
            csv_rows.append(row)

    if len(csv_rows) > 3:
        return "\n".join(csv_rows)

    # Strategy 2: Multi-line chunk grouping
    multi_rows: List[str] = ["Date,Description,Debit,Credit,Balance"]
    curr_date = None
    curr_tokens: List[str] = []

    for l in lines:
        if any(k in l.lower() for k in ["statement period", "account number", "balance as on"]):
            continue
        dm = DATE_REGEX.search(l)
        if dm and (dm.start() == 0 or len(l.split()) <= 2):
            d_val = dm.group(1)
            # Check if this is a consecutive duplicate date (like Value Date)
            if curr_date and not curr_tokens:
                continue
            if curr_date and curr_tokens:
                rem_text = " ".join(curr_tokens)
                row = _format_csv_row(curr_date, rem_text)
                if row:
                    multi_rows.append(row)
            curr_date = d_val
            curr_tokens = []
            rem_l = (l[:dm.start()] + " " + l[dm.end():]).strip()
            if rem_l:
                curr_tokens.append(rem_l)
        elif curr_date:
            curr_tokens.append(l)

    if curr_date and curr_tokens:
        rem_text = " ".join(curr_tokens)
        row = _format_csv_row(curr_date, rem_text)
        if row:
            multi_rows.append(row)

    if len(multi_rows) > 1:
        return "\n".join(multi_rows)

    raise PDFParseError(
        "Could not detect structured transaction rows in PDF statement. Please ensure it is an official bank e-statement."
    )
