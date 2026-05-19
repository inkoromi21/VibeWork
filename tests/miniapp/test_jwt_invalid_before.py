"""JWT_INVALID_BEFORE отклоняет старые токены."""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_repo = Path(__file__).resolve().parents[2]
_backend = _repo / "miniapp" / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))


def test_old_token_rejected_after_invalid_before(monkeypatch) -> None:
    future = (datetime.now(timezone.utc) + timedelta(minutes=5)).replace(microsecond=0).isoformat()
    monkeypatch.setenv("JWT_INVALID_BEFORE", future)
    monkeypatch.setenv("JWT_SECRET", "test-secret-invalid-before")

    import importlib

    import wibe_work.config as cfg_mod
    import wibe_work.jwt_service as jwt_mod

    importlib.reload(cfg_mod)
    importlib.reload(jwt_mod)

    old_token = jwt_mod.create_access_token("u_old")
    assert jwt_mod.decode_token_subject(old_token) is None

    monkeypatch.setenv("JWT_INVALID_BEFORE", "")
    importlib.reload(cfg_mod)
    importlib.reload(jwt_mod)
    new_token = jwt_mod.create_access_token("u_new")
    assert jwt_mod.decode_token_subject(new_token) == "u_new"
