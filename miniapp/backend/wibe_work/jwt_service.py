"""Выпуск и разбор JWT для входа по email (миниаппа)."""

from datetime import datetime, timezone
from typing import Optional

import jwt

from wibe_work.config import JWT_EXPIRE_DELTA, JWT_SECRET


def create_access_token(user_id: str) -> str:
    exp = datetime.now(timezone.utc) + JWT_EXPIRE_DELTA
    return jwt.encode(
        {"sub": user_id, "exp": exp},
        JWT_SECRET,
        algorithm="HS256",
    )


def decode_token_subject(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        sub = payload.get("sub")
        return str(sub) if sub is not None else None
    except jwt.PyJWTError:
        return None
