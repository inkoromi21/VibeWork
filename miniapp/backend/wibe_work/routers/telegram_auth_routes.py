import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from wibe_work.telegram_init_data import check_telegram_auth, parse_init_data_user_id
from wibe_work.sqlite_db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


def _upsert_tg_user(telegram_id: int, first_name: str, username: str, user_key: str) -> None:
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
    Старая авторизация для мини-аппа: тело с полями Telegram Login или { "init_data": "..." }.
    Возвращает фиктивный токен (как раньше).
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    init_data = data.get("init_data")
    if init_data:
        tid = parse_init_data_user_id(init_data)
        if tid is None:
            raise HTTPException(400, detail="Не удалось разобрать init_data")
        user_key = f"tg_{tid}"
        _upsert_tg_user(tid, "", "", user_key)
        return {"access_token": "fake_token", "user_id": user_key}

    if not check_telegram_auth(data, bot_token):
        raise HTTPException(status_code=403, detail="Неверная подпись Telegram")
    tid = data.get("id")
    if tid is None:
        raise HTTPException(400, detail="Нужно поле id")
    tid = int(tid)
    fn = str(data.get("first_name") or "")
    un = str(data.get("username") or "")
    user_key = f"tg_{tid}"
    _upsert_tg_user(tid, fn, un, user_key)
    return {"access_token": "fake_token", "user_id": user_key}
