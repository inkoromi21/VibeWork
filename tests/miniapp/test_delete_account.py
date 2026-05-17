"""Удаление аккаунта по DELETE /auth/account."""

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
def client():
    import wibe_work.main as main_mod

    with TestClient(main_mod.app) as c:
        yield c


def test_delete_account_removes_user(client: TestClient) -> None:
    from wibe_work.jwt_service import create_access_token
    from wibe_work.services.user_accounts import account_exists
    from wibe_work.sqlite_db import get_db

    uid = "u_del_" + uuid.uuid4().hex[:12]
    email = f"del_{uuid.uuid4().hex[:8]}@example.com"
    pw_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("ascii")
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO email_users (user_id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (uid, email, pw_hash, now),
        )
        conn.commit()
    token = create_access_token(uid)
    r = client.delete(
        "/auth/account",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json().get("ok") is True
    assert account_exists(uid) is False


def test_delete_account_requires_auth(client: TestClient) -> None:
    r = client.delete("/auth/account")
    assert r.status_code == 401
