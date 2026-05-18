"""После /auth/email/login веб-сайт видит сессию через cookie vw_session и /api/auth/me."""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import bcrypt
import pytest
from fastapi.testclient import TestClient

_repo = Path(__file__).resolve().parents[2]
_backend = _repo / "miniapp" / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-jwt-website-email-session-32b")
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("COOKIE_SECURE", "0")

    import importlib

    import wibe_work.config as cfg_mod
    import wibe_work.main as main_mod
    import wibe_work.routers.email_auth_routes as email_routes_mod
    import wibe_work.routers.website_auth_compat_routes as web_auth_mod

    importlib.reload(cfg_mod)
    importlib.reload(web_auth_mod)
    importlib.reload(email_routes_mod)
    importlib.reload(main_mod)

    with TestClient(main_mod.app) as c:
        yield c


def test_email_login_issues_website_cookie(client: TestClient) -> None:
    from wibe_work.sqlite_db import get_db

    email = f"site-{uuid.uuid4().hex[:8]}@example.com"
    password = "test-pass-12345"
    user_id = str(uuid.uuid4())
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    created = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO email_users (user_id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (user_id, email, pw_hash, created),
        )
        conn.commit()

    login = client.post(
        "/auth/email/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    assert login.json().get("access_token")

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    data = me.json()
    assert data.get("authenticated") is True
    assert data.get("email") == email
