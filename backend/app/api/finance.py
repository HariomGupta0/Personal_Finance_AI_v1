from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.deps import get_current_user_id, get_neo4j_service
from backend.app.database.neo4j_service import Neo4jService
from backend.app.engine.financial_engine import (
    calculate_category_expenses,
    calculate_comprehensive_health,
    calculate_debt_burden,
    calculate_emergency_fund,
    calculate_emergency_runway,
    calculate_savings_rate,
    generate_financial_summary,
)

router = APIRouter(prefix="/api/finance", tags=["Finance"])


@router.get("/summary")
def get_summary(
    user_id: str = Depends(get_current_user_id),
    db: Neo4jService = Depends(get_neo4j_service),
):
    context = db.get_financial_context(user_id)
    if not context:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    return generate_financial_summary(context)


@router.get("/expenses")
def get_expenses(
    user_id: str = Depends(get_current_user_id),
    db: Neo4jService = Depends(get_neo4j_service),
):
    context = db.get_financial_context(user_id)
    if not context:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    return calculate_category_expenses(context)


@router.get("/savings")
def get_savings(
    user_id: str = Depends(get_current_user_id),
    db: Neo4jService = Depends(get_neo4j_service),
):
    context = db.get_savings_context(user_id)
    if not context:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    return calculate_savings_rate(context)


@router.get("/emergency-fund")
def get_emergency_fund(
    user_id: str = Depends(get_current_user_id),
    db: Neo4jService = Depends(get_neo4j_service),
):
    context = db.get_financial_context(user_id)
    if not context:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    fund_data = calculate_emergency_fund(context)
    runway_data = calculate_emergency_runway(context)
    return {
        **fund_data,
        **runway_data,
    }


@router.get("/debt")
def get_debt(
    user_id: str = Depends(get_current_user_id),
    db: Neo4jService = Depends(get_neo4j_service),
):
    context = db.get_financial_context(user_id)
    if not context:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    debt_burden = calculate_debt_burden(context)
    return {
        **debt_burden,
        "loans": context.get("loans", []),
    }


@router.get("/health")
def get_health(
    user_id: str = Depends(get_current_user_id),
    db: Neo4jService = Depends(get_neo4j_service),
):
    context = db.get_financial_context(user_id)
    if not context:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    return calculate_comprehensive_health(context)


@router.get("/plan")
async def get_financial_plan_endpoint(
    refresh: bool = False,
    user_id: str = Depends(get_current_user_id),
    db: Neo4jService = Depends(get_neo4j_service),
):
    """
    Generate or retrieve a data-driven personalized financial plan for the user.
    """
    context = db.get_financial_context(user_id)
    if not context:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    from backend.app.services.financial_planner import generate_financial_plan
    return await generate_financial_plan(context=context, user_id=user_id, force_refresh=refresh)


@router.post("/plan")
async def post_financial_plan_endpoint(
    user_id: str = Depends(get_current_user_id),
    db: Neo4jService = Depends(get_neo4j_service),
):
    """
    Explicitly re-generate a personalized financial plan.
    """
    context = db.get_financial_context(user_id)
    if not context:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    from backend.app.services.financial_planner import generate_financial_plan
    return await generate_financial_plan(context=context, user_id=user_id, force_refresh=True)


