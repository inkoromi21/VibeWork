"""Транзакционная почта через Resend HTTP API."""

from __future__ import annotations

from typing import Optional, Tuple

from wibe_work.services.resend_send import resend_configured, send_resend_message


def transactional_email_configured() -> bool:
    return resend_configured()


async def send_transactional_email(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: Optional[str] = None,
    timeout: float = 25.0,
) -> Tuple[bool, Optional[str]]:
    return await send_resend_message(
        to_email, subject, text_body, html_body, timeout=timeout
    )
