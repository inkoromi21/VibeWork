"""Проверка, что user_id соответствует зарегистрированному аккаунту в БД."""

from __future__ import annotations

from wibe_work.sqlite_db import get_db


def account_exists(user_id: str) -> bool:
    """Аккаунт есть, если привязан email или Telegram (не «осиротевший» JWT)."""
    uid = (user_id or "").strip()
    if not uid:
        return False
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT 1 WHERE EXISTS (SELECT 1 FROM email_users WHERE user_id = ?)
               OR EXISTS (SELECT 1 FROM telegram_users WHERE user_id = ?)
            """,
            (uid, uid),
        ).fetchone()
    return row is not None
