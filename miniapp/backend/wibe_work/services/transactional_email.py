"""Транзакционная почта: SMTP (бесплатно с ящиком) или Mailgun."""

from __future__ import annotations

import asyncio
from typing import Optional, Tuple

from wibe_work.services.mailgun_send import mailgun_configured, send_mailgun_message
from wibe_work.services.resend_send import resend_configured, send_resend_message
from wibe_work.services.smtp_send import send_smtp_message_sync, smtp_configured
from wibe_work.services.unisender_send_email import (
    send_unisender_web_email,
    unisender_web_configured,
)
from wibe_work.services.unisender_go_send import (
    send_unisender_go_message,
    unisender_go_configured,
)


def transactional_email_configured() -> bool:
    return (
        smtp_configured()
        or resend_configured()
        or unisender_web_configured()
        or unisender_go_configured()
        or mailgun_configured()
    )


async def send_transactional_email(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: Optional[str] = None,
    timeout: float = 25.0,
) -> Tuple[bool, Optional[str]]:
    """
    Сначала SMTP (если задан в .env). Если SMTP недоступен — Resend, затем Unisender (Web API / Go), затем Mailgun.
    """
    if smtp_configured():
        ok, err = await asyncio.to_thread(
            send_smtp_message_sync, to_email, subject, text_body, html_body, timeout
        )
        if ok:
            return True, None
        # SMTP часто блокируют на VPS; если настроен Unisender — попробуем его.
        if resend_configured():
            ok2, err2 = await send_resend_message(
                to_email, subject, text_body, html_body, timeout=timeout
            )
            if ok2:
                return True, None
            return False, f"SMTP: {err}; Resend: {err2}"
        if unisender_web_configured():
            ok2, err2 = await send_unisender_web_email(
                to_email,
                subject,
                html_body or ("<pre>" + text_body + "</pre>"),
                timeout=timeout,
            )
            if ok2:
                return True, None
            return False, f"SMTP: {err}; Unisender: {err2}"
        if unisender_go_configured():
            ok2, err2 = await send_unisender_go_message(
                to_email, subject, text_body, html_body, timeout=timeout
            )
            if ok2:
                return True, None
            return False, f"SMTP: {err}; Unisender Go: {err2}"
        return False, err

    if resend_configured():
        return await send_resend_message(
            to_email, subject, text_body, html_body, timeout=timeout
        )

    if unisender_web_configured():
        return await send_unisender_web_email(
            to_email,
            subject,
            html_body or ("<pre>" + text_body + "</pre>"),
            timeout=timeout,
        )

    if unisender_go_configured():
        return await send_unisender_go_message(
            to_email, subject, text_body, html_body, timeout=timeout
        )

    if mailgun_configured():
        return await send_mailgun_message(
            to_email, subject, text_body, html_body, timeout=timeout
        )
    return (
        False,
        "Почта не настроена: задайте SMTP (EMAIL_SMTP_* + EMAIL_FROM) или Resend (RESEND_API_KEY) или Unisender (UNISENDER_API_KEY + UNISENDER_LIST_ID) или Mailgun.",
    )
