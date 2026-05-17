"""Вход администратора: логин и пароль из .env, сессия в httponly-cookie (JWT)."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Cookie, HTTPException, Response

from wibe_work import config as cfg
from wibe_work.config import JWT_SECRET

ADMIN_COOKIE = "vw_admin_session"
ADMIN_TOKEN_TYP = "admin"
ADMIN_SESSION_HOURS = cfg.ADMIN_SESSION_HOURS


def admin_credentials_configured() -> bool:
    return bool(cfg.ADMIN_LOGIN.strip() and cfg.ADMIN_PASSWORD)


def verify_admin_credentials(login: str, password: str) -> bool:
    if not admin_credentials_configured():
        return False
    ok_login = secrets.compare_digest(
        (login or "").strip(),
        cfg.ADMIN_LOGIN.strip(),
    )
    ok_pass = secrets.compare_digest(
        password or "",
        cfg.ADMIN_PASSWORD,
    )
    return ok_login and ok_pass


def create_admin_session_token() -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=ADMIN_SESSION_HOURS)
    return jwt.encode(
        {"typ": ADMIN_TOKEN_TYP, "exp": exp},
        JWT_SECRET,
        algorithm="HS256",
    )


def is_valid_admin_token(raw: Optional[str]) -> bool:
    if not raw:
        return False
    try:
        payload = jwt.decode(raw, JWT_SECRET, algorithms=["HS256"])
        return payload.get("typ") == ADMIN_TOKEN_TYP
    except jwt.PyJWTError:
        return False


def require_admin(
    vw_admin_session: Optional[str] = Cookie(default=None, alias=ADMIN_COOKIE),
) -> None:
    if not is_valid_admin_token(vw_admin_session):
        raise HTTPException(status_code=401, detail="Требуется вход администратора")


def set_admin_cookie(response: Response, token: str) -> None:
    secure = cfg.cookie_secure()
    response.set_cookie(
        key=ADMIN_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        path="/",
        secure=secure,
        max_age=ADMIN_SESSION_HOURS * 3600,
    )


def clear_admin_cookie(response: Response) -> None:
    secure = cfg.cookie_secure()
    response.delete_cookie(
        key=ADMIN_COOKIE,
        path="/",
        secure=secure,
    )
