"""Имя бота для Login Widget: TELEGRAM_BOT_USERNAME или getMe по TELEGRAM_BOT_TOKEN."""

from __future__ import annotations

import os
import threading
from typing import Optional

import requests

_lock = threading.Lock()
_cached: Optional[str] = None
_resolved = False


def get_telegram_bot_username() -> Optional[str]:
    """
    Имя без @ для data-telegram-login.
    Приоритет: TELEGRAM_BOT_USERNAME → кэш getMe → None.
    """
    explicit = (os.environ.get("TELEGRAM_BOT_USERNAME") or "").strip().lstrip("@")
    if explicit:
        return explicit

    global _cached, _resolved
    with _lock:
        if _resolved:
            return _cached
        _resolved = True
        token = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
        if not token:
            _cached = None
            return None
        try:
            r = requests.get(
                f"https://api.telegram.org/bot{token}/getMe",
                timeout=12,
            )
            r.raise_for_status()
            data = r.json()
            un = str((data.get("result") or {}).get("username") or "").strip()
            _cached = un or None
        except (requests.RequestException, ValueError, TypeError, KeyError):
            _cached = None
        return _cached
