from fastapi import APIRouter, HTTPException, Depends
from backend.app.database.neo4j_service import Neo4jService
from backend.app.api.deps import get_current_user_id
from backend.app.engine.financial_engine import (
    calculate_category_expenses,
    calculate_savings_rate,
    calculate_emergency_fund,
    calculate_emergency_runway,
    calculate_debt_burden,
    calculate_comprehensive_health,
    generate_financial_summary
)

router = APIRouter(prefix="/api/finance", tags=["Finance"])
db = Neo4jService()

@router.get("/summary")
def get_summary(user_id: str = Depends(get_current_user_id)):
    context = db.get_financial_context(user_id)
    if not context:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    return generate_financial_summary(context)

@router.get("/expenses")
def get_expenses(user_id: str = Depends(get_current_user_id)):
    context = db.get_financial_context(user_id)
    if not context:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    return calculate_category_expenses(context)

@router.get("/savings")
def get_savings(user_id: str = Depends(get_current_user_id)):
    context = db.get_savings_context(user_id)
    if not context:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    return calculate_savings_rate(context)

@router.get("/emergency-fund")
def get_emergency_fund(user_id: str = Depends(get_current_user_id)):
    context = db.get_financial_context(user_id)
    if not context:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    fund_data = calculate_emergency_fund(context)
    runway_data = calculate_emergency_runway(context)
    return {
        **fund_data,
        **runway_data
    }

@router.get("/debt")
def get_debt(user_id: str = Depends(get_current_user_id)):
    context = db.get_financial_context(user_id)
    if not context:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    debt_burden = calculate_debt_burden(context)
    return {
        **debt_burden,
        "loans": context.get("loans", [])
    }

@router.get("/health")
def get_health(user_id: str = Depends(get_current_user_id)):
    context = db.get_financial_context(user_id)
    if not context:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    return calculate_comprehensive_health(context)
