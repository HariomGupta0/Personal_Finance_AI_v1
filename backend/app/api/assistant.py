from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.app.rag.graph_rag import GraphRAG
from backend.app.api.deps import get_current_user_id

router = APIRouter(prefix="/api/assistant", tags=["Assistant"])

# GraphRAG is instantiated once per process — Neo4j driver is reused.
graph_rag = GraphRAG()


class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        description="Natural language financial question",
        example="Can I spend ₹15,000 on a phone?",
        min_length=3,
        max_length=500,
    )


@router.post("/query")
def ask_assistant(
    request: Request,
    payload: QueryRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Process a natural language financial question through the GraphRAG pipeline.

    Rate limit: 20 requests per minute per IP address.
    Returns the LLM explanation, deterministic math result, evidence cards,
    per-stage latency breakdown, and LLM token usage.
    """
    try:
        result = graph_rag.process_query(
            question=payload.question,
            user_id=user_id,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
