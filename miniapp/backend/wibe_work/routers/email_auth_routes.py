import sqlite3
import uuid
from datetime import datetime, timezone

import bcrypt
from fastapi import APIRouter, HTTPException, Request

from wibe_work.bearer_auth import require_bearer_matches_user
from wibe_work.jwt_service import create_access_token
from wibe_work.miniapp_paths import PROJECT_ROOT
from wibe_work.sqlite_db import get_db
from wibe_work.api_schemas import EmailLoginBody, EmailPasswordChangeBody, EmailRegisterBody

router = APIRouter(prefix="/auth/email", tags=["auth_email"])

# Изолированный `website/main.py` (порт 8765) писал сюда; миниаппа — в miniapp/data/*.db
_LEGACY_ISOLATED_WEB_DB = PROJECT_ROOT / "website" / "data" / "vibework.db"


def _norm_email(email: str) -> str:
    return email.strip().lower()


def _verify_bcrypt_password(raw: str, stored_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            raw.encode("utf-8"),
            str(stored_hash).encode("ascii"),
        )
    except (ValueError, TypeError):
        return False


def _legacy_isolated_db_has_email(email: str) -> bool:
    if not _LEGACY_ISOLATED_WEB_DB.is_file():
        return False
    try:
        with sqlite3.connect(
            f"file:{_LEGACY_ISOLATED_WEB_DB.as_posix()}?mode=ro", uri=True
        ) as leg:
            r = leg.execute(
                "SELECT 1 FROM users WHERE lower(trim(email)) = ? LIMIT 1",
                (email,),
            ).fetchone()
        return r is not None
    except sqlite3.Error:
        return False


def _migrate_legacy_isolated_user_if_valid(email: str, password: str) -> str | None:
    """
    Переносит учётку из website/data/vibework.db в email_users при верном пароле.
    Возвращает новый user_id или None, если перенос не нужен / невозможен.
    """
    if not _LEGACY_ISOLATED_WEB_DB.is_file():
        return None
    leg = None
    row = None
    snap = None
    try:
        leg = sqlite3.connect(
            f"file:{_LEGACY_ISOLATED_WEB_DB.as_posix()}?mode=ro", uri=True
        )
        leg.row_factory = sqlite3.Row
        row = leg.execute(
            "SELECT id, password_hash FROM users WHERE lower(trim(email)) = ?",
            (email,),
        ).fetchone()
        if row:
            snap = leg.execute(
                "SELECT payload_json, updated_at FROM user_snapshots WHERE user_id = ?",
                (int(row["id"]),),
            ).fetchone()
    except sqlite3.OperationalError:
        return None
    finally:
        if leg is not None:
            try:
                leg.close()
            except Exception:
                pass
    if not row:
        return None
    if not _verify_bcrypt_password(password, str(row["password_hash"])):
        return None
    user_id = "u_" + uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    pw_hash = str(row["password_hash"])
    with get_db() as conn:
        exists = conn.execute(
            "SELECT user_id FROM email_users WHERE email = ?", (email,)
        ).fetchone()
        if exists:
            return str(exists["user_id"])
        conn.execute(
            """INSERT INTO email_users (user_id, email, password_hash, created_at)
               VALUES (?, ?, ?, ?)""",
            (user_id, email, pw_hash, now),
        )
        conn.execute(
            "INSERT OR IGNORE INTO user_profiles (user_id) VALUES (?)", (user_id,)
        )
        if snap and snap["payload_json"]:
            upd = snap["updated_at"]
            if upd is not None and not isinstance(upd, str):
                try:
                    upd = str(upd)
                except Exception:
                    upd = now
            elif upd is None:
                upd = now
            conn.execute(
                """INSERT OR REPLACE INTO vibework_snapshots (user_id, payload_json, updated_at)
                   VALUES (?, ?, ?)""",
                (user_id, str(snap["payload_json"]), upd),
            )
        conn.commit()
    return user_id


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
        if _legacy_isolated_db_has_email(email):
            raise HTTPException(
                status_code=409,
                detail="Этот email уже зарегистрирован на сайте. Войдите с тем же паролем — аккаунт подключится к мини-приложению.",
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
    if row:
        if not _verify_bcrypt_password(body.password, str(row["password_hash"])):
            raise HTTPException(
                status_code=401, detail="Неверный email или пароль."
            )
        user_id = str(row["user_id"])
    else:
        # Учётка могла быть создана только в изолированном website/data/vibework.db
        user_id = _migrate_legacy_isolated_user_if_valid(email, body.password)
        if not user_id:
            if _legacy_isolated_db_has_email(email):
                raise HTTPException(
                    status_code=401, detail="Неверный email или пароль."
                )
            raise HTTPException(status_code=401, detail="Аккаунт не найден.")
    token = create_access_token(user_id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user_id,
        "email": email,
    }


@router.post("/change-password/{user_id}")
async def email_change_password(
    user_id: str,
    request: Request,
    body: EmailPasswordChangeBody,
):
    require_bearer_matches_user(request, user_id)
    with get_db() as conn:
        row = conn.execute(
            "SELECT password_hash FROM email_users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if not row:
        raise HTTPException(
            status_code=404,
            detail="Пароль можно менять только для аккаунта с входом по почте.",
        )
    try:
        ok = bcrypt.checkpw(
            body.current_password.encode("utf-8"),
            str(row["password_hash"]).encode("ascii"),
        )
    except (ValueError, TypeError):
        ok = False
    if not ok:
        raise HTTPException(status_code=401, detail="Текущий пароль указан неверно.")
    new_hash = bcrypt.hashpw(
        body.new_password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("ascii")
    with get_db() as conn:
        conn.execute(
            "UPDATE email_users SET password_hash = ? WHERE user_id = ?",
            (new_hash, user_id),
        )
        conn.commit()
    return {"ok": True}
