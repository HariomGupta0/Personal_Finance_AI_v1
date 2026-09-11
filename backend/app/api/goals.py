from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from backend.app.database.neo4j_service import Neo4jService
from backend.app.services.ingestion_service import IngestionService
from backend.app.api.deps import get_current_user_id

router = APIRouter(prefix="/api/goals", tags=["Goals"])
db = Neo4jService()
ingestion = IngestionService(db=db)

class GoalSchema(BaseModel):
    name: str = Field(..., description="Goal Name e.g. 'Emergency Fund'")
    target_amount: float = Field(..., description="Target Amount in ₹")
    current_amount: Optional[float] = Field(None, description="Current Saved Amount in ₹")
    target_date: Optional[str] = Field(None, description="Target Date in YYYY-MM-DD")

@router.get("")
def list_goals(user_id: str = Depends(get_current_user_id)):
    context = db.get_financial_context(user_id)
    if not context:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    return {
        "goals": context.get("goals", [])
    }

@router.post("")
def create_or_update_goal(payload: GoalSchema, user_id: str = Depends(get_current_user_id)):
    try:
        return ingestion.ingest_goal(
            user_id=user_id,
            name=payload.name,
            target_amount=payload.target_amount,
            current_amount=payload.current_amount,
            target_date=payload.target_date
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
