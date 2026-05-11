import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from wibe_work import config as cfg
from wibe_work.jwt_service import create_access_token
from wibe_work.telegram_init_data import (
    check_telegram_auth,
    parse_init_data_user_fields,
    validate_webapp_init_data,
)
from wibe_work.sqlite_db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_or_create_user_id_for_telegram_id(tid: int, first_name: str, username: str) -> str:
    """
    Telegram -> internal user_id mapping.

    Раньше user_id был вида tg_{tid}. Для склейки данных между сайт/miniapp/ботом
    нам нужен стабильный internal user_id, хранимый в telegram_users.user_id.
    """
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        row = conn.execute(
            "SELECT user_id FROM telegram_users WHERE telegram_id = ?",
            (tid,),
        ).fetchone()
        if row and row["user_id"]:
            user_id = str(row["user_id"])
        else:
            import uuid

            user_id = "u_" + uuid.uuid4().hex
        conn.execute(
            "INSERT OR IGNORE INTO user_profiles (user_id) VALUES (?)",
            (user_id,),
        )
        conn.execute(
            """INSERT OR REPLACE INTO telegram_users (telegram_id, user_id, first_name, username, auth_date)
               VALUES (?, ?, ?, ?, ?)""",
            (tid, user_id, first_name or "", username or "", now),
        )
        conn.commit()
    return user_id


def _upsert_tg_user(telegram_id: int, first_name: str, username: str, user_key: str) -> None:
    """Старый хелпер; живёт для старых импортов — новый код через `_get_or_create_user_id_for_telegram_id`."""
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO user_profiles (user_id) VALUES (?)",
            (user_key,),
        )
        conn.execute(
            """INSERT OR REPLACE INTO telegram_users (telegram_id, user_id, first_name, username, auth_date)
               VALUES (?, ?, ?, ?, ?)""",
            (telegram_id, user_key, first_name or "", username or "", now),
        )
        conn.commit()


@router.post("/telegram/")
async def auth_telegram(data: dict):
    """
    Мини-апп Telegram: { "init_data": "<строка из Telegram.WebApp.initData>" } —
    проверка подписи и JWT как у входа по почте.

    Виджет Login в теле запроса (поля id, hash, …) — прежняя схема с проверкой hash.
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    init_data = data.get("init_data")
    if init_data:
        if not isinstance(init_data, str):
            raise HTTPException(400, detail="init_data должен быть строкой")
        require_tg = True
        if cfg.REQUIRE_TELEGRAM_BOT_TOKEN.strip():
            require_tg = cfg.REQUIRE_TELEGRAM_BOT_TOKEN.strip().lower() in ("1", "true", "yes", "y", "on")
        elif cfg.VIBEWORK_ENV != "prod":
            require_tg = False

        if require_tg and not bot_token:
            raise HTTPException(
                status_code=503,
                detail="TELEGRAM_BOT_TOKEN не настроен на сервере (в prod подпись Telegram обязательна).",
            )

        if bot_token and not validate_webapp_init_data(init_data, bot_token):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Неверная подпись Mini App (init_data). Проверьте в .env TELEGRAM_BOT_TOKEN "
                    "— он должен быть от того же бота, через которого открыто приложение; "
                    "после смены токена перезапустите API."
                ),
            )
        tid, fn, un = parse_init_data_user_fields(init_data)
        if tid is None:
            raise HTTPException(400, detail="Не удалось разобрать init_data")
        user_id = _get_or_create_user_id_for_telegram_id(tid, fn, un)
        return {"access_token": create_access_token(user_id), "user_id": user_id}

    # Login widget: подпись тоже должна быть обязательной в prod
    require_tg = True
    if cfg.REQUIRE_TELEGRAM_BOT_TOKEN.strip():
        require_tg = cfg.REQUIRE_TELEGRAM_BOT_TOKEN.strip().lower() in ("1", "true", "yes", "y", "on")
    elif cfg.VIBEWORK_ENV != "prod":
        require_tg = False
    if require_tg and not bot_token:
        raise HTTPException(
            status_code=503,
            detail="TELEGRAM_BOT_TOKEN не настроен на сервере (в prod подпись Telegram обязательна).",
        )

    if not check_telegram_auth(data, bot_token):
        raise HTTPException(status_code=403, detail="Неверная подпись Telegram")
    tid = data.get("id")
    if tid is None:
        raise HTTPException(400, detail="Нужно поле id")
    tid = int(tid)
    fn = str(data.get("first_name") or "")
    un = str(data.get("username") or "")
    user_id = _get_or_create_user_id_for_telegram_id(tid, fn, un)
    return {"access_token": create_access_token(user_id), "user_id": user_id}
