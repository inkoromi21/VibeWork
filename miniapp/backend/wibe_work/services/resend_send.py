"""Отправка транзакционной почты через Resend HTTP API (443)."""

from __future__ import annotations

from typing import Optional, Tuple

import httpx

from wibe_work.config import EMAIL_FROM, RESEND_API_KEY, RESEND_BASE_URL


def resend_configured() -> bool:
    return bool(RESEND_API_KEY and EMAIL_FROM)


def resend_missing_keys() -> list[str]:
    """Имена переменных без значения (для сообщений об ошибке, без секретов)."""
    out: list[str] = []
    if not RESEND_API_KEY:
        out.append("RESEND_API_KEY")
    if not EMAIL_FROM:
        out.append("EMAIL_FROM")
    return out


async def send_resend_message(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: Optional[str] = None,
    timeout: float = 20.0,
) -> Tuple[bool, Optional[str]]:
    """
    POST {RESEND_BASE_URL}/emails
    Auth: Authorization: Bearer <RESEND_API_KEY>
    """
    if not resend_configured():
        return False, "Resend не настроен (RESEND_API_KEY, EMAIL_FROM)"

    url = RESEND_BASE_URL.rstrip("/") + "/emails"
    payload: dict = {
        "from": EMAIL_FROM,
        "to": [to_email],
        "subject": subject,
    }
    if html_body:
        payload["html"] = html_body
    payload["text"] = text_body

    headers = {"Authorization": f"Bearer {RESEND_API_KEY}"}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, headers=headers, json=payload)
    except httpx.RequestError as e:
        return False, str(e)

    try:
        data = r.json()
    except Exception:
        data = None

    if r.status_code >= 400:
        return False, f"Resend HTTP {r.status_code}: {data or r.text}"

    # Успех обычно возвращает {"id": "..."}
    if isinstance(data, dict) and data.get("id"):
        return True, None

    return True, None

