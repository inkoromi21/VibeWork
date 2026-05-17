"""Сессия: JWT без записи в БД должен отклоняться."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

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


def test_session_rejects_orphan_jwt(client: TestClient) -> None:
    from wibe_work.jwt_service import create_access_token

    ghost_id = "u_" + uuid.uuid4().hex
    token = create_access_token(ghost_id)
    r = client.get(
        "/auth/session",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 401


def test_session_ok_for_registered_email_user(client: TestClient) -> None:
    from datetime import datetime, timezone

    import bcrypt

    from wibe_work.jwt_service import create_access_token
    from wibe_work.sqlite_db import get_db

    uid = "u_test_" + uuid.uuid4().hex[:12]
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    pw_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("ascii")
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO email_users (user_id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (uid, email, pw_hash, now),
        )
        conn.commit()
    token = create_access_token(uid)
    r = client.get(
        "/auth/session",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["user_id"] == uid
    assert data["email"] == email
