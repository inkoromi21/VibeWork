"""Синхронизация аккаунта Telegram и входа по почте: привязка, слияние данных."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Annotated, Any

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from wibe_work.api_schemas import EmailLoginBody, EmailRegisterBody
from wibe_work.bearer_auth import get_current_user_id_from_bearer
from wibe_work.jwt_service import create_access_token
from wibe_work.sqlite_db import get_db
from wibe_work.telegram_init_data import (
    check_telegram_auth,
    parse_init_data_user_fields,
    validate_webapp_init_data,
)
from wibe_work.routers.telegram_auth_routes import _get_or_create_user_id_for_telegram_id
from wibe_work.user_merge import merge_users_into_transaction

router = APIRouter(prefix="/auth/account", tags=["account"])


def _norm_email(email: str) -> str:
    return email.strip().lower()


def _user_id_for_email_password(email: str, password: str) -> str | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT user_id, password_hash FROM email_users WHERE email = ?",
            (email,),
        ).fetchone()
    if not row:
        return None
    try:
        ok = bcrypt.checkpw(
            password.encode("utf-8"),
            str(row["password_hash"]).encode("ascii"),
        )
    except (ValueError, TypeError):
        ok = False
    if not ok:
        return None
    return str(row["user_id"])


class TelegramInitBody(BaseModel):
    init_data: str = Field(..., min_length=1)


def _telegram_uid_for_telegram_id(conn, telegram_id: int) -> str | None:
    row = conn.execute(
        "SELECT user_id FROM telegram_users WHERE telegram_id = ?",
        (telegram_id,),
    ).fetchone()
    return str(row["user_id"]) if row and row["user_id"] else None


CurrentUser = Annotated[str, Depends(get_current_user_id_from_bearer)]


@router.get("/status")
async def account_status(current: CurrentUser):
    """Для UI: есть ли почта и привязан ли Telegram."""
    bot_username = os.environ.get("TELEGRAM_BOT_USERNAME", "").strip() or None
    with get_db() as conn:
        em = conn.execute(
            "SELECT email FROM email_users WHERE user_id = ?", (current,)
        ).fetchone()
        tg = conn.execute(
            "SELECT 1 FROM telegram_users WHERE user_id = ?", (current,)
        ).fetchone()
    return {
        "user_id": current,
        "email": str(em["email"]) if em and em["email"] else None,
        "telegram_linked": tg is not None,
        "telegram_login_bot_username": bot_username,
    }


@router.post("/email/register")
async def register_email_on_session(body: EmailRegisterBody, current: CurrentUser):
    """
    Добавить почту и пароль к текущему аккаунту (например вошли только через Telegram).
    Тот же user_id — данные анкеты и чата остаются на месте.
    """
    email = _norm_email(str(body.email))
    with get_db() as conn:
        if conn.execute(
            "SELECT 1 FROM email_users WHERE user_id = ?", (current,)
        ).fetchone():
            raise HTTPException(
                status_code=409,
                detail="У этого аккаунта уже есть почта.",
            )
        if conn.execute(
            "SELECT user_id FROM email_users WHERE email = ?", (email,)
        ).fetchone():
            raise HTTPException(
                status_code=409,
                detail="Этот email уже занят. Войдите под ним на сайте и привяжите Telegram.",
            )
        password_hash = bcrypt.hashpw(
            body.password.encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("ascii")
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """INSERT INTO email_users (user_id, email, password_hash, created_at)
               VALUES (?, ?, ?, ?)""",
            (current, email, password_hash, now),
        )
        conn.commit()
    token = create_access_token(current)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": current,
        "email": email,
    }


@router.post("/email/bind")
async def bind_existing_email_account(body: EmailLoginBody, current: CurrentUser):
    """
    Текущая сессия — Telegram (или второй аккаунт). Войти в существующий аккаунт по почте:
    объединяем данные в аккаунт с почтой и возвращаем JWT этого аккаунта.
    """
    email = _norm_email(str(body.email))
    with get_db() as conn:
        has_own_email = conn.execute(
            "SELECT 1 FROM email_users WHERE user_id = ?", (current,)
        ).fetchone()
    if has_own_email:
        raise HTTPException(
            status_code=409,
            detail="У этого аккаунта уже есть почта. Выйдите и войдите по почте.",
        )
    email_uid = _user_id_for_email_password(email, body.password)
    if not email_uid:
        raise HTTPException(status_code=401, detail="Неверный email или пароль.")
    if email_uid == current:
        token = create_access_token(current)
        return {
            "access_token": token,
            "user_id": current,
            "email": email,
            "merged": False,
        }
    merge_users_into_transaction(email_uid, current)
    token = create_access_token(email_uid)
    return {
        "access_token": token,
        "user_id": email_uid,
        "email": email,
        "merged": True,
    }


@router.post("/telegram/link")
async def link_telegram_webapp_init(body: TelegramInitBody, current: CurrentUser):
    """
    Текущая сессия — почта (браузер). Тело: initData из Telegram WebApp
    (например после открытия миниаппа в Telegram на том же устройстве недоступно;
    чаще используйте /telegram/widget с виджетом на странице).
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if bot_token and not validate_webapp_init_data(body.init_data, bot_token):
        raise HTTPException(status_code=403, detail="Неверная подпись init_data")
    tid, fn, un = parse_init_data_user_fields(body.init_data)
    if tid is None:
        raise HTTPException(400, detail="Не удалось разобрать init_data")
    with get_db() as conn:
        tg_uid = _telegram_uid_for_telegram_id(conn, int(tid))
    if not tg_uid:
        raise HTTPException(
            status_code=400,
            detail="Сначала откройте мини-приложение из бота в Telegram.",
        )
    if tg_uid == current:
        return {"ok": True, "merged": False}
    merge_users_into_transaction(current, tg_uid)
    return {"ok": True, "merged": True}


@router.post("/telegram/widget")
async def link_telegram_login_widget(request: Request, current: CurrentUser):
    """
    Telegram Login Widget на сайте: те же поля, что и у виджета (id, hash, …).
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    data: dict[str, Any] = await request.json()
    if not check_telegram_auth(data, bot_token):
        raise HTTPException(status_code=403, detail="Неверная подпись Telegram")
    tid = data.get("id")
    if tid is None:
        raise HTTPException(400, detail="Нужно поле id")
    tid = int(tid)
    fn = str(data.get("first_name") or "")
    un = str(data.get("username") or "")
    tg_uid = _get_or_create_user_id_for_telegram_id(tid, fn, un)
    if tg_uid == current:
        return {"ok": True, "merged": False}
    merge_users_into_transaction(current, tg_uid)
    return {"ok": True, "merged": True}
