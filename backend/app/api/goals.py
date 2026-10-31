from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from backend.app.core.money import normalize_rupees

from backend.app.api.deps import (
    get_current_user_id,
    get_ingestion_service,
    get_neo4j_service,
)
from backend.app.database.neo4j_service import Neo4jService
from backend.app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/api/goals", tags=["Goals"])


class GoalSchema(BaseModel):
    name: str = Field(..., description="Goal Name e.g. 'Emergency Fund'")
    target_amount: float = Field(..., description="Target Amount in ₹")
    current_amount: Optional[float] = Field(None, description="Current Saved Amount in ₹")
    target_date: Optional[str] = Field(None, description="Target Date in YYYY-MM-DD")

    @field_validator("target_amount", "current_amount", mode="before")
    @classmethod
    def _normalize_goal_amounts(cls, v):
        if v is None:
            return v
        try:
            return normalize_rupees(v)
        except Exception:
            return v


@router.get("")
def list_goals(
    user_id: str = Depends(get_current_user_id),
    db: Neo4jService = Depends(get_neo4j_service),
):
    context = db.get_financial_context(user_id)
    if not context:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    return {
        "goals": context.get("goals", []),
    }


@router.post("")
def create_or_update_goal(
    payload: GoalSchema,
    user_id: str = Depends(get_current_user_id),
    ingestion: IngestionService = Depends(get_ingestion_service),
):
    try:
        return ingestion.ingest_goal(
            user_id=user_id,
            name=payload.name,
            target_amount=payload.target_amount,
            current_amount=payload.current_amount,
            target_date=payload.target_date,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{goal_name}")
def delete_goal(
    goal_name: str,
    user_id: str = Depends(get_current_user_id),
    ingestion: IngestionService = Depends(get_ingestion_service),
):
    try:
        res = ingestion.remove_goal(user_id=user_id, name=goal_name)
        if not res.get("deleted"):
            raise HTTPException(status_code=404, detail=f"Goal '{goal_name}' not found")
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

