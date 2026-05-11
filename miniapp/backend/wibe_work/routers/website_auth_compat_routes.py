"""Вход и снимок профиля для веб-фронта: те же URL, что ожидает `website/frontend`.

Данные в SQLite миниаппы: email_users, vibework_sessions, vibework_snapshots."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import bcrypt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, Field, field_validator

from wibe_work import config as cfg
from wibe_work.password_input import sanitize_password_input
from wibe_work.sqlite_db import get_db
from wibe_work.telegram_init_data import parse_init_data_user_id

router = APIRouter(prefix="/api/auth", tags=["auth_compat"])

SESSION_COOKIE = "vw_session"
SESSION_DAYS = 30
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def _verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("ascii"))
    except (ValueError, TypeError):
        return False


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
    stored_result: dict[str, Any] | None = None


class LinkTelegramBody(BaseModel):
    init_data: str = Field(..., min_length=1, description="Telegram WebApp initData")


def _create_cookie_session(user_id: str) -> tuple[str, str]:
    """Return (raw_token, expires_iso). Stores hashed token in vibework_sessions."""
    raw = uuid.uuid4().hex + "_" + uuid.uuid4().hex
    # reuse implementation from cookie_sessions.py but keep this file self-contained
    import hashlib

    token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    expires = datetime.now(timezone.utc).timestamp() + SESSION_DAYS * 86400
    exp_iso = datetime.fromtimestamp(expires, tz=timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute("DELETE FROM vibework_sessions WHERE user_id = ?", (user_id,))
        conn.execute(
            """INSERT INTO vibework_sessions (token_hash, user_id, expires_at)
               VALUES (?, ?, ?)""",
            (token_hash, user_id, exp_iso),
        )
        conn.commit()
    return raw, exp_iso


def _user_id_from_cookie(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    import hashlib

    token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        row = conn.execute(
            "SELECT user_id, expires_at FROM vibework_sessions WHERE token_hash = ?",
            (token_hash,),
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
        # best-effort cleanup
        with get_db() as conn:
            conn.execute("DELETE FROM vibework_sessions WHERE token_hash = ?", (token_hash,))
            conn.commit()
        return None
    return str(row["user_id"])


def _clear_cookie(response: Response) -> None:
    # Secure — только при HTTPS (в проде обычно да).
    secure_flag = None
    if cfg.COOKIE_SECURE:
        secure_flag = cfg.COOKIE_SECURE.strip().lower() in ("1", "true", "yes", "y", "on")
    else:
        secure_flag = cfg.PUBLIC_BASE_URL.lower().startswith("https://")
    response.set_cookie(
        key=SESSION_COOKIE,
        value="",
        httponly=True,
        samesite="lax",
        secure=bool(secure_flag),
        max_age=0,
        path="/",
    )


def _set_cookie(response: Response, token: str) -> None:
    secure_flag = None
    if cfg.COOKIE_SECURE:
        secure_flag = cfg.COOKIE_SECURE.strip().lower() in ("1", "true", "yes", "y", "on")
    else:
        secure_flag = cfg.PUBLIC_BASE_URL.lower().startswith("https://")
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=bool(secure_flag),
        max_age=SESSION_DAYS * 86400,
        path="/",
    )


def _load_snapshot(user_id: str) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT payload_json FROM vibework_snapshots WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if not row:
        return None
    try:
        return json.loads(row["payload_json"])
    except (json.JSONDecodeError, TypeError):
        return {}


def _save_snapshot(user_id: str, payload: dict[str, Any]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    raw = json.dumps(payload, ensure_ascii=False)
    with get_db() as conn:
        conn.execute(
            """INSERT INTO vibework_snapshots (user_id, payload_json, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 payload_json = excluded.payload_json,
                 updated_at = excluded.updated_at""",
            (user_id, raw, now),
        )
        conn.commit()


def require_user_id(vw_session: str | None = Cookie(default=None)) -> str:
    uid = _user_id_from_cookie(vw_session)
    if not uid:
        raise HTTPException(status_code=401, detail="Нужно войти")
    return uid


@router.post("/register")
async def register(body: RegisterBody, response: Response):
    user_id = "u_" + uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    raw_pw = sanitize_password_input(body.password)
    if len(raw_pw) < 8:
        raise HTTPException(
            status_code=422,
            detail="Пароль не короче 8 символов.",
        )
    pw = _hash_password(raw_pw)
    with get_db() as conn:
        dup = conn.execute(
            "SELECT user_id FROM email_users WHERE email = ?",
            (body.email,),
        ).fetchone()
        if dup:
            raise HTTPException(status_code=409, detail="Email уже зарегистрирован")
        conn.execute(
            """INSERT INTO email_users (user_id, email, password_hash, created_at)
               VALUES (?, ?, ?, ?)""",
            (user_id, body.email, pw, now),
        )
        conn.execute(
            "INSERT OR IGNORE INTO user_profiles (user_id) VALUES (?)",
            (user_id,),
        )
        conn.commit()

    token, _exp_iso = _create_cookie_session(user_id)
    _set_cookie(response, token)
    return {"ok": True, "email": body.email}


@router.post("/login")
async def login(body: LoginBody, response: Response):
    raw_pw = sanitize_password_input(body.password)
    with get_db() as conn:
        row = conn.execute(
            "SELECT user_id, password_hash FROM email_users WHERE email = ?",
            (body.email,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Аккаунт не найден")
    if not _verify_password(raw_pw, str(row["password_hash"])):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    user_id = str(row["user_id"])
    token, _exp_iso = _create_cookie_session(user_id)
    _set_cookie(response, token)
    return {"ok": True, "email": body.email}


@router.post("/logout")
async def logout(response: Response, vw_session: str | None = Cookie(default=None)):
    if vw_session:
        import hashlib

        token_hash = hashlib.sha256(vw_session.encode("utf-8")).hexdigest()
        with get_db() as conn:
            conn.execute("DELETE FROM vibework_sessions WHERE token_hash = ?", (token_hash,))
            conn.commit()
    _clear_cookie(response)
    return {"ok": True}


@router.get("/me")
async def me(vw_session: str | None = Cookie(default=None)):
    user_id = _user_id_from_cookie(vw_session)
    if not user_id:
        return {"authenticated": False}
    with get_db() as conn:
        row = conn.execute(
            "SELECT email FROM email_users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    email = str(row["email"]) if row and row["email"] is not None else None
    snap = _load_snapshot(user_id)
    return {"authenticated": True, "email": email, "snapshot": snap}


@router.put("/snapshot")
async def put_snapshot(body: SnapshotUpdate, user_id: str = Depends(require_user_id)):
    existing = _load_snapshot(user_id) or {}
    incoming = body.model_dump(exclude_none=True)
    for k, v in incoming.items():
        existing[k] = v
    _save_snapshot(user_id, existing)
    return {"ok": True}


@router.post("/link/telegram")
async def link_telegram(body: LinkTelegramBody, user_id: str = Depends(require_user_id)):
    """
    Привязка Telegram к текущему (email) аккаунту.

    Делает telegram_users.user_id = текущий user_id и аккуратно переносит снапшот:
    - если у Telegram-аккаунта есть vibework_snapshots, мерджит ключи в текущий снапшот,
      не перетирая уже существующие ключи.
    """
    tid = parse_init_data_user_id(body.init_data)
    if tid is None:
        raise HTTPException(status_code=400, detail="Не удалось разобрать init_data")

    with get_db() as conn:
        tg = conn.execute(
            "SELECT telegram_id, user_id FROM telegram_users WHERE telegram_id = ?",
            (int(tid),),
        ).fetchone()
        tg_user_id = str(tg["user_id"]) if tg and tg["user_id"] is not None else None

    if tg_user_id and tg_user_id != user_id:
        from_snap = _load_snapshot(tg_user_id) or {}
        to_snap = _load_snapshot(user_id) or {}
        merged = dict(from_snap)
        merged.update(to_snap)  # приоритет текущего аккаунта
        _save_snapshot(user_id, merged)

    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO user_profiles (user_id) VALUES (?)",
            (user_id,),
        )
        # если записи ещё нет — создадим, сразу привязав к текущему user_id
        conn.execute(
            """INSERT OR REPLACE INTO telegram_users (telegram_id, user_id, first_name, username, auth_date)
               VALUES (?, ?, COALESCE((SELECT first_name FROM telegram_users WHERE telegram_id = ?), ''),
                          COALESCE((SELECT username FROM telegram_users WHERE telegram_id = ?), ''),
                          ?)""",
            (int(tid), user_id, int(tid), int(tid), now),
        )
        conn.commit()

    return {"ok": True, "user_id": user_id, "telegram_id": int(tid)}

