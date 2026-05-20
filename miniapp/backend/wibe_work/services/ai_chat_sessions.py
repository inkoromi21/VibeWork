"""Сохранение диалогов с карьерным ИИ (SQLite)."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

from wibe_work.sqlite_db import get_db
from wibe_work.services.llm_client import fetch_llm_completion, llm_configured
from wibe_work.services.llm_prompts import chat_session_title_system_for_grade
from wibe_work.services.profile_analysis_context import education_grade as profile_education_grade
from wibe_work.services.user_context import load_profile

logger = logging.getLogger(__name__)

_TITLE_MAX_LEN = 56

_GREETING_ONE_WORD = frozenset(
    {
        "привет",
        "здравствуйте",
        "добрый день",
        "добрый вечер",
        "hello",
        "hi",
        "hey",
        "qq",
    }
)


def _now_ts() -> int:
    return int(time.time())


def _has_assistant_reply(messages: List[Dict[str, Any]]) -> bool:
    return any((m.get("role") or "").strip() == "assistant" for m in messages)


def _should_try_topic_title(messages: List[Dict[str, Any]]) -> bool:
    """Тему из диалога имеет смысл просить у модели после хотя бы одной реплики ассистента."""
    if len(messages) < 2:
        return False
    return _has_assistant_reply(messages)


def _sanitize_title(raw: str) -> str:
    s = raw.strip()
    s = re.sub(r"^[\s\"«»„''`\-–—:]+|[\s\"«»„''`:]+$", "", s)
    s = s.split("\n")[0].strip()
    if len(s) > _TITLE_MAX_LEN:
        s = s[: _TITLE_MAX_LEN - 1].rstrip() + "…"
    return s if s else ""


def _build_dialog_excerpt(messages: List[Dict[str, Any]], *, max_msgs: int = 24, max_chars_per_msg: int = 480) -> str:
    lines: List[str] = []
    slice_msgs = messages[-max_msgs:] if len(messages) > max_msgs else messages
    for m in slice_msgs:
        role = (m.get("role") or "").strip()
        content = str(m.get("content", "")).strip().replace("\n", " ")
        if not content:
            continue
        if len(content) > max_chars_per_msg:
            content = content[: max_chars_per_msg - 1] + "…"
        if role == "user":
            lines.append(f"Пользователь: {content}")
        elif role == "assistant":
            lines.append(f"Ассистент: {content}")
    return "\n".join(lines)


def _title_from_llm(
    messages: List[Dict[str, Any]], *, education_grade: str = "university"
) -> Optional[str]:
    if not llm_configured():
        return None
    excerpt = _build_dialog_excerpt(messages)
    if len(excerpt.strip()) < 12:
        return None
    text, err = fetch_llm_completion(
        (
            "Ниже фрагмент диалога пользователя с карьерным консультантом VibeWork.\n"
            "Составь заголовок для списка чатов по правилам из system.\n\n"
            f"--- ДИАЛОГ ---\n{excerpt}\n--- КОНЕЦ ---\n\n"
            "Выведи только одну строку заголовка."
        ),
        max_tokens=80,
        temperature=0.2,
        system_prompt=chat_session_title_system_for_grade(education_grade),
    )
    if err:
        logger.debug("Заголовок чата LLM: %s", err)
    if not text:
        return None
    title = _sanitize_title(text)
    if len(title) < 3:
        return None
    return title


def _is_greeting_only(text: str) -> bool:
    t = text.strip().lower().strip("!.… ")
    if not t:
        return True
    if t in _GREETING_ONE_WORD:
        return True
    if len(t) <= 10 and t.split()[0] in _GREETING_ONE_WORD:
        return True
    return False


def _first_substantive_user_line(messages: List[Dict[str, Any]]) -> str:
    """Первая содержательная реплика пользователя (не только приветствие)."""
    for m in messages:
        if (m.get("role") or "").strip() != "user":
            continue
        t = str(m.get("content", "")).strip().replace("\n", " ")
        if not t:
            continue
        if _is_greeting_only(t):
            continue
        return t
    return ""


def _title_fallback(messages: List[Dict[str, Any]]) -> str:
    """Без LLM: не дублировать голое «Привет» — взять следующую содержательную реплику или общий ярлык."""
    sub = _first_substantive_user_line(messages)
    if sub:
        return (sub[: _TITLE_MAX_LEN - 1] + "…") if len(sub) > _TITLE_MAX_LEN else sub
    for m in messages:
        if (m.get("role") or "").strip() == "user":
            t = str(m.get("content", "")).strip().replace("\n", " ")
            if t:
                if _is_greeting_only(t):
                    return "Новый диалог"
                return (t[: _TITLE_MAX_LEN - 1] + "…") if len(t) > _TITLE_MAX_LEN else t
    return "Диалог"


def compute_session_title(
    messages: List[Dict[str, Any]],
    previous_title: Optional[str],
    *,
    education_grade: str = "university",
) -> str:
    if _should_try_topic_title(messages):
        generated = _title_from_llm(messages, education_grade=education_grade)
        if generated:
            return generated
        if previous_title and previous_title.strip() not in ("", "Диалог", "Новый диалог"):
            return previous_title.strip()
    return _title_fallback(messages)


def upsert_session(user_id: str, session_id: str, messages: List[Dict[str, Any]]) -> None:
    previous_title: Optional[str] = None
    with get_db() as conn:
        row = conn.execute(
            "SELECT title FROM ai_chat_sessions WHERE session_id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()
        if row:
            previous_title = str(row["title"] or "").strip() or None

    profile = load_profile(user_id) or {}
    grade = profile_education_grade(profile)
    title = compute_session_title(messages, previous_title, education_grade=grade)
    payload = json.dumps(messages, ensure_ascii=False)
    now = _now_ts()
    with get_db() as conn:
        row = conn.execute(
            "SELECT created_at FROM ai_chat_sessions WHERE session_id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()
        if row:
            conn.execute(
                """UPDATE ai_chat_sessions SET title = ?, messages_json = ?, updated_at = ?
                   WHERE session_id = ? AND user_id = ?""",
                (title, payload, now, session_id, user_id),
            )
        else:
            conn.execute(
                """INSERT INTO ai_chat_sessions (session_id, user_id, title, messages_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (session_id, user_id, title, payload, now, now),
            )
        conn.commit()


def list_sessions(user_id: str, *, limit: int = 40) -> List[Dict[str, Any]]:
    lim = max(1, min(100, limit))
    with get_db() as conn:
        rows = conn.execute(
            """SELECT session_id, title, messages_json, created_at, updated_at
               FROM ai_chat_sessions WHERE user_id = ?
               ORDER BY updated_at DESC LIMIT ?""",
            (user_id, lim),
        ).fetchall()
    out: List[Dict[str, Any]] = []
    for r in rows:
        mid = str(r["session_id"])
        raw = r["messages_json"] or "[]"
        try:
            msgs = json.loads(raw)
            n = len(msgs) if isinstance(msgs, list) else 0
        except (json.JSONDecodeError, TypeError):
            n = 0
        out.append(
            {
                "session_id": mid,
                "title": r["title"] or "Диалог",
                "created_at": int(r["created_at"]),
                "updated_at": int(r["updated_at"]),
                "message_count": n,
            }
        )
    return out


def get_messages(user_id: str, session_id: str) -> Optional[List[Dict[str, Any]]]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT messages_json FROM ai_chat_sessions WHERE session_id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()
    if not row:
        return None
    try:
        data = json.loads(row["messages_json"] or "[]")
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []
