import uuid
from datetime import datetime, timezone

import bcrypt
from fastapi import APIRouter, HTTPException

from wibe_work.jwt_service import create_access_token
from wibe_work.sqlite_db import get_db
from wibe_work.api_schemas import EmailLoginBody, EmailRegisterBody

router = APIRouter(prefix="/auth/email", tags=["auth_email"])


def _norm_email(email: str) -> str:
    return email.strip().lower()


@router.post("/register")
async def email_register(body: EmailRegisterBody):
    email = _norm_email(str(body.email))
    password_hash = bcrypt.hashpw(
        body.password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("ascii")
    user_id = "u_" + uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        dup = conn.execute(
            "SELECT user_id FROM email_users WHERE email = ?", (email,)
        ).fetchone()
        if dup:
            raise HTTPException(
                status_code=409,
                detail="Этот email уже зарегистрирован. Войдите.",
            )
        conn.execute(
            """INSERT INTO email_users (user_id, email, password_hash, created_at)
               VALUES (?, ?, ?, ?)""",
            (user_id, email, password_hash, now),
        )
        conn.execute(
            "INSERT OR IGNORE INTO user_profiles (user_id) VALUES (?)",
            (user_id,),
        )
        conn.commit()
    token = create_access_token(user_id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user_id,
        "email": email,
    }


@router.post("/login")
async def email_login(body: EmailLoginBody):
    email = _norm_email(str(body.email))
    with get_db() as conn:
        row = conn.execute(
            "SELECT user_id, password_hash FROM email_users WHERE email = ?",
            (email,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Аккаунт не найден.")
    try:
        ok = bcrypt.checkpw(
            body.password.encode("utf-8"),
            str(row["password_hash"]).encode("ascii"),
        )
    except (ValueError, TypeError):
        ok = False
    if not ok:
        raise HTTPException(status_code=401, detail="Неверный email или пароль.")
    user_id = row["user_id"]
    token = create_access_token(user_id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user_id,
        "email": email,
    }
