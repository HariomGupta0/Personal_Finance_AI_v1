from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.app.api.deps import get_current_user_id, get_graph_rag
from backend.app.rag.graph_rag import GraphRAG
from backend.app.services.prompt_builder import list_prompt_versions

router = APIRouter(prefix="/api/assistant", tags=["Assistant"])

# In-memory session conversation store: user_id -> list of turn dicts
_user_conversation_store: dict[str, list[dict]] = {}


class ConversationTurn(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Turn text content", max_length=10000)


class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        description="Natural language financial question",
        json_schema_extra={"example": "Can I spend ₹15,000 on a phone?"},
        min_length=1,
        max_length=1000,
    )
    history: list[ConversationTurn] = Field(
        default_factory=list,
        description="Optional client-managed history for multi-turn conversational follow-ups",
    )
    prompt_version: str | None = Field(
        default=None,
        description="Optional prompt template version to use (e.g. 'v1.0', 'v1.1'). Defaults to system configured version.",
    )


def get_conversation_history(user_id: str) -> list[dict]:
    """Retrieve current session conversation history for a user."""
    return list(_user_conversation_store.get(user_id, []))


@router.post("/query")
async def ask_assistant(
    request: Request,
    payload: QueryRequest,
    user_id: str = Depends(get_current_user_id),
    graph_rag: GraphRAG = Depends(get_graph_rag),
):
    """
    Process a natural language financial question through the non-blocking async GraphRAG pipeline.

    Supports multi-turn follow-ups via client-provided history or server-side session memory.
    Always recalculates using current authorized financial data from the database.
    Distinguishes new questions from follow-ups and clarifies missing or ambiguous information.
    Previous assistant responses or user assertions in chat history are never treated as authoritative facts.
    """
    try:
        # Resolve conversation history: prefer client payload if provided, else use session cache
        if payload.history:
            history_list = []
            for t in payload.history:
                role = str(t.role).strip().lower()
                if role in ["user", "assistant"]:
                    history_list.append({"role": role, "content": str(t.content)[:1000]})
        else:
            history_list = _user_conversation_store.get(user_id, [])

        result = await graph_rag.process_query_async(
            question=payload.question,
            user_id=user_id,
            conversation_history=history_list,
            prompt_version=payload.prompt_version,
        )

        # Update server-side conversation store (keep last 6 turns, max 1000 chars per turn)
        session_history = _user_conversation_store.setdefault(user_id, [])
        session_history.append({"role": "user", "content": payload.question[:1000]})
        if result.get("explanation"):
            session_history.append({"role": "assistant", "content": result["explanation"][:1000]})
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


@router.get("/prompt-versions")
def get_prompt_versions():
    """
    List registered prompt template versions and indicate the active default.
    """
    return {"versions": list_prompt_versions()}


