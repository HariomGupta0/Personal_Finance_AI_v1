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


def convert_pdf_text_to_csv(text: str) -> str:
    """
    Heuristically extracts transaction table rows from extracted text and
    formats them into a clean CSV string suitable for parse_csv.
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    csv_rows: List[str] = ["Date,Description,Debit,Credit,Balance"]

    for line in lines:
        # Check if line begins with or contains a date
        date_match = DATE_REGEX.search(line)
        if not date_match:
            continue

        txn_date = date_match.group(1)
        remaining = (line[:date_match.start()] + " " + line[date_match.end():]).strip()

        # Find all amounts in the line
        amounts = AMOUNT_REGEX.findall(remaining)
        if not amounts:
            continue

        # Bank statements usually have 1, 2, or 3 amounts at the end of the line:
        # e.g.: [Debit/Credit, Balance] or [Debit, Credit, Balance]
        # Clean narration is the text preceding the numbers
        # Remove amounts from remaining text to get description
        desc_part = remaining
        for amt in amounts:
            desc_part = desc_part.replace(amt, "", 1)
        
        # Clean description
        desc = re.sub(r"\s+", " ", desc_part).strip(" -|;,")
        if not desc:
            desc = "Bank Transaction"

        # Escape quotes in description for CSV
        clean_desc = desc.replace('"', '""')

        debit = ""
        credit = ""
        balance = ""

        # Determine debit vs credit from line keywords (CR, DR, UPI, Deposit, etc.) or amount positioning
        lower_line = line.lower()
        if len(amounts) == 1:
            amt_val = amounts[0]
            if "cr" in lower_line or "credit" in lower_line or "deposit" in lower_line or "salary" in lower_line:
                credit = amt_val
            else:
                debit = amt_val
        elif len(amounts) == 2:
            # Often [Txn Amount, Balance]
            amt_val = amounts[0]
            balance = amounts[1]
            if "cr" in lower_line or "credit" in lower_line or "deposit" in lower_line or "refund" in lower_line or "salary" in lower_line:
                credit = amt_val
            else:
                debit = amt_val
        elif len(amounts) >= 3:
            # Often [Debit, Credit, Balance]
            debit = amounts[0]
            credit = amounts[1]
            balance = amounts[2]

        csv_rows.append(f'"{txn_date}","{clean_desc}","{debit}","{credit}","{balance}"')

    if len(csv_rows) <= 1:
        # Fallback: could not detect standard tabular lines
        raise PDFParseError(
            "Could not detect structured transaction rows in PDF statement. Please ensure it is an official bank e-statement."
        )

    return "\n".join(csv_rows)
