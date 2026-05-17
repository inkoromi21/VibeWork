"""Прогресс по шагам пути обучения."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from wibe_work.sqlite_db import get_db


def _migrate_learning_progress(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS learning_progress (
            user_id TEXT NOT NULL,
            path_id TEXT NOT NULL,
            step_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            updated_at TEXT NOT NULL,
            PRIMARY KEY (user_id, path_id, step_id)
        )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_learning_progress_user ON learning_progress(user_id)"
    )


def ensure_table() -> None:
    with get_db() as conn:
        _migrate_learning_progress(conn)
        conn.commit()


def get_progress_map(user_id: str, path_id: str) -> Dict[str, str]:
    ensure_table()
    with get_db() as conn:
        rows = conn.execute(
            """SELECT step_id, status FROM learning_progress
               WHERE user_id = ? AND path_id = ?""",
            (user_id, path_id),
        ).fetchall()
    return {str(r["step_id"]): str(r["status"]) for r in rows}


def set_step_status(user_id: str, path_id: str, step_id: str, status: str) -> None:
    if status not in ("pending", "in_progress", "done"):
        status = "pending"
    now = datetime.now(timezone.utc).isoformat()
    ensure_table()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO learning_progress (user_id, path_id, step_id, status, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(user_id, path_id, step_id) DO UPDATE SET
                 status = excluded.status,
                 updated_at = excluded.updated_at""",
            (user_id, path_id, step_id, status, now),
        )
        conn.commit()


def apply_progress_to_steps(
    steps: List[Dict[str, Any]], progress: Dict[str, str]
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for s in steps:
        sid = str(s.get("step_id") or "")
        row = dict(s)
        row["status"] = progress.get(sid, "pending")
        out.append(row)
    return out


def compute_metrics(steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(steps)
    done = sum(1 for s in steps if s.get("status") == "done")
    in_prog = sum(1 for s in steps if s.get("status") == "in_progress")
    current_idx = 0
    for i, s in enumerate(steps):
        if s.get("status") != "done":
            current_idx = i
            break
    else:
        current_idx = max(0, total - 1) if total else 0
    pct = int(round(100 * done / total)) if total else 0
    return {
        "total_steps": total,
        "completed_steps": done,
        "in_progress_steps": in_prog,
        "current_step_index": current_idx,
        "coverage_percent": pct,
    }
