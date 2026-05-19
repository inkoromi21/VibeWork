"""Выпуск и разбор JWT для входа по email (миниаппа)."""

from datetime import datetime, timezone
from typing import Optional

import jwt

from wibe_work.config import JWT_EXPIRE_DELTA, JWT_INVALID_BEFORE, JWT_SECRET


def _parse_invalid_before() -> Optional[datetime]:
    raw = JWT_INVALID_BEFORE
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError):
        return None


def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    exp = now + JWT_EXPIRE_DELTA
    return jwt.encode(
        {"sub": user_id, "exp": exp, "iat": int(now.timestamp())},
        JWT_SECRET,
        algorithm="HS256",
    )


def decode_token_subject(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        inv = _parse_invalid_before()
        if inv is not None:
            iat = payload.get("iat")
            if iat is None:
                return None
            try:
                issued = datetime.fromtimestamp(float(iat), tz=timezone.utc)
            except (TypeError, ValueError, OSError):
                return None
            if issued < inv:
                return None
        sub = payload.get("sub")
        return str(sub) if sub is not None else None
    except jwt.PyJWTError:
        return None
