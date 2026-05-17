"""FastAPI-зависимость: Bearer JWT должен совпадать с user_id в пути."""

from fastapi import HTTPException, Request

from wibe_work.jwt_service import decode_token_subject
from wibe_work.services.user_accounts import account_exists


def _reject_missing_account(user_id: str) -> None:
    if not account_exists(user_id):
        raise HTTPException(
            status_code=401,
            detail="Аккаунт не найден. Войдите или зарегистрируйтесь снова.",
        )


def require_bearer_matches_user(request: Request, user_id: str) -> None:
    auth = request.headers.get("Authorization") or request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail="Нужен вход: войдите по почте и паролю.",
        )
    token = auth[7:].strip()
    sub = decode_token_subject(token)
    if not sub:
        raise HTTPException(
            status_code=401,
            detail="Сессия истекла или недействительна. Войдите снова.",
        )
    if sub != user_id:
        raise HTTPException(status_code=403, detail="Нет доступа к этим данным.")
    _reject_missing_account(sub)


def optional_user_id_from_bearer(request: Request) -> str | None:
    """user_id из JWT, если заголовок есть; иначе None (без 401)."""
    auth = request.headers.get("Authorization") or request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        return None
    token = auth[7:].strip()
    sub = decode_token_subject(token)
    if not sub:
        return None
    uid = str(sub)
    if not account_exists(uid):
        return None
    return uid


def get_current_user_id_from_bearer(request: Request) -> str:
    """Текущий user_id из JWT (без сопоставления с path)."""
    auth = request.headers.get("Authorization") or request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail="Нужен вход: передайте Authorization: Bearer <токен>.",
        )
    token = auth[7:].strip()
    sub = decode_token_subject(token)
    if not sub:
        raise HTTPException(
            status_code=401,
            detail="Сессия истекла или недействительна. Войдите снова.",
        )
    uid = str(sub)
    _reject_missing_account(uid)
    return uid
