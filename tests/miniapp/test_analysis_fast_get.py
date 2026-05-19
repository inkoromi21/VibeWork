"""Быстрый GET разбора и статус без пересборки learning path."""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

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


def _register_user(client: TestClient) -> tuple[str, str]:
    from wibe_work.jwt_service import create_access_token
    from wibe_work.sqlite_db import get_db

    uid = "u_fast_" + uuid.uuid4().hex[:10]
    email = f"fast_{uuid.uuid4().hex[:8]}@example.com"
    pw_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("ascii")
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO email_users (user_id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (uid, email, pw_hash, now),
        )
        conn.commit()
    return uid, create_access_token(uid)


def _save_snapshot(uid: str, snap: dict) -> None:
    from wibe_work.sqlite_db import get_db

    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO vibework_snapshots (user_id, payload_json, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET payload_json = excluded.payload_json""",
            (uid, json.dumps(snap, ensure_ascii=False), now),
        )
        conn.commit()


def test_analysis_status_endpoint(client: TestClient) -> None:
    uid, token = _register_user(client)
    headers = {"Authorization": f"Bearer {token}"}

    r0 = client.get(f"/vibework/analysis/{uid}/status", headers=headers)
    assert r0.status_code == 200
    assert r0.json() == {"exists": False}

    _save_snapshot(
        uid,
        {
            "analyzed_at": "2026-01-01",
            "readiness": {"score": 50},
            "learning_path": {
                "path_id": "p1",
                "steps": [{"step_id": "s1", "order": 1, "title": "Шаг", "resources": []}],
            },
        },
    )
    r1 = client.get(f"/vibework/analysis/{uid}/status", headers=headers)
    assert r1.status_code == 200
    assert r1.json() == {"exists": True}


def test_get_analysis_skips_full_learning_rebuild(client: TestClient) -> None:
    uid, token = _register_user(client)
    headers = {"Authorization": f"Bearer {token}"}
    _save_snapshot(
        uid,
        {
            "analyzed_at": "2026-01-01",
            "readiness": {"score": 55, "label": "Средний"},
            "style_radar": {"axes": []},
            "learning_path": {
                "path_id": "it_backend_weak",
                "title": "Путь",
                "steps": [
                    {
                        "step_id": "step_1",
                        "order": 1,
                        "title": "Основы",
                        "goal": "Изучить",
                        "resources": [
                            {
                                "title": "Курс",
                                "url": "https://example.com/course",
                                "kind": "курс",
                            }
                        ],
                        "status": "pending",
                    }
                ],
                "metrics": {"total_steps": 1, "completed_steps": 0},
            },
            "learning": [
                {
                    "title": "Курс",
                    "url": "https://example.com/course",
                    "kind": "курс",
                }
            ],
        },
    )

    def _forbidden(*_a, **_kw):
        raise AssertionError("build_learning_for_analysis must not run on GET")

    with patch(
        "wibe_work.services.learning.engine.build_learning_for_analysis",
        side_effect=_forbidden,
    ):
        r = client.get(f"/vibework/analysis/{uid}", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body.get("readiness", {}).get("score") == 55
    assert body.get("learning_path", {}).get("path_id") == "it_backend_weak"


def test_merge_learning_progress_updates_status() -> None:
    from wibe_work.services.learning.engine import merge_learning_progress_in_snapshot
    from wibe_work.services.learning.progress import set_step_status

    uid = "u_merge_" + uuid.uuid4().hex[:8]
    snap = {
        "learning_path": {
            "path_id": "p_test",
            "steps": [
                {"step_id": "s1", "order": 1, "title": "A", "status": "pending"},
            ],
        }
    }
    set_step_status(uid, "p_test", "s1", "done")
    merged = merge_learning_progress_in_snapshot(snap, uid)
    steps = merged["learning_path"]["steps"]
    assert steps[0]["status"] == "done"
    assert merged["learning_path"]["metrics"]["completed_steps"] == 1
