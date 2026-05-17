"""Чтение данных пользователей для админ-панели."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from wibe_work.services.ai_chat_sessions import get_messages, list_sessions
from wibe_work.services.career_analysis import public_analysis_payload
from wibe_work.services.learning.progress import ensure_table as ensure_learning_table
from wibe_work.services.simulator_progress import ensure_table as ensure_simulator_table, get_progress
from wibe_work.sqlite_db import get_db


def _row_to_dict(row) -> Dict[str, Any]:
    if row is None:
        return {}
    return {k: row[k] for k in row.keys()}


def list_users() -> List[Dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                u.user_id,
                e.email,
                e.created_at AS email_created_at,
                t.telegram_id,
                t.username AS telegram_username,
                t.first_name AS telegram_first_name,
                p.city,
                p.age,
                p.profile_completed,
                (SELECT COUNT(*) FROM ai_chat_sessions c WHERE c.user_id = u.user_id) AS chat_sessions,
                (SELECT 1 FROM vibework_snapshots s WHERE s.user_id = u.user_id LIMIT 1) AS has_analysis_snapshot
            FROM (
                SELECT user_id FROM email_users
                UNION SELECT user_id FROM telegram_users
                UNION SELECT user_id FROM user_profiles
            ) u
            LEFT JOIN email_users e ON e.user_id = u.user_id
            LEFT JOIN telegram_users t ON t.user_id = u.user_id
            LEFT JOIN user_profiles p ON p.user_id = u.user_id
            ORDER BY COALESCE(e.created_at, '') DESC, u.user_id
            """
        ).fetchall()

    out: List[Dict[str, Any]] = []
    for r in rows:
        d = _row_to_dict(r)
        d["profile_completed"] = bool(d.get("profile_completed"))
        d["has_analysis"] = bool(d.get("has_analysis_snapshot"))
        d["chat_sessions"] = int(d.get("chat_sessions") or 0)
        del d["has_analysis_snapshot"]
        out.append(d)
    return out


def _load_snapshot(user_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT payload_json, updated_at FROM vibework_snapshots WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if not row:
        return None
    try:
        data = json.loads(row["payload_json"] or "{}")
    except (json.JSONDecodeError, TypeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data["_snapshot_updated_at"] = row["updated_at"]
    return data


def _load_profile(user_id: str) -> Dict[str, Any]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)).fetchone()
    return _row_to_dict(row)


def _load_poll_answers(user_id: str) -> List[Dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT question_id, text_answer, choice_id
               FROM answers WHERE user_id = ?
               ORDER BY question_id, id""",
            (user_id,),
        ).fetchall()
    out: List[Dict[str, Any]] = []
    for r in rows:
        item: Dict[str, Any] = {"question_id": r["question_id"]}
        if r["text_answer"]:
            item["text"] = r["text_answer"]
        if r["choice_id"] is not None:
            item["choice_id"] = r["choice_id"]
        out.append(item)
    return out


def _load_learning_progress(user_id: str) -> List[Dict[str, Any]]:
    ensure_learning_table()
    with get_db() as conn:
        rows = conn.execute(
            """SELECT path_id, step_id, status, updated_at
               FROM learning_progress WHERE user_id = ?
               ORDER BY path_id, step_id""",
            (user_id,),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_user_detail(user_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        exists = conn.execute(
            """
            SELECT 1 FROM email_users WHERE user_id = ?
            UNION SELECT 1 FROM telegram_users WHERE user_id = ?
            UNION SELECT 1 FROM user_profiles WHERE user_id = ?
            LIMIT 1
            """,
            (user_id, user_id, user_id),
        ).fetchone()
    if not exists:
        return None

    ensure_simulator_table()

    with get_db() as conn:
        email_row = conn.execute(
            "SELECT email, created_at FROM email_users WHERE user_id = ?", (user_id,)
        ).fetchone()
        tg_row = conn.execute(
            "SELECT telegram_id, username, first_name, auth_date FROM telegram_users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        hh_row = conn.execute(
            "SELECT tests_completed, tests_completed_at, hh_area_id, updated_at FROM user_hh_state WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    snap = _load_snapshot(user_id)
    quiz_answers = list(snap.get("_quiz_answers") or []) if snap else []
    analysis = public_analysis_payload(snap) if snap else None

    chats: List[Dict[str, Any]] = []
    for meta in list_sessions(user_id, limit=50):
        sid = meta["session_id"]
        msgs = get_messages(user_id, sid) or []
        chats.append(
            {
                "session_id": sid,
                "title": meta.get("title"),
                "updated_at": meta.get("updated_at"),
                "message_count": meta.get("message_count"),
                "messages": msgs,
            }
        )

    sim = get_progress(user_id)

    return {
        "user_id": user_id,
        "email": email_row["email"] if email_row else None,
        "email_created_at": email_row["created_at"] if email_row else None,
        "telegram": _row_to_dict(tg_row) if tg_row else None,
        "profile": _load_profile(user_id),
        "poll_answers": _load_poll_answers(user_id),
        "quiz_answers": quiz_answers,
        "analysis": analysis,
        "analysis_snapshot_updated_at": snap.get("_snapshot_updated_at") if snap else None,
        "chat_sessions": chats,
        "simulator": sim,
        "learning_progress": _load_learning_progress(user_id),
        "hh_state": _row_to_dict(hh_row) if hh_row else None,
    }
