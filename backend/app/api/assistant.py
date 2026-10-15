from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.app.rag.graph_rag import GraphRAG
from backend.app.api.deps import get_current_user_id

router = APIRouter(prefix="/api/assistant", tags=["Assistant"])

# GraphRAG is instantiated once per process — Neo4j driver is reused.
graph_rag = GraphRAG()

# In-memory session conversation store: user_id -> list of turn dicts
_user_conversation_store: dict[str, list[dict]] = {}


class ConversationTurn(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Turn text content")


class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        description="Natural language financial question",
        json_schema_extra={"example": "Can I spend ₹15,000 on a phone?"},
        min_length=3,
        max_length=500,
    )
    history: list[ConversationTurn] = Field(
        default_factory=list,
        description="Optional client-managed history for multi-turn conversational follow-ups",
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
    Supports multi-turn follow-ups via client-provided history or server-side session memory.
    Returns the LLM explanation, deterministic math result, evidence cards,
    per-stage latency breakdown, and LLM token usage.
    """
    try:
        # Resolve conversation history: prefer client payload if provided, else use session cache
        if payload.history:
            history_list = [{"role": t.role, "content": t.content} for t in payload.history]
        else:
            history_list = _user_conversation_store.get(user_id, [])

        result = graph_rag.process_query(
            question=payload.question,
            user_id=user_id,
            conversation_history=history_list,
        )

        # Update server-side conversation store (keep last 6 turns)
        session_history = _user_conversation_store.setdefault(user_id, [])
        session_history.append({"role": "user", "content": payload.question})
        if result.get("explanation"):
            session_history.append({"role": "assistant", "content": result["explanation"]})
        _user_conversation_store[user_id] = session_history[-6:]

        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/clear-history")
def clear_conversation_history(user_id: str = Depends(get_current_user_id)):
    """
    Clear multi-turn conversational memory for the active user session.
    """
    _user_conversation_store.pop(user_id, None)
    return {"status": "success", "message": "Conversation history reset"}
