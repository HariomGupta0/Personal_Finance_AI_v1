"""
CSV bank statement parser.

Supports common column variations found in Indian/international bank exports:
  Date / Transaction Date / Value Date
  Description / Narration / Particulars / Remarks
  Debit / Withdrawal / Dr
  Credit / Deposit / Cr
  Amount / Transaction Amount
  Transaction Type / Type / Dr/Cr
  Balance / Closing Balance  (ignored — not treated as a transaction amount)
  Reference / Ref No / Transaction ID / UTR

Rules:
  - A missing or blank amount cell is NEVER treated as 0.
  - A "Closing Balance" or "Balance" column is NEVER used as the transaction amount.
  - If the column mapping is ambiguous the parser returns a list of candidate mappings
    for the caller to present to the user rather than guessing silently.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime
from typing import Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Column name aliases
# ---------------------------------------------------------------------------

DATE_COLS = [
    "date", "transaction date", "txn date", "value date", "trans date",
    "posting date", "booking date",
]

DESC_COLS = [
    "description", "narration", "particulars", "remarks", "details",
    "transaction details", "transaction narration", "transaction description",
    "name", "merchant", "payee", "beneficiary", "party", "party name", "mode",
]

DEBIT_COLS = [
    "debit", "withdrawal", "dr", "debit amount", "withdrawal amount",
    "debit (inr)", "amount debit",
]

CREDIT_COLS = [
    "credit", "deposit", "cr", "credit amount", "deposit amount",
    "credit (inr)", "amount credit",
]

AMOUNT_COLS = [
    "amount", "transaction amount", "txn amount", "value",
]

TYPE_COLS = [
    "transaction type", "type", "dr/cr", "cr/dr", "debit/credit", "drcr", "crdr",
    "dr_cr", "cr_dr", "txn type", "entry type", "type of transaction",
]

REF_COLS = [
    "ref", "reference", "ref no", "reference no", "reference number",
    "transaction id", "txn id", "utr", "chq/ref number", "cheque number",
    "instrument id", "narration ref", "utr number",
]

# Columns that must NEVER be used as a transaction amount
BALANCE_COLS = {
    "balance", "closing balance", "running balance", "available balance",
    "book balance", "ledger balance",
}

# ---------------------------------------------------------------------------
# Date format patterns tried in order
# ---------------------------------------------------------------------------

DATE_FORMATS = [
    "%Y-%m-%d",      # 2026-09-15
    "%d-%m-%Y",      # 15-09-2026
    "%d/%m/%Y",      # 15/09/2026
    "%m/%d/%Y",      # 09/15/2026
    "%d-%b-%Y",      # 15-Sep-2026
    "%d %b %Y",      # 15 Sep 2026
    "%d-%B-%Y",      # 15-September-2026
    "%Y/%m/%d",      # 2026/09/15
    "%d.%m.%Y",      # 15.09.2026
    "%b %d, %Y",     # Sep 15, 2026
    "%B %d, %Y",     # September 15, 2026
    "%d%b%Y",        # 15Sep2026
]


def _parse_date(raw: str) -> Optional[str]:
    """Try all known date formats; return ISO YYYY-MM-DD string or None."""
    raw = raw.strip()
    if not raw:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _parse_amount(raw) -> Optional[float]:
    """
    Parse an amount cell.
    Returns None if the cell is blank / None / truly unreadable.
    Never returns 0.0 for a missing value.
    """
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    raw_str = str(raw).strip()
    if not raw_str or raw_str in ("-", "—", "N/A", "n/a", "nil", "Nil"):
        return None
    # Strip currency symbols and thousands separators
    cleaned = re.sub(r"[₹$€£¥,\s]", "", raw_str)
    # Handle parenthesised negatives like (1234.56)
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    try:
        val = float(cleaned)
    except ValueError:
        return None
    return val  # Keep sign as-is; direction inferred later


def _normalise_col(name: str) -> str:
    return str(name).strip().lower()


def _match_col(headers: list[str], aliases: list[str]) -> Optional[str]:
    """Return the first header that matches any alias (case-insensitive)."""
    norm_headers = {_normalise_col(h): h for h in headers}
    for alias in aliases:
        if alias in norm_headers:
            return norm_headers[alias]
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class CSVParseError(ValueError):
    """Raised when the uploaded file cannot be parsed at all."""


class ColumnMapResult:
    """
    Result of the column-detection step.

    If `ambiguous` is True the caller MUST show `mapping_options` to the
    user and let them confirm before normalisation.
    """

    def __init__(
        self,
        mapping: dict,
        ambiguous: bool,
        warnings: list[str],
        unrecognized_columns: list[str] | None = None,
    ):
        self.mapping = mapping           # {role: actual_header_name}
        self.ambiguous = ambiguous
        self.warnings = warnings
        self.unrecognized_columns = unrecognized_columns or []


def _check_date_ambiguity(raw_date: str) -> bool:
    """
    Returns True if date string matches DD/MM/YYYY or MM/DD/YYYY
    where both day and month numbers are between 1 and 12 and not equal.
    """
    m = re.match(r"^(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})$", raw_date.strip())
    if m:
        p1, p2 = int(m.group(1)), int(m.group(2))
        if 1 <= p1 <= 12 and 1 <= p2 <= 12 and p1 != p2:
            return True
    return False


def detect_columns(df: pd.DataFrame) -> ColumnMapResult:
    """
    Inspect the DataFrame headers and produce a column mapping.

    Returns a ColumnMapResult whose `.mapping` dict contains keys:
        date, description, amount_col, amount_mode
    where `amount_mode` is one of: 'signed', 'debit_credit', 'separate'
    """
    headers = list(df.columns)
    warnings: list[str] = []
    ambiguous = False

    # Check for balance columns that must not be used as amounts
    norm_h = [_normalise_col(h) for h in headers]
    balance_present = any(h in BALANCE_COLS for h in norm_h)
    if balance_present:
        warnings.append(
            "A 'Balance' / 'Closing Balance' column was found and will be ignored — "
            "it is not a transaction amount."
        )

    date_col = _match_col(headers, DATE_COLS)
    desc_col = _match_col(headers, DESC_COLS)
    ref_col = _match_col(headers, REF_COLS)
    type_col = _match_col(headers, TYPE_COLS)

    # Determine amount mode
    debit_col = _match_col(headers, DEBIT_COLS)
    credit_col = _match_col(headers, CREDIT_COLS)
    amount_col = _match_col(headers, AMOUNT_COLS)

    # Guard: do not accept a balance column as the amount column
    if amount_col and _normalise_col(amount_col) in BALANCE_COLS:
        amount_col = None

    mapping: dict[str, Optional[str]] = {
        "date": date_col,
        "description": desc_col,
        "ref": ref_col,
        "type": type_col,
    }

    if debit_col and credit_col:
        mapping["amount_mode"] = "debit_credit"
        mapping["debit"] = debit_col
        mapping["credit"] = credit_col
        mapping["amount_col"] = None
    elif amount_col:
        mapping["amount_mode"] = "signed"
        mapping["amount_col"] = amount_col
        mapping["debit"] = None
        mapping["credit"] = None
    elif debit_col and not credit_col:
        # Only debit column present — unusual; flag as ambiguous
        mapping["amount_mode"] = "debit_only"
        mapping["debit"] = debit_col
        mapping["credit"] = None
        mapping["amount_col"] = None
        ambiguous = True
        warnings.append(
            "Only a 'Debit' column was detected but no 'Credit' column. "
            "Please confirm whether this file contains only expenses."
        )
    else:
        raise CSVParseError(
            "Cannot find an amount column. Expected one of: "
            + ", ".join(AMOUNT_COLS + DEBIT_COLS + CREDIT_COLS)
        )

    if not date_col:
        ambiguous = True
        warnings.append("No date column detected. Transactions will default to today's date.")
    if not desc_col:
        ambiguous = True
        warnings.append(
            "No description column found. Expected one of: "
            + ", ".join(DESC_COLS[:4])
        )

    # Identify unrecognized columns (present in CSV but unmapped and not known balance/enrichment)
    recognized_headers = {date_col, desc_col, ref_col, type_col, debit_col, credit_col, amount_col} - {None}
    enrichment_cols = {"name", "mode"}
    unrecognized = [
        h for h in headers
        if h not in recognized_headers
        and _normalise_col(h) not in BALANCE_COLS
        and _normalise_col(h) not in enrichment_cols
    ]
    if unrecognized:
        warnings.append(
            f"Unrecognized column(s) detected: {', '.join(unrecognized)}. These columns will not be mapped to transaction fields."
        )

    return ColumnMapResult(
        mapping=mapping,
        ambiguous=ambiguous,
        warnings=warnings,
        unrecognized_columns=unrecognized,
    )


def _infer_type_from_type_col(raw: str) -> Optional[str]:
    """Parse a type/dr-cr cell into EXPENSE | INCOME | REFUND | None."""
    v = str(raw).strip().upper()
    if v in ("CR", "CREDIT", "INCOME", "DEP", "DEPOSIT", "IN"):
        return "INCOME"
    if v in ("DR", "DB", "DEBIT", "EXPENSE", "WITHDRAWAL", "OUT", "WDL", "WD"):
        return "EXPENSE"
    if v in ("REFUND", "REV", "REVERSAL", "RETURN"):
        return "REFUND"
    return None


def parse_csv(
    content: bytes,
    user_mapping: Optional[dict] = None,
) -> dict:
    """
    Parse raw CSV bytes into a list of normalised row dicts.

    Parameters
    ----------
    content : bytes
        Raw file content.
    user_mapping : dict | None
        If the frontend resolved an ambiguous mapping it passes it here.
        Keys mirror ColumnMapResult.mapping.

    Returns
    -------
    dict with keys:
        rows     : list[dict]  — valid normalised rows
        errors   : list[dict]  — {row_index, raw, error}
        warnings : list[str]
        ambiguous: bool
        mapping  : dict        — detected column mapping (for frontend display)
        columns  : list[str]   — original CSV headers
    """
    # Validate content type heuristically
    try:
        text = content.decode("utf-8-sig")  # handle BOM
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except Exception as exc:
            raise CSVParseError(f"Could not decode file as text: {exc}") from exc

    # Reject obviously non-CSV content
    if text.strip().startswith("{") or text.strip().startswith("<"):
        raise CSVParseError("File appears to be JSON or HTML, not a CSV bank statement.")

    try:
        df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    except Exception as exc:
        raise CSVParseError(f"Failed to parse CSV: {exc}") from exc

    if df.empty:
        raise CSVParseError("The uploaded CSV file is empty.")

    # Detect or apply column mapping
    if user_mapping:
        col_map = ColumnMapResult(
            mapping=user_mapping,
            ambiguous=False,
            warnings=[],
        )
    else:
        col_map = detect_columns(df)

    mapping = col_map.mapping
    today_iso = date.today().isoformat()

    rows: list[dict] = []
    errors: list[dict] = []
    skipped: list[dict] = []
    has_ambiguous_dates = False
    ambiguous_sample: Optional[str] = None

    for idx, row in df.iterrows():
        raw_row = dict(row)
        error_reason = None

        # Check for completely blank row
        if all(str(v).strip() == "" for v in row.values):
            skipped.append({
                "row_index": int(idx) + 2,
                "reason": "Empty row skipped",
            })
            continue

        # --- Date ---
        date_iso: Optional[str] = None
        if mapping.get("date"):
            raw_date = str(row.get(mapping["date"], "")).strip()
            if not raw_date:
                error_reason = f"Row {idx + 2}: Date cell is blank in date column '{mapping['date']}'."
            else:
                date_iso = _parse_date(raw_date)
                if not date_iso:
                    error_reason = f"Row {idx + 2}: Invalid or unparseable date '{raw_date}'. Financial records require a valid date."
                elif _check_date_ambiguity(raw_date):
                    has_ambiguous_dates = True
                    if not ambiguous_sample:
                        ambiguous_sample = raw_date
        else:
            date_iso = today_iso

        # --- Description ---
        description = ""
        if mapping.get("description"):
            description = str(row.get(mapping["description"], "")).strip()

        # If description is empty or generic, check if name/mode columns exist to enrich it
        if not description or description.startswith("Imported transaction"):
            name_val = str(row.get("name", "")).strip() if "name" in row else ""
            mode_val = str(row.get("mode", "")).strip() if "mode" in row else ""
            if name_val and mode_val:
                description = f"{mode_val} - {name_val}"
            elif name_val:
                description = name_val
            elif mode_val:
                description = mode_val

        if not description:
            description = f"Imported transaction (row {idx + 2})"

        # --- Reference ---
        source_ref: Optional[str] = None
        if mapping.get("ref"):
            r = str(row.get(mapping["ref"], "")).strip()
            if r and r.lower() not in ("", "-", "n/a", "nil"):
                source_ref = r

        # --- Amount & Direction ---
        amount: Optional[float] = None
        tx_type: Optional[str] = None
        mode = mapping.get("amount_mode", "signed")

        if mode == "debit_credit":
            debit_raw = row.get(mapping.get("debit", ""), "")
            credit_raw = row.get(mapping.get("credit", ""), "")
            debit_val = _parse_amount(debit_raw) if debit_raw else None
            credit_val = _parse_amount(credit_raw) if credit_raw else None

            # Check if cells were non-empty but couldn't be parsed
            if str(debit_raw).strip() not in ("", "-", "—", "N/A", "n/a", "nil", "Nil") and debit_val is None:
                error_reason = f"Row {idx + 2}: Invalid debit amount '{debit_raw}'. Numbers must be valid amounts."
            elif str(credit_raw).strip() not in ("", "-", "—", "N/A", "n/a", "nil", "Nil") and credit_val is None:
                error_reason = f"Row {idx + 2}: Invalid credit amount '{credit_raw}'. Numbers must be valid amounts."
            elif debit_val is not None and debit_val != 0 and (credit_val is None or credit_val == 0):
                amount = abs(debit_val)
                tx_type = "EXPENSE"
            elif credit_val is not None and credit_val != 0 and (debit_val is None or debit_val == 0):
                amount = abs(credit_val)
                tx_type = "INCOME"
            elif debit_val is not None and credit_val is not None and debit_val != 0 and credit_val != 0:
                error_reason = f"Row {idx + 2}: Both debit and credit values are non-zero ({debit_val}, {credit_val}). Please review."
            else:
                error_reason = f"Row {idx + 2}: Missing amount — both debit and credit cells are blank."

        elif mode in ("signed", "debit_only"):
            raw_amt = row.get(mapping.get("amount_col") or mapping.get("debit", ""), "")
            if str(raw_amt).strip() == "":
                error_reason = f"Row {idx + 2}: Amount cell is blank. Skipping — amounts are never guessed."
            else:
                parsed = _parse_amount(raw_amt)
                if parsed is None:
                    error_reason = f"Row {idx + 2}: Amount cell is blank or cannot be parsed ('{raw_amt}'). Skipping — a missing amount is never treated as zero."
                elif parsed == 0:
                    error_reason = f"Row {idx + 2}: Amount is zero or missing after parsing."
                else:
                    amount = abs(parsed)
                    if mode == "debit_only":
                        tx_type = "EXPENSE"
                    elif parsed < 0:
                        tx_type = "EXPENSE"
                    else:
                        tx_type = "INCOME"

        # Override type from explicit type column
        if mapping.get("type") and error_reason is None:
            raw_type = str(row.get(mapping["type"], "")).strip()
            inferred = _infer_type_from_type_col(raw_type)
            if inferred:
                tx_type = inferred

        # Handle refund as INCOME subtype
        if tx_type == "REFUND":
            tx_type = "INCOME"  # stored as INCOME; description signals refund

        if error_reason:
            errors.append({"row_index": int(idx) + 2, "raw": raw_row, "error": error_reason, "reason": error_reason})
            continue

        if amount is None or amount <= 0:
            errors.append({
                "row_index": int(idx) + 2,
                "raw": raw_row,
                "error": f"Row {idx + 2}: Amount is zero or missing after parsing.",
                "reason": f"Row {idx + 2}: Amount is zero or missing after parsing.",
            })
            continue

        rows.append({
            "date": date_iso,
            "description": description,
            "amount": round(amount, 2),
            "type": tx_type or "EXPENSE",
            "category": None,        # will be inferred by import_pipeline
            "source_ref": source_ref,
            "source_type": "csv",
        })

    date_warnings = []
    if has_ambiguous_dates and ambiguous_sample:
        date_warnings.append(
            f"Ambiguous date format detected (e.g. '{ambiguous_sample}'). Dates were parsed assuming DD/MM/YYYY. If your statement uses MM/DD/YYYY, please verify dates in the preview."
        )

    return {
        "rows": rows,
        "errors": errors,
        "rejected_rows": errors,
        "skipped": skipped,
        "skipped_rows": skipped,
        "warnings": col_map.warnings + date_warnings,
        "ambiguous": col_map.ambiguous or has_ambiguous_dates,
        "date_ambiguity": has_ambiguous_dates,
        "unrecognized_columns": col_map.unrecognized_columns,
        "mapping": mapping,
        "columns": list(df.columns),
    }
