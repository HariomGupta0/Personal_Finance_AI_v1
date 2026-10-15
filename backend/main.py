import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.app.core.logging_config import setup_logging
from backend.app.api.finance import router as finance_router
from backend.app.api.transactions import router as transactions_router
from backend.app.api.goals import router as goals_router
from backend.app.api.assistant import router as assistant_router
from backend.app.api.auth import router as auth_router
from backend.app.api.import_api import router as import_router
from backend.config import (
    GROQ_API_KEY, NEO4J_URI, NEO4J_DATABASE, SESSION_SECRET
)

# ── Startup validation ────────────────────────────────────────────────────────
if not SESSION_SECRET:
    raise RuntimeError(
        "SESSION_SECRET is not set. Add a strong random secret to your .env file.\n"
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )

# ── Logging ───────────────────────────────────────────────────────────────────
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))

# ── Rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Personal Finance AI Assistant API",
    description=(
        "Explainable personal finance assistant using Dynamic Knowledge Graphs "
        "and LLM-based GraphRAG. All financial calculations are deterministic — "
        "the LLM is used only for natural language explanation."
    ),
    version="1.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
_allowed_origins_env = os.getenv("CORS_ORIGINS", "")
_default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
origins = (
    [o.strip() for o in _allowed_origins_env.split(",") if o.strip()]
    if _allowed_origins_env
    else _default_origins
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(finance_router)
app.include_router(transactions_router)
app.include_router(goals_router)
app.include_router(assistant_router)
app.include_router(auth_router)
app.include_router(import_router)


# ── Health endpoint ───────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Deep health check: verifies Neo4j connectivity and LLM configuration.
    Returns HTTP 200 when all dependencies are healthy, HTTP 503 otherwise.
    """
    results: dict = {
        "api": "ONLINE",
        "neo4j": "UNKNOWN",
        "llm_configured": bool(GROQ_API_KEY),
        "neo4j_uri": NEO4J_URI,
        "neo4j_database": NEO4J_DATABASE,
    }
    try:
        from backend.app.database.neo4j_service import Neo4jService
        svc = Neo4jService()
        with svc.driver.session(database=NEO4J_DATABASE) as session:
            session.run("RETURN 1")
        svc.close()
        results["neo4j"] = "ONLINE"
    except Exception as exc:
        results["neo4j"] = f"ERROR: {type(exc).__name__}: {str(exc)[:120]}"

    is_healthy = results["neo4j"] == "ONLINE"
    return JSONResponse(content=results, status_code=200 if is_healthy else 503)


# ── Root redirect ─────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "ONLINE",
        "service": "Personal Finance AI Assistant API",
        "version": "1.1.0",
        "health_url": "/health",
        "docs_url": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
