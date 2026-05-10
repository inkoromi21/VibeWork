"""Транзакционная почта: SMTP (бесплатно с ящиком) или Mailgun."""

from __future__ import annotations

import asyncio
from typing import Optional, Tuple

from wibe_work.services.mailgun_send import mailgun_configured, send_mailgun_message
from wibe_work.services.smtp_send import send_smtp_message_sync, smtp_configured


def transactional_email_configured() -> bool:
    return smtp_configured() or mailgun_configured()


async def send_transactional_email(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: Optional[str] = None,
    timeout: float = 25.0,
) -> Tuple[bool, Optional[str]]:
    """
    Сначала SMTP (если задан в .env), иначе Mailgun.
    """
    if smtp_configured():
        return await asyncio.to_thread(
            send_smtp_message_sync,
            to_email,
            subject,
            text_body,
            html_body,
            timeout,
        )
    if mailgun_configured():
        return await send_mailgun_message(
            to_email, subject, text_body, html_body, timeout=timeout
        )
    return (
        False,
        "Почта не настроена: задайте EMAIL_SMTP_* + EMAIL_FROM или Mailgun.",
    )
