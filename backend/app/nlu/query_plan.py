"""
Structured Query Plan (SQP) Schema for Personal Finance AI Assistant.

Provides a validated, typed representation of user analytical intents.
Acts as the architectural bridge between Natural Language Understanding (NLU)
and parameterized database retrieval / deterministic calculations, preventing
arbitrary LLM-generated Cypher injection.
"""
from datetime import date
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

from backend.app.core.money import normalize_rupees


class OperationType(str, Enum):
    CATEGORY_EXPENSE = "CATEGORY_EXPENSE"
    EXPENSE_BREAKDOWN = "EXPENSE_BREAKDOWN"
    TOTAL_EXPENSE = "TOTAL_EXPENSE"
    MERCHANT_EXPENSE = "MERCHANT_EXPENSE"
    TOP_TRANSACTIONS = "TOP_TRANSACTIONS"
    PERIOD_COMPARISON = "PERIOD_COMPARISON"
    SPENDING_TREND = "SPENDING_TREND"
    PURCHASE_SAFETY = "PURCHASE_SAFETY"
    SAVINGS_ANALYSIS = "SAVINGS_ANALYSIS"
    EMERGENCY_RUNWAY_ANALYSIS = "EMERGENCY_RUNWAY_ANALYSIS"
    EMERGENCY_FUND_ANALYSIS = "EMERGENCY_FUND_ANALYSIS"
    DEBT_ANALYSIS = "DEBT_ANALYSIS"
    FINANCIAL_HEALTH = "FINANCIAL_HEALTH"
    FINANCIAL_SUMMARY = "FINANCIAL_SUMMARY"
    TRANSACTION_INGESTION = "TRANSACTION_INGESTION"
    GENERAL_FINANCIAL_KNOWLEDGE = "GENERAL_FINANCIAL_KNOWLEDGE"
    UNKNOWN = "UNKNOWN"


class DateRange(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reporting_period: Optional[str] = None  # e.g. "2026-10"


class ExpenditureQueryPlan(BaseModel):
    """
    Validated execution plan for expenditure intelligence queries.
    """
    operation: OperationType = Field(
        default=OperationType.UNKNOWN,
        description="The validated financial analytical operation"
    )
    raw_query: str = Field(default="", description="Original natural language user question")
    date_range: DateRange = Field(
        default_factory=DateRange,
        description="Primary temporal range for filtering"
    )
    comparison_date_range: Optional[DateRange] = Field(
        default=None,
        description="Optional secondary temporal range for period comparisons"
    )
    trend_months: Optional[int] = Field(
        default=None,
        ge=1,
        le=36,
        description="Number of historical months for trend analysis"
    )
    category: Optional[str] = Field(
        default=None,
        description="Target normalized expense category (e.g., 'Food', 'Transport')"
    )
    merchant: Optional[str] = Field(
        default=None,
        description="Target merchant or payee name (e.g., 'Uber', 'Swiggy')"
    )
    amount: Optional[float] = Field(
        default=None,
        description="Target single amount for purchase safety checks"
    )
    amount_min: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Minimum transaction threshold filter (e.g. expenses > ₹5,000)"
    )
    amount_max: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Maximum transaction threshold filter"
    )

    @field_validator("amount", "amount_min", "amount_max", mode="before")
    @classmethod
    def _normalize_amount_fields(cls, v):
        if v is None:
            return None
        try:
            return normalize_rupees(v)
        except (ValueError, TypeError):
            return None
    sort_by: str = Field(
        default="date",
        description="Attribute to sort results by ('amount', 'date')"
    )
    sort_direction: str = Field(
        default="DESC",
        description="Sort direction ('ASC', 'DESC')"
    )
    limit: Optional[int] = Field(
        default=None,
        ge=1,
        le=100,
        description="Limit on number of records (e.g. top 5)"
    )
    exclude_transfers: bool = Field(
        default=True,
        description="Whether internal account transfers should be excluded from expenditure totals"
    )
    is_followup: bool = Field(
        default=False,
        description="Whether this query was resolved as a conversational follow-up"
    )
    needs_clarification: bool = Field(
        default=False,
        description="Whether essential information is missing or ambiguous"
    )
    clarification_type: Optional[str] = Field(
        default=None,
        description="Type of clarification required (e.g. 'MISSING_AMOUNT', 'AMBIGUOUS_DATE', 'AMBIGUOUS_PERIOD')"
    )
    clarification_message: Optional[str] = Field(
        default=None,
        description="User-facing prompt asking for required clarification"
    )

    def to_legacy_entities(self) -> dict:
        """
        Backwards-compatible bridge converting ExpenditureQueryPlan into the
        entities dictionary expected by legacy GraphRAG components.
        """
        rep_date = self.date_range.start_date if self.date_range else None
        comp_rep_date = self.comparison_date_range.start_date if self.comparison_date_range else None
        return {
            "intent": self.operation.value,
            "operation": self.operation.value,
            "category": self.category,
            "merchant": self.merchant,
            "amount": self.amount,
            "amount_min": self.amount_min,
            "amount_max": self.amount_max,
            "limit": self.limit,
            "sort_by": self.sort_by,
            "sort_direction": self.sort_direction,
            "reporting_date": rep_date,
            "comparison_reporting_date": comp_rep_date,
            "date_range": self.date_range,
            "comparison_date_range": self.comparison_date_range,
            "trend_months": self.trend_months,
            "raw_query": self.raw_query,
            "is_followup": self.is_followup,
            "needs_clarification": self.needs_clarification,
            "clarification_type": self.clarification_type,
            "clarification_message": self.clarification_message,
            "exclude_transfers": self.exclude_transfers,
            "query_plan": self,
        }


def create_query_plan_from_parsed(parsed: dict) -> ExpenditureQueryPlan:
    """
    Constructs and validates an ExpenditureQueryPlan from an intent/entity dictionary.
    Enforces the explicit resolution strategy when legacy parsers or LLM fallbacks
    disagree with domain rules (e.g., confusing merchants with categories).
    """
    if not isinstance(parsed, dict):
        return ExpenditureQueryPlan(operation=OperationType.UNKNOWN)

    # 1. Resolve operation enum safely
    raw_intent = str(parsed.get("intent") or parsed.get("operation") or "UNKNOWN").strip().upper()
    try:
        operation = OperationType(raw_intent)
    except ValueError:
        operation = OperationType.UNKNOWN

    raw_query = parsed.get("raw_query") or ""
    cat = parsed.get("category")
    merchant = parsed.get("merchant")

    # 2. Disagreement Resolution Strategy:
    # If legacy parser classified query as CATEGORY_EXPENSE, but the 'category' is actually
    # a known merchant (e.g. Uber, Swiggy, Netflix), correct operation to MERCHANT_EXPENSE.
    from backend.app.services.merchant_normalizer import KNOWN_MERCHANTS
    if operation == OperationType.CATEGORY_EXPENSE and cat:
        cat_lower = cat.lower().strip()
        if cat_lower in KNOWN_MERCHANTS:
            canonical_name, _ = KNOWN_MERCHANTS[cat_lower]
            operation = OperationType.MERCHANT_EXPENSE
            merchant = canonical_name
            cat = None

    # 3. Resolve DateRange & Comparison DateRange
    rep_date = parsed.get("reporting_date")
    start_date = None
    end_date = None
    reporting_period = None

    if rep_date:
        if isinstance(rep_date, str):
            try:
                rep_date = date.fromisoformat(rep_date)
            except Exception:
                rep_date = None
        if isinstance(rep_date, date):
            import calendar
            last_day = calendar.monthrange(rep_date.year, rep_date.month)[1]
            start_date = date(rep_date.year, rep_date.month, 1)
            end_date = date(rep_date.year, rep_date.month, last_day)
            reporting_period = f"{rep_date.year}-{rep_date.month:02d}"

    date_range = DateRange(
        start_date=start_date,
        end_date=end_date,
        reporting_period=reporting_period,
    )

    comp_rep_date = parsed.get("comparison_reporting_date")
    comp_start = None
    comp_end = None
    comp_period = None

    if comp_rep_date:
        if isinstance(comp_rep_date, str):
            try:
                comp_rep_date = date.fromisoformat(comp_rep_date)
            except Exception:
                comp_rep_date = None
        if isinstance(comp_rep_date, date):
            import calendar
            last_day = calendar.monthrange(comp_rep_date.year, comp_rep_date.month)[1]
            comp_start = date(comp_rep_date.year, comp_rep_date.month, 1)
            comp_end = date(comp_rep_date.year, comp_rep_date.month, last_day)
            comp_period = f"{comp_rep_date.year}-{comp_rep_date.month:02d}"

    comparison_date_range = None
    if comp_start:
        comparison_date_range = DateRange(
            start_date=comp_start,
            end_date=comp_end,
            reporting_period=comp_period,
        )
    elif isinstance(parsed.get("comparison_date_range"), DateRange):
        comparison_date_range = parsed.get("comparison_date_range")

    trend_months = parsed.get("trend_months")
    if trend_months is not None:
        try:
            trend_months = max(1, min(36, int(trend_months)))
        except (ValueError, TypeError):
            trend_months = None

    # 4. Numeric and Threshold Boundaries
    amt = parsed.get("amount")
    if amt is not None:
        try:
            amt = normalize_rupees(amt)
        except (ValueError, TypeError):
            amt = None

    amt_min = parsed.get("amount_min")
    if amt_min is not None:
        try:
            amt_min = max(0.0, normalize_rupees(amt_min))
        except (ValueError, TypeError):
            amt_min = None

    amt_max = parsed.get("amount_max")
    if amt_max is not None:
        try:
            amt_max = max(0.0, normalize_rupees(amt_max))
        except (ValueError, TypeError):
            amt_max = None

    limit_val = parsed.get("limit")
    if limit_val is not None:
        try:
            limit_val = max(1, min(100, int(limit_val)))
        except (ValueError, TypeError):
            limit_val = None

    sort_by = str(parsed.get("sort_by") or ("amount" if operation == OperationType.TOP_TRANSACTIONS else "date"))
    sort_direction = str(parsed.get("sort_direction") or "DESC").upper()
    if sort_direction not in ["ASC", "DESC"]:
        sort_direction = "DESC"

    return ExpenditureQueryPlan(
        operation=operation,
        raw_query=raw_query,
        date_range=date_range,
        comparison_date_range=comparison_date_range,
        trend_months=trend_months,
        category=cat,
        merchant=merchant,
        amount=amt,
        amount_min=amt_min,
        amount_max=amt_max,
        sort_by=sort_by,
        sort_direction=sort_direction,
        limit=limit_val,
        exclude_transfers=parsed.get("exclude_transfers", True),
        is_followup=parsed.get("is_followup", False),
        needs_clarification=parsed.get("needs_clarification", False),
        clarification_type=parsed.get("clarification_type"),
        clarification_message=parsed.get("clarification_message"),
    )


