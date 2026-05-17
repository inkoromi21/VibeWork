"""Вход админа через POST /auth/email/login (логин без @)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_repo = Path(__file__).resolve().parents[2]
_backend = _repo / "miniapp" / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("ADMIN_LOGIN", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-admin-pass")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-admin-email-login")
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("COOKIE_SECURE", "0")

    import importlib

    import wibe_work.admin_auth as admin_auth_mod
    import wibe_work.config as cfg_mod
    import wibe_work.main as main_mod
    import wibe_work.routers.email_auth_routes as email_routes_mod

    importlib.reload(cfg_mod)
    importlib.reload(admin_auth_mod)
    importlib.reload(email_routes_mod)
    importlib.reload(main_mod)

    with TestClient(main_mod.app) as c:
        yield c


def test_email_login_accepts_admin_without_at(client: TestClient) -> None:
    r = client.post(
        "/auth/email/login",
        json={"email": "admin", "password": "test-admin-pass"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("admin") is True
    assert data.get("redirect") == "/admin"
