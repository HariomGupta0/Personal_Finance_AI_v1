from fastapi import HTTPException, Request

from backend.app.api.auth import SESSION_COOKIE_NAME, get_session_user_id

def get_current_user_id(request: Request) -> str:
    """Resolve identity exclusively from the signed, HTTP-only session cookie."""
    user_id = get_session_user_id(request.cookies.get(SESSION_COOKIE_NAME))
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id
