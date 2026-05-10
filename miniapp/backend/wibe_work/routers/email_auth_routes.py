import hashlib
import logging
import secrets
import sqlite3
import time
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, HTTPException, Request

from wibe_work.bearer_auth import require_bearer_matches_user
from wibe_work.config import PUBLIC_BASE_URL
from wibe_work.jwt_service import create_access_token
from wibe_work.miniapp_paths import PROJECT_ROOT
from wibe_work.services.smtp_send import smtp_missing_keys
from wibe_work.sqlite_db import get_db
from wibe_work.api_schemas import (
    EmailForgotPasswordBody,
    EmailLoginBody,
    EmailPasswordChangeBody,
    EmailRegisterBody,
    EmailResetPasswordBody,
)
from wibe_work.password_input import sanitize_password_input
from wibe_work.services.transactional_email import (
    send_transactional_email,
    transactional_email_configured,
)

router = APIRouter(prefix="/auth/email", tags=["auth_email"])
_log = logging.getLogger(__name__)

_FORGOT_COOLDOWN_SEC = 90
_forgot_last_by_email: dict[str, float] = {}

_FORGOT_PUBLIC_MESSAGE = "Ссылка для сброса пароля отправлена."

# Изолированный `website/main.py` (порт 8765) писал сюда; миниаппа — в miniapp/data/*.db
_LEGACY_ISOLATED_WEB_DB = PROJECT_ROOT / "website" / "data" / "vibework.db"


def _norm_email(email: str) -> str:
    return email.strip().lower()


def _forgot_rate_check(email: str) -> bool:
    """Проверка интервала без записи — cooldown ставим только после успешной отправки или «тихого» ok."""
    now = time.time()
    last = _forgot_last_by_email.get(email, 0.0)
    return now - last >= _FORGOT_COOLDOWN_SEC


def _forgot_rate_commit(email: str) -> None:
    _forgot_last_by_email[email] = time.time()


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
    pw = sanitize_password_input(body.password)
    if len(pw) < 8:
        raise HTTPException(
            status_code=422,
            detail="Пароль не короче 8 символов (проверьте пробелы по краям).",
        )
    password_hash = bcrypt.hashpw(
        pw.encode("utf-8"),
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


@router.post("/forgot-password")
async def email_forgot_password(body: EmailForgotPasswordBody):
    """Запрос сброса: одно письмо на Mailgun; ответ одинаковый, если email не в базе."""
    email = _norm_email(str(body.email))
    if not _forgot_rate_check(email):
        raise HTTPException(
            status_code=429,
            detail="Подождите около минуты перед повторной отправкой.",
        )

    with get_db() as conn:
        row = conn.execute(
            "SELECT user_id FROM email_users WHERE email = ?",
            (email,),
        ).fetchone()

    if not row:
        _forgot_rate_commit(email)
        return {"ok": True, "message": _FORGOT_PUBLIC_MESSAGE}

    if not transactional_email_configured():
        miss = smtp_missing_keys()
        env_hint = (
            f" Не заданы: {', '.join(miss)}."
            if miss
            else " Заполните SMTP или Mailgun."
        )
        _log.warning(
            "forgot-password 503: почта не настроена email=%s missing_keys=%s project_root=%s",
            email,
            miss or [],
            PROJECT_ROOT,
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "Почта не настроена в этом процессе API."
                + env_hint
                + f" Ожидается файл {PROJECT_ROOT / '.env'} (рядом с папкой miniapp). "
                "Перезапустите uvicorn после правок. "
                "Проверка: GET /api/health/email"
            ),
        )

    user_id = str(row["user_id"])
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=1)

    with get_db() as conn:
        conn.execute(
            "DELETE FROM password_reset_tokens WHERE user_id = ? AND used_at IS NULL",
            (user_id,),
        )
        conn.execute(
            """INSERT INTO password_reset_tokens
               (user_id, token_hash, expires_at, used_at, created_at)
               VALUES (?, ?, ?, NULL, ?)""",
            (user_id, token_hash, expires.isoformat(), now.isoformat()),
        )
        conn.commit()

    reset_url = f"{PUBLIC_BASE_URL}/reset-password?token={raw_token}"
    subject = "VibeWork — сброс пароля"
    text_body = (
        "Здравствуйте.\n\n"
        f"Чтобы задать новый пароль, перейдите по ссылке (действует 1 час):\n{reset_url}\n\n"
        "Если вы не запрашивали сброс, проигнорируйте это письмо.\n"
    )
    html_body = (
        "<p>Здравствуйте.</p>"
        "<p>Чтобы задать новый пароль, нажмите на кнопку ниже (ссылка действует 1 час).</p>"
        f'<p><a href="{reset_url}" style="color:#166534;font-weight:600;">Сбросить пароль</a></p>'
        "<p style=\"color:#666;font-size:14px;\">Если вы не запрашивали сброс — удалите письмо.</p>"
    )

    ok, err_msg = await send_transactional_email(email, subject, text_body, html_body)
    if not ok:
        _log.warning(
            "forgot-password 503: отправка не удалась email=%s err=%s",
            email,
            err_msg or "",
        )
        with get_db() as conn:
            conn.execute(
                "DELETE FROM password_reset_tokens WHERE token_hash = ?",
                (token_hash,),
            )
            conn.commit()
        raise HTTPException(
            status_code=503,
            detail=(
                "Не удалось отправить письмо."
                + (f" {err_msg}" if err_msg else " Попробуйте позже.")
            ),
        )

    _forgot_rate_commit(email)
    return {"ok": True, "message": _FORGOT_PUBLIC_MESSAGE}


@router.post("/reset-password")
async def email_reset_password(body: EmailResetPasswordBody):
    """Установка нового пароля по одноразовому токену из письма."""
    raw = (body.token or "").strip()
    new_pw = sanitize_password_input(body.new_password)
    if len(new_pw) < 8:
        raise HTTPException(
            status_code=422,
            detail="Пароль не короче 8 символов (проверьте пробелы по краям).",
        )

    token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        row = conn.execute(
            """SELECT id, user_id, expires_at, used_at FROM password_reset_tokens
               WHERE token_hash = ?""",
            (token_hash,),
        ).fetchone()

    if not row or row["used_at"]:
        raise HTTPException(
            status_code=400,
            detail="Ссылка недействительна или уже использована. Запросите новую.",
        )

    exp_raw = str(row["expires_at"])
    try:
        exp = datetime.fromisoformat(exp_raw.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Ссылка недействительна. Запросите новую.",
        )
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > exp:
        raise HTTPException(
            status_code=400,
            detail="Срок действия ссылки истёк. Запросите сброс пароля снова.",
        )

    user_id = str(row["user_id"])
    new_hash = bcrypt.hashpw(
        new_pw.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("ascii")

    with get_db() as conn:
        conn.execute(
            "UPDATE email_users SET password_hash = ? WHERE user_id = ?",
            (new_hash, user_id),
        )
        conn.execute(
            "UPDATE password_reset_tokens SET used_at = ? WHERE id = ?",
            (now_iso, row["id"]),
        )
        conn.commit()

    return {"ok": True}


@router.post("/login")
async def email_login(body: EmailLoginBody):
    email = _norm_email(str(body.email))
    pw = sanitize_password_input(body.password)
    with get_db() as conn:
        row = conn.execute(
            "SELECT user_id, password_hash FROM email_users WHERE email = ?",
            (email,),
        ).fetchone()
    if row:
        if not _verify_bcrypt_password(pw, str(row["password_hash"])):
            raise HTTPException(
                status_code=401, detail="Неверный email или пароль."
            )
        user_id = str(row["user_id"])
    else:
        # Учётка могла быть создана только в изолированном website/data/vibework.db
        user_id = _migrate_legacy_isolated_user_if_valid(email, pw)
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
    cur_pw = sanitize_password_input(body.current_password)
    new_pw = sanitize_password_input(body.new_password)
    if len(new_pw) < 8:
        raise HTTPException(
            status_code=422,
            detail="Новый пароль — не короче 8 символов.",
        )
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
            cur_pw.encode("utf-8"),
            str(row["password_hash"]).encode("ascii"),
        )
    except (ValueError, TypeError):
        ok = False
    if not ok:
        raise HTTPException(status_code=401, detail="Текущий пароль указан неверно.")
    new_hash = bcrypt.hashpw(
        new_pw.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("ascii")
    with get_db() as conn:
        conn.execute(
            "UPDATE email_users SET password_hash = ? WHERE user_id = ?",
            (new_hash, user_id),
        )
        conn.commit()
    return {"ok": True}
