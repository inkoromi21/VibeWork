"""Отправка писем через SMTP (Яндекс, Mail.ru, хостинг и т.д.) — без платных API."""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional, Tuple

from wibe_work.config import (
    EMAIL_FROM,
    EMAIL_SMTP_HOST,
    EMAIL_SMTP_PASSWORD,
    EMAIL_SMTP_PORT,
    EMAIL_SMTP_USE_SSL,
    EMAIL_SMTP_USER,
)


def smtp_configured() -> bool:
    return bool(
        EMAIL_SMTP_HOST and EMAIL_SMTP_USER and EMAIL_SMTP_PASSWORD and EMAIL_FROM
    )


def smtp_missing_keys() -> list[str]:
    """Имена переменных SMTP без значения (для сообщений об ошибке, без секретов)."""
    out: list[str] = []
    if not EMAIL_FROM:
        out.append("EMAIL_FROM")
    if not EMAIL_SMTP_HOST:
        out.append("EMAIL_SMTP_HOST")
    if not EMAIL_SMTP_USER:
        out.append("EMAIL_SMTP_USER")
    if not EMAIL_SMTP_PASSWORD:
        out.append("EMAIL_SMTP_PASSWORD")
    return out


def send_smtp_message_sync(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: Optional[str] = None,
    timeout: float = 25.0,
) -> Tuple[bool, Optional[str]]:
    if not smtp_configured():
        return False, "SMTP не настроен (EMAIL_SMTP_HOST, USER, PASSWORD, EMAIL_FROM)"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email
    msg.set_content(text_body, charset="utf-8")
    if html_body:
        msg.add_alternative(html_body, subtype="html", charset="utf-8")

    use_ssl = EMAIL_SMTP_USE_SSL or EMAIL_SMTP_PORT == 465
    ctx = ssl.create_default_context()
    try:
        if use_ssl:
            with smtplib.SMTP_SSL(
                EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, timeout=timeout, context=ctx
            ) as smtp:
                smtp.login(EMAIL_SMTP_USER, EMAIL_SMTP_PASSWORD)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(
                EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, timeout=timeout
            ) as smtp:
                smtp.starttls(context=ctx)
                smtp.login(EMAIL_SMTP_USER, EMAIL_SMTP_PASSWORD)
                smtp.send_message(msg)
    except OSError as e:
        return False, str(e)
    except smtplib.SMTPException as e:
        return False, str(e)

    return True, None
