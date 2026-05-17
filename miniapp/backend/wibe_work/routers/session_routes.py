"""Проверка актуальности JWT-сессии (аккаунт существует в БД)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Request

from wibe_work.bearer_auth import get_current_user_id_from_bearer
from wibe_work.sqlite_db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


def _session_payload(user_id: str) -> dict[str, Any]:
    email: Optional[str] = None
    telegram: Optional[dict[str, Any]] = None
    with get_db() as conn:
        er = conn.execute(
            "SELECT email FROM email_users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if er:
            email = str(er["email"])
        tr = conn.execute(
            "SELECT telegram_id, username, first_name FROM telegram_users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if tr:
            telegram = {
                "telegram_id": int(tr["telegram_id"]),
                "username": tr["username"],
                "first_name": tr["first_name"],
            }
    return {
        "ok": True,
        "user_id": user_id,
        "email": email,
        "telegram": telegram,
    }


@router.get("/session")
async def auth_session(request: Request):
    """
    Проверка сессии при загрузке SPA: JWT валиден и аккаунт не удалён из БД.
    """
    user_id = get_current_user_id_from_bearer(request)
    return _session_payload(user_id)
