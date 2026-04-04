"""Cookie-сессии миниаппы в браузере (~30 дней), хранение токенов в SQLite."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from wibe_work.sqlite_db import get_db

COOKIE_NAME = "vibework_session"
SESSION_DAYS = 30


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_session(user_id: str) -> Tuple[str, datetime]:
    raw = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw)
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    exp_iso = expires.isoformat()
    with get_db() as conn:
        conn.execute("DELETE FROM vibework_sessions WHERE user_id = ?", (user_id,))
        conn.execute(
            """INSERT INTO vibework_sessions (token_hash, user_id, expires_at)
               VALUES (?, ?, ?)""",
            (token_hash, user_id, exp_iso),
        )
        conn.commit()
    return raw, expires


def delete_session_for_token(raw: Optional[str]) -> None:
    if not raw:
        return
    th = _hash_token(raw)
    with get_db() as conn:
        conn.execute("DELETE FROM vibework_sessions WHERE token_hash = ?", (th,))
        conn.commit()


def get_user_id_from_token(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    th = _hash_token(raw)
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        row = conn.execute(
            """SELECT user_id, expires_at FROM vibework_sessions WHERE token_hash = ?""",
            (th,),
        ).fetchone()
    if not row:
        return None
    try:
        exp = datetime.fromisoformat(str(row["expires_at"]).replace("Z", "+00:00"))
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None
    if datetime.now(timezone.utc) > exp:
        delete_session_for_token(raw)
        return None
    return str(row["user_id"])


def get_email_for_user(user_id: str) -> Optional[str]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT email FROM email_users WHERE user_id = ?", (user_id,)
        ).fetchone()
    return str(row["email"]) if row else None
