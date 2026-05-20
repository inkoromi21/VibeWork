"""Регистрация, вход, cookie-сессия, снимок данных пользователя."""

from __future__ import annotations

import datetime as dt
import json
import re
import secrets
from typing import Annotated, Any

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from passlib.context import CryptContext
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.orm_models import DbSessionToken, DbUser, DbUserSnapshot
from app.sqlite_async_session import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SESSION_COOKIE = "vw_session"
SESSION_DAYS = 30
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterBody(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def norm_email(cls, v: str) -> str:
        s = v.strip().lower()
        if not EMAIL_RE.match(s):
            raise ValueError("Некорректный email")
        return s


class LoginBody(RegisterBody):
    pass


class SnapshotUpdate(BaseModel):
    profile: dict[str, Any] | None = None
    analysis: dict[str, Any] | None = None
    test_answers: list[dict[str, Any]] | None = None
    personality_test_answers: list[dict[str, Any]] | None = None
    chat_messages: list[dict[str, Any]] | None = None
    last_tab: str | None = None
    stored_result: dict[str, Any] | None = Field(None, description="Как объект из localStorage: data + profile")


def _hash_password(raw: str) -> str:
    return pwd_context.hash(raw)


def _verify_password(raw: str, hashed: str) -> bool:
    return pwd_context.verify(raw, hashed)


def _new_token() -> str:
    return secrets.token_urlsafe(32)


async def _get_user_by_session(db: AsyncSession, token: str | None) -> DbUser | None:
    if not token:
        return None
    now = dt.datetime.now(dt.UTC)
    res = await db.execute(
        select(DbUser)
        .join(DbSessionToken, DbSessionToken.user_id == DbUser.id)
        .where(DbSessionToken.token == token, DbSessionToken.expires_at > now)
    )
    return res.scalar_one_or_none()


async def require_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    vw_session: Annotated[str | None, Cookie()] = None,
) -> DbUser:
    u = await _get_user_by_session(db, vw_session)
    if not u:
        raise HTTPException(status_code=401, detail="Нужно войти")
    return u


def _session_cookie_value(token: str, max_age: int) -> dict[str, Any]:
    return {
        "key": SESSION_COOKIE,
        "value": token,
        "httponly": True,
        "samesite": "lax",
        "max_age": max_age,
        "path": "/",
    }


def _clear_session_cookie() -> dict[str, Any]:
    return {
        "key": SESSION_COOKIE,
        "value": "",
        "httponly": True,
        "samesite": "lax",
        "max_age": 0,
        "path": "/",
    }


@router.post("/register")
async def register(body: RegisterBody, response: Response, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(DbUser).where(DbUser.email == body.email))
    if res.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email уже зарегистрирован")
    user = DbUser(email=body.email, password_hash=_hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = _new_token()
    exp = dt.datetime.now(dt.UTC) + dt.timedelta(days=SESSION_DAYS)
    db.add(DbSessionToken(token=token, user_id=user.id, expires_at=exp))
    await db.commit()

    response.set_cookie(**_session_cookie_value(token, SESSION_DAYS * 86400))
    return {"ok": True, "email": user.email, "onboarding": True}


@router.post("/login")
async def login(body: LoginBody, response: Response, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(DbUser).where(DbUser.email == body.email))
    user = res.scalar_one_or_none()
    if not user or not _verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")

    await db.execute(delete(DbSessionToken).where(DbSessionToken.user_id == user.id))
    token = _new_token()
    exp = dt.datetime.now(dt.UTC) + dt.timedelta(days=SESSION_DAYS)
    db.add(DbSessionToken(token=token, user_id=user.id, expires_at=exp))
    await db.commit()

    response.set_cookie(**_session_cookie_value(token, SESSION_DAYS * 86400))
    return {"ok": True, "email": user.email}


@router.post("/logout")
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_db),
    vw_session: Annotated[str | None, Cookie()] = None,
):
    if vw_session:
        await db.execute(delete(DbSessionToken).where(DbSessionToken.token == vw_session))
        await db.commit()
    response.set_cookie(**_clear_session_cookie())
    return {"ok": True}


@router.get("/me")
async def me(
    db: AsyncSession = Depends(get_db),
    vw_session: Annotated[str | None, Cookie()] = None,
):
    user = await _get_user_by_session(db, vw_session)
    if not user:
        return {"authenticated": False}
    snap_res = await db.execute(select(DbUserSnapshot).where(DbUserSnapshot.user_id == user.id))
    snap = snap_res.scalar_one_or_none()
    snapshot: dict[str, Any] | None = None
    if snap and snap.payload_json:
        try:
            snapshot = json.loads(snap.payload_json)
        except json.JSONDecodeError:
            snapshot = {}
    return {"authenticated": True, "email": user.email, "snapshot": snapshot}


@router.put("/snapshot")
async def put_snapshot(
    body: SnapshotUpdate,
    user: DbUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(DbUserSnapshot).where(DbUserSnapshot.user_id == user.id))
    row = res.scalar_one_or_none()
    existing: dict[str, Any] = {}
    if row:
        try:
            existing = json.loads(row.payload_json)
        except json.JSONDecodeError:
            existing = {}
    incoming = body.model_dump(exclude_none=True)
    for k, v in incoming.items():
        existing[k] = v
    raw = json.dumps(existing, ensure_ascii=False)
    if row:
        row.payload_json = raw
        row.updated_at = dt.datetime.now(dt.UTC)
    else:
        db.add(
            DbUserSnapshot(
                user_id=user.id,
                payload_json=raw,
                updated_at=dt.datetime.now(dt.UTC),
            )
        )
    await db.commit()
    return {"ok": True}
