"""
Onboarding API — Rapid setup & cold-start bootstrap endpoints.
"""
from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.api.deps import get_current_user_id, get_neo4j_service
from backend.app.database.neo4j_service import Neo4jService
from backend.app.engine.financial_engine import (
    calculate_debt_burden,
    calculate_emergency_runway,
    calculate_comprehensive_health
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/onboarding", tags=["Onboarding"])


class BootstrapRequest(BaseModel):
    bank_name: str = Field(default="HDFC Bank", min_length=2, max_length=50)
    liquid_balance_inr: Optional[float] = None
    liquid_balance: Optional[float] = None
    monthly_income_inr: Optional[float] = None
    monthly_income: Optional[float] = None
    monthly_emi_inr: Optional[float] = 0.0
    monthly_emi: Optional[float] = None
    loan_type: Optional[str] = Field(default="Personal Loan", max_length=50)

    def get_liquid_balance(self) -> float:
        val = self.liquid_balance_inr if self.liquid_balance_inr is not None else self.liquid_balance
        return float(val or 0.0)

    def get_monthly_income(self) -> float:
        val = self.monthly_income_inr if self.monthly_income_inr is not None else self.monthly_income
        return float(val or 0.0)

    def get_monthly_emi(self) -> float:
        if self.monthly_emi is not None:
            return float(self.monthly_emi)
        if self.monthly_emi_inr is not None:
            return float(self.monthly_emi_inr)
        return 0.0


class BootstrapResponse(BaseModel):
    status: str
    user_id: str
    onboarding_completed: bool
    accounts_created: int
    initial_metrics: dict
    deterministic_metrics: Optional[dict] = None


@router.post("/bootstrap", response_model=BootstrapResponse)
def bootstrap_onboarding(
    payload: BootstrapRequest,
    user_id: str = Depends(get_current_user_id),
    db: Neo4jService = Depends(get_neo4j_service)
):
    """
    Bootstrap a new user's financial profile in under 1 second.
    Creates primary Account, Income, and optional Loan nodes in Neo4j,
    instantly activating deterministic runway and health calculations.
    """
    liquid_bal = payload.get_liquid_balance()
    monthly_inc = payload.get_monthly_income()
    monthly_emi_val = payload.get_monthly_emi()

    try:
        res = db.bootstrap_user_financials(
            user_id=user_id,
            bank_name=payload.bank_name,
            liquid_balance=liquid_bal,
            monthly_income=monthly_inc,
            monthly_emi=monthly_emi_val,
            loan_type=payload.loan_type or "Personal Loan"
        )
        if not res:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize user financials in Neo4j"
            )

        # Baseline living burn estimation: 50% of income or minimum ₹15,000
        baseline_living_burn = max(15000.0, monthly_inc * 0.5)
        runway_months = round(liquid_bal / baseline_living_burn, 1) if baseline_living_burn > 0 else 0.0
        dti_ratio = round((monthly_emi_val / monthly_inc) * 100.0, 1) if monthly_inc > 0 else 0.0
        health_score = round(min(100.0, max(0.0, (100.0 - dti_ratio) * 0.4 + min(runway_months / 6.0, 1.0) * 40.0 + 20.0)))
        health_grade = "A" if health_score >= 80 else ("B" if health_score >= 65 else ("C" if health_score >= 50 else "D"))
        runway_status = "STRONG" if runway_months >= 6.0 else ("ADEQUATE" if runway_months >= 3.0 else "INSUFFICIENT")

        initial_metrics = {
            "liquid_balance_inr": liquid_bal,
            "monthly_income_inr": monthly_inc,
            "monthly_emi_inr": monthly_emi_val,
            "estimated_living_burn": baseline_living_burn,
            "dti_ratio_pct": dti_ratio,
            "estimated_runway_months": runway_months,
            "runway_status": runway_status,
            "health_score": health_score,
            "health_grade": health_grade
        }

        deterministic_metrics = {
            "emergency_runway_months": runway_months,
            "debt_to_income_ratio": dti_ratio,
            "financial_health_score": health_score,
        }

        return BootstrapResponse(
            status="SUCCESS",
            user_id=user_id,
            onboarding_completed=True,
            accounts_created=1,
            initial_metrics=initial_metrics,
            deterministic_metrics=deterministic_metrics
        )

    except Exception as e:
        logger.error(f"Error in onboarding bootstrap: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bootstrap failed: {str(e)}"
        )


@router.get("/status")
def get_onboarding_status(
    user_id: str = Depends(get_current_user_id),
    db: Neo4jService = Depends(get_neo4j_service)
):
    """
    Returns whether the current user has completed onboarding or has existing transactions.
    """
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    accounts = db.get_user_accounts(user_id)
    txns = db.get_all_transactions(user_id, limit=1)

    is_complete = bool(user.get("onboarding_completed", False)) or len(accounts) > 0 or len(txns) > 0

    return {
        "user_id": user_id,
        "onboarding_completed": is_complete,
        "has_accounts": len(accounts) > 0,
        "has_transactions": len(txns) > 0
    }
