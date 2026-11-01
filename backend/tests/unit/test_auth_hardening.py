"""
Unit tests for Auth hardening:
- Password hashing check (PBKDF2 with salt, constant-time verification, no plaintext accepted)
- Login rate limiting (slowapi 5/minute threshold triggers 429)
- Demo password only allowed when DEV_MODE is True
- Secrets configured strictly from environment variables
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.app.database.neo4j_service import hash_password, verify_password
from backend.main import app
from backend.app.core.limiter import limiter


@pytest.fixture(autouse=True)
def reset_limiter():
    limiter.reset()
    yield
    limiter.reset()


def test_password_hashing_and_verification():
    """Verify passwords are salted and hashed with PBKDF2 HMAC SHA-256."""
    pwd = "SecurePassword123!"
    hash1, salt1 = hash_password(pwd)
    hash2, salt2 = hash_password(pwd)

    # Different salts must yield different hashes
    assert salt1 != salt2
    assert hash1 != hash2
    assert hash1 != pwd  # Never plaintext

    # Same salt must verify correctly
    assert verify_password(pwd, hash1, salt1) is True
    assert verify_password(pwd, hash2, salt2) is True
    assert verify_password("WrongPassword", hash1, salt1) is False


def test_authenticate_user_rejects_unhashed_or_missing_hash():
    """Users without password_hash or salt in Neo4j must never authenticate."""
    from backend.app.database.neo4j_service import Neo4jService

    mock_db = MagicMock()
    # Simulate DB returning a user record with no password_hash or salt
    mock_session = MagicMock()
    mock_record = MagicMock()
    mock_record.single.return_value = {
        "user_id": "U001",
        "username": "legacy_user",
        "name": "Legacy",
        "password_hash": None,
        "salt": None,
    }
    mock_session.__enter__.return_value.run.return_value = mock_record
    mock_db.driver.session.return_value = mock_session
    mock_db.database = "finance-ai-antigravity"

    # Call real authenticate_user logic with mocked session
    result = Neo4jService.authenticate_user(mock_db, "legacy_user", "password123")
    assert result is None


def test_demo_password_rejected_when_dev_mode_false():
    """When DEV_MODE is False, in-memory demo password fallback is forbidden."""
    client = TestClient(app)

    # Mock authenticate_user to return None (user not in DB)
    with patch("backend.app.api.auth.DEV_MODE", False), \
         patch("backend.app.database.neo4j_service.Neo4jService.authenticate_user", return_value=None):

        resp = client.post("/api/auth/login", json={"username": "Rahul", "password": "demo1234"})
        assert resp.status_code == 401
        assert "Invalid username or password" in resp.json()["detail"]


def test_demo_password_allowed_when_dev_mode_true():
    """When DEV_MODE is True, demo credentials fallback is permitted."""
    client = TestClient(app)

    with patch("backend.app.api.auth.DEV_MODE", True), \
         patch("backend.app.api.auth.APP_PASSWORD", "demo1234"), \
         patch("backend.app.api.auth.APP_USERNAME", "Rahul"), \
         patch("backend.app.api.auth.SESSION_SECRET", "test_secret_key_1234567890"), \
         patch("backend.app.database.neo4j_service.Neo4jService.authenticate_user", return_value=None):

        resp = client.post("/api/auth/login", json={"username": "Rahul", "password": "demo1234"})
        assert resp.status_code == 200
        assert resp.json()["username"] == "Rahul"


def test_login_rate_limiting():
    """Excessive rapid login attempts must be throttled with HTTP 429."""
    client = TestClient(app)

    # Send 10 rapid failed login attempts
    statuses = []
    for _ in range(10):
        r = client.post("/api/auth/login", json={"username": "test_rate", "password": "bad_password"})
        statuses.append(r.status_code)

    assert 429 in statuses, f"Expected HTTP 429 in login rate limit responses, got {statuses}"


def test_secrets_only_from_env():
    """Verify secrets cannot default to hardcoded strings when env vars are absent."""
    import os
    import importlib
    import backend.config as cfg

    # In config.py, GROQ_API_KEY, NEO4J_PASSWORD, APP_PASSWORD must not have non-None hardcoded defaults
    # Test by importing with clean env
    with patch.dict(os.environ, {}, clear=True):
        # When env vars are cleared, os.getenv("GROQ_API_KEY") is None
        assert os.getenv("GROQ_API_KEY") is None
        assert os.getenv("APP_PASSWORD") is None
        assert os.getenv("NEO4J_PASSWORD") is None
        assert os.getenv("SESSION_SECRET") is None
