"""Проверка подписи Telegram Web App / Login (initData)."""

import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional, Tuple
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
    tid, _, _ = parse_init_data_user_fields(init_data)
    return tid


def parse_init_data_user_fields(init_data: str) -> Tuple[Optional[int], str, str]:
    """Telegram user id и поля профиля из init_data (без проверки подписи)."""
    if not init_data:
        return None, "", ""
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        u = parsed.get("user")
        if not u:
            return None, "", ""
        j = json.loads(u)
        tid = j.get("id")
        if tid is None:
            return None, "", ""
        return int(tid), str(j.get("first_name") or ""), str(j.get("username") or "")
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None, "", ""


def validate_webapp_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int = 86400,
) -> bool:
    """
    Проверка целостности Telegram.WebApp.initData (Mini App).
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    if not bot_token or not init_data:
        return False
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    hash_received = parsed.pop("hash", None)
    if not hash_received:
        return False
    # Поля signature / другие — не входят в классическую data-check-string с hash
    parsed.pop("signature", None)
    pairs = sorted(parsed.items())
    data_check_string = "\n".join(f"{k}={v}" for k, v in pairs)
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode(),
        hashlib.sha256,
    ).digest()
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(calculated_hash, hash_received):
        return False
    auth_date_raw = parsed.get("auth_date")
    if auth_date_raw is not None and max_age_seconds > 0:
        try:
            ts = int(auth_date_raw)
            if time.time() - ts > max_age_seconds:
                return False
        except (TypeError, ValueError):
            return False
    return True
