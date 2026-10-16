from fastapi import Depends, HTTPException, Request

from backend.app.api.auth import SESSION_COOKIE_NAME, get_session_user_id
from backend.app.database.neo4j_service import Neo4jService, get_neo4j_service
from backend.app.services.ingestion_service import IngestionService
from backend.app.rag.graph_rag import GraphRAG



def get_ingestion_service(
    db: Neo4jService = Depends(get_neo4j_service),
) -> IngestionService:
    return IngestionService(db=db)


def get_graph_rag(
    db: Neo4jService = Depends(get_neo4j_service),
) -> GraphRAG:
    return GraphRAG(db=db)


def get_current_user_id(request: Request) -> str:
    """Resolve identity exclusively from the signed, HTTP-only session cookie."""
    user_id = get_session_user_id(request.cookies.get(SESSION_COOKIE_NAME))
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id

