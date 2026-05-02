"""Проверка подписи Telegram Web App / Login (initData)."""

import hashlib
import hmac
import json
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl


def check_telegram_auth(auth_data: Dict[str, Any], bot_token: str) -> bool:
    """
    Проверка данных виджета Login / старых запросов (упрощённо).
    Если bot_token пустой — пропускаем (локальная разработка).
    """
    if not bot_token:
        return True
    recv_hash = auth_data.get("hash")
    if not recv_hash:
        return False
    check: Dict[str, Any] = {k: v for k, v in auth_data.items() if k != "hash"}
    data_check_string = "\n".join(f"{k}={check[k]}" for k in sorted(check.keys()))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    h = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return h == recv_hash


def parse_init_data_user_id(init_data: str) -> Optional[int]:
    """Telegram user id из строки init_data; подпись здесь не проверяем."""
    if not init_data:
        return None
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        u = parsed.get("user")
        if not u:
            return None
        j = json.loads(u)
        tid = j.get("id")
        return int(tid) if tid is not None else None
    except (ValueError, TypeError, KeyError):
        return None
