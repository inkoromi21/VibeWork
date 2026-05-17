"""Проверка и удаление зарегистрированных аккаунтов в БД."""

from __future__ import annotations

from wibe_work.sqlite_db import get_db

# Порядок: сначала зависимые таблицы, затем email_users / telegram_users / user_profiles.
_USER_DATA_TABLES = (
    "learning_progress",
    "ai_chat_sessions",
    "password_reset_tokens",
    "vibework_sessions",
    "vibework_snapshots",
    "user_hh_state",
    "user_competencies",
    "answers",
    "simulator_progress",
    "email_users",
    "telegram_users",
    "user_profiles",
)


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


def delete_user_account(user_id: str) -> bool:
    """Удалить все данные пользователя. False, если аккаунта не было."""
    uid = (user_id or "").strip()
    if not uid or not account_exists(uid):
        return False
    with get_db() as conn:
        existing = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        for table in _USER_DATA_TABLES:
            if table not in existing:
                continue
            conn.execute(f"DELETE FROM [{table}] WHERE user_id = ?", (uid,))
        conn.commit()
    return True
