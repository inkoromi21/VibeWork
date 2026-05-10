"""Отправка транзакционной почты через Unisender Go HTTP API (443)."""

from __future__ import annotations

import re
from typing import Optional, Tuple

import httpx

from wibe_work.config import EMAIL_FROM, UNISENDER_API_KEY, UNISENDER_GO_BASE_URL


def unisender_go_configured() -> bool:
    return bool(UNISENDER_API_KEY and EMAIL_FROM)


_FROM_RE = re.compile(r"^\s*(?:(.*?)\s*)?<\s*([^<>\s]+@[^<>\s]+)\s*>\s*$")


def _split_from(value: str) -> tuple[Optional[str], str]:
    """
    EMAIL_FROM допускает:
    - "Name <email@domain>"
    - "email@domain"
    """
    v = (value or "").strip()
    if not v:
        return None, ""
    m = _FROM_RE.match(v)
    if m:
        name = (m.group(1) or "").strip() or None
        return name, (m.group(2) or "").strip()
    # fallback: assume raw email
    return None, v


async def send_unisender_go_message(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: Optional[str] = None,
    timeout: float = 20.0,
) -> Tuple[bool, Optional[str]]:
    """
    Отправка одного письма. Возвращает (успех, текст_ошибки).

    Документация: Unisender Go Transactional API v1, endpoint:
    POST /ru/transactional/api/v1/email/send.json
    """
    if not unisender_go_configured():
        return False, "Unisender Go не настроен (UNISENDER_API_KEY, EMAIL_FROM)"

    from_name, from_email = _split_from(EMAIL_FROM)
    if not from_email:
        return False, "EMAIL_FROM пустой или некорректный"

    url = UNISENDER_GO_BASE_URL.rstrip("/") + "/ru/transactional/api/v1/email/send.json"
    payload: dict = {
        "subject": subject,
        "from_email": from_email,
        "recipients": [{"email": to_email}],
        "body": {"plaintext": text_body},
    }
    if from_name:
        payload["from_name"] = from_name
    if html_body:
        payload["body"]["html"] = html_body

    headers = {"X-API-KEY": UNISENDER_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, headers=headers, json=payload)
    except httpx.RequestError as e:
        return False, str(e)

    # Обычно ошибки приходят как HTTP 4xx/5xx, но подстрахуемся на "error" в JSON при 200.
    try:
        data = r.json()
    except Exception:
        data = None

    if r.status_code >= 400:
        return False, f"Unisender Go HTTP {r.status_code}: {data or r.text}"

    if isinstance(data, dict) and (data.get("error") or data.get("errors")):
        return False, f"Unisender Go error: {data.get('error') or data.get('errors')}"

    return True, None

