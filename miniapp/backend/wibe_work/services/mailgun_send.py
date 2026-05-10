"""Отправка транзакционной почты через Mailgun HTTP API."""

from __future__ import annotations

from typing import Optional, Tuple

import httpx

from wibe_work.config import (
    EMAIL_FROM,
    MAILGUN_API_KEY,
    MAILGUN_DOMAIN,
    MAILGUN_REGION,
)


def mailgun_configured() -> bool:
    return bool(MAILGUN_API_KEY and MAILGUN_DOMAIN and EMAIL_FROM)


def _mailgun_base_url() -> str:
    if MAILGUN_REGION == "eu":
        return "https://api.eu.mailgun.net"
    return "https://api.mailgun.net"


async def send_mailgun_message(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: Optional[str] = None,
    timeout: float = 20.0,
) -> Tuple[bool, Optional[str]]:
    """
    Отправка одного письма. Возвращает (успех, текст_ошибки).
    """
    if not mailgun_configured():
        return False, "Mailgun не настроен (MAILGUN_API_KEY, MAILGUN_DOMAIN, EMAIL_FROM)"

    url = f"{_mailgun_base_url()}/v3/{MAILGUN_DOMAIN}/messages"
    data = {
        "from": EMAIL_FROM,
        "to": to_email,
        "subject": subject,
        "text": text_body,
    }
    if html_body:
        data["html"] = html_body

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, auth=("api", MAILGUN_API_KEY), data=data)
    except httpx.RequestError as e:
        return False, str(e)

    if r.status_code >= 400:
        try:
            detail = r.json()
        except Exception:
            detail = r.text
        return False, f"Mailgun HTTP {r.status_code}: {detail}"

    return True, None
