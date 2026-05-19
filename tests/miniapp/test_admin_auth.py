"""Админ-панель: вход и защита API."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_repo = Path(__file__).resolve().parents[2]
_backend = _repo / "miniapp" / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))


@pytest.fixture()
def admin_client(monkeypatch):
    monkeypatch.setenv("ADMIN_LOGIN", "testadmin")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-secret-pass")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-for-admin-tests-only")
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("COOKIE_SECURE", "0")

    import importlib

    import wibe_work.admin_auth as admin_auth_mod
    import wibe_work.config as cfg_mod
    import wibe_work.main as main_mod
    import wibe_work.routers.admin_routes as admin_routes_mod

    importlib.reload(cfg_mod)
    importlib.reload(admin_auth_mod)
    importlib.reload(admin_routes_mod)
    importlib.reload(main_mod)

    with TestClient(main_mod.app) as client:
        yield client


def test_admin_login_and_users_list(admin_client: TestClient) -> None:
    r = admin_client.post(
        "/admin/api/login",
        json={"login": "testadmin", "password": "test-secret-pass"},
    )
    assert r.status_code == 200
    assert r.json().get("ok") is True

    me = admin_client.get("/admin/api/me")
    assert me.status_code == 200
    assert me.json().get("authenticated") is True

    users = admin_client.get("/admin/api/users")
    assert users.status_code == 200
    assert "users" in users.json()


def test_admin_rejects_wrong_password(admin_client: TestClient) -> None:
    r = admin_client.post(
        "/admin/api/login",
        json={"login": "testadmin", "password": "wrong"},
    )
    assert r.status_code == 401


def test_admin_users_requires_auth(admin_client: TestClient) -> None:
    admin_client.cookies.clear()
    r = admin_client.get("/admin/api/users")
    assert r.status_code == 401


def test_admin_delete_user(admin_client: TestClient) -> None:
    import uuid
    from datetime import datetime, timezone

    import bcrypt

    from wibe_work.services.user_accounts import account_exists
    from wibe_work.sqlite_db import get_db

    admin_client.post(
        "/admin/api/login",
        json={"login": "testadmin", "password": "test-secret-pass"},
    )
    uid = "u_adm_del_" + uuid.uuid4().hex[:10]
    email = f"adm_del_{uuid.uuid4().hex[:8]}@example.com"
    pw_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("ascii")
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO email_users (user_id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (uid, email, pw_hash, now),
        )
        conn.commit()
    assert account_exists(uid)

    r = admin_client.delete(f"/admin/api/users/{uid}")
    assert r.status_code == 200
    assert r.json().get("ok") is True
    assert account_exists(uid) is False

    r404 = admin_client.delete(f"/admin/api/users/{uid}")
    assert r404.status_code == 404
