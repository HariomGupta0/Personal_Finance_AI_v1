from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from backend.app.rag.graph_rag import GraphRAG
from backend.app.api.deps import get_current_user_id

router = APIRouter(prefix="/api/assistant", tags=["Assistant"])
graph_rag = GraphRAG()

class QueryRequest(BaseModel):
    question: str = Field(..., description="Natural language financial question", example="Can I spend ₹15000 on a phone?")

@router.post("/query")
def ask_assistant(payload: QueryRequest, user_id: str = Depends(get_current_user_id)):
    try:
        result = graph_rag.process_query(
            question=payload.question,
            user_id=user_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
