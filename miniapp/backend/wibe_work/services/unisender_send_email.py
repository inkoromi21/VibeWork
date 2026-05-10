"""Отправка писем через Unisender Web API метод sendEmail (HTTPS/443)."""

from __future__ import annotations

import re
from typing import Optional, Tuple

import httpx

from wibe_work.config import (
    EMAIL_FROM,
    UNISENDER_API_KEY,
    UNISENDER_LIST_ID,
    UNISENDER_WEB_BASE_URL,
)


def unisender_web_configured() -> bool:
    return bool(UNISENDER_API_KEY and UNISENDER_LIST_ID and EMAIL_FROM)


_FROM_RE = re.compile(r"^\s*(?:(.*?)\s*)?<\s*([^<>\s]+@[^<>\s]+)\s*>\s*$")


def _split_from(value: str) -> tuple[Optional[str], str]:
    v = (value or "").strip()
    if not v:
        return None, ""
    m = _FROM_RE.match(v)
    if m:
        name = (m.group(1) or "").strip() or None
        return name, (m.group(2) or "").strip()
    return None, v


async def send_unisender_web_email(
    to_email: str,
    subject: str,
    html_body: str,
    timeout: float = 20.0,
) -> Tuple[bool, Optional[str]]:
    """
    https://api.unisender.com/ru/api/sendEmail?format=json
    обязательные: api_key, email, sender_name, sender_email, subject, body, list_id
    """
    if not unisender_web_configured():
        return (
            False,
            "Unisender не настроен (UNISENDER_API_KEY, UNISENDER_LIST_ID, EMAIL_FROM)",
        )

    sender_name, sender_email = _split_from(EMAIL_FROM)
    if not sender_email:
        return False, "EMAIL_FROM пустой или некорректный"
    if not sender_name:
        sender_name = "VibeWork"

    url = UNISENDER_WEB_BASE_URL.rstrip("/") + "/ru/api/sendEmail"
    data = {
        "format": "json",
        "api_key": UNISENDER_API_KEY,
        "email": to_email,
        "sender_name": sender_name,
        "sender_email": sender_email,
        "subject": subject,
        "body": html_body,
        "list_id": str(UNISENDER_LIST_ID),
        "error_checking": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, data=data)
    except httpx.RequestError as e:
        return False, str(e)

    if r.status_code >= 400:
        return False, f"Unisender HTTP {r.status_code}: {r.text}"

    try:
        payload = r.json()
    except Exception:
        return False, f"Unisender: non-JSON response: {r.text}"

    # error_checking=1 => result: [{..., errors:[{message:...}]}]
    if isinstance(payload, dict):
        res = payload.get("result")
        if isinstance(res, list) and res:
            first = res[0] or {}
            errs = first.get("errors")
            if isinstance(errs, list) and errs:
                msg = errs[0].get("message") if isinstance(errs[0], dict) else None
                return False, msg or str(errs)
            if first.get("id") or first.get("email_id"):
                return True, None
        # older format: {"result":{"email_id":...}}
        if isinstance(res, dict) and res.get("email_id"):
            return True, None

        if payload.get("error"):
            return False, str(payload.get("error"))

    return False, f"Unisender: unexpected response: {payload}"

