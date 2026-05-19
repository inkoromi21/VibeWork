"""Админ-панель: вход по ADMIN_LOGIN / ADMIN_PASSWORD и просмотр данных пользователей."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from wibe_work.admin_auth import (
    ADMIN_COOKIE,
    admin_credentials_configured,
    clear_admin_cookie,
    create_admin_session_token,
    is_valid_admin_token,
    require_admin,
    set_admin_cookie,
    verify_admin_credentials,
)
from wibe_work.password_input import sanitize_password_input
from wibe_work.services.admin_queries import get_user_detail, list_users
from wibe_work.services.user_accounts import delete_user_account

router = APIRouter(prefix="/admin/api", tags=["admin"])


class AdminLoginBody(BaseModel):
    login: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


@router.get("/status")
async def admin_status():
    return {"configured": admin_credentials_configured()}


@router.post("/login")
async def admin_login(body: AdminLoginBody, response: Response):
    if not admin_credentials_configured():
        raise HTTPException(
            status_code=503,
            detail="Админка не настроена: задайте ADMIN_LOGIN и ADMIN_PASSWORD в .env",
        )
    password = sanitize_password_input(body.password)
    if not verify_admin_credentials(body.login.strip(), password):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    token = create_admin_session_token()
    set_admin_cookie(response, token)
    return {"ok": True}


@router.post("/logout")
async def admin_logout(response: Response, _: None = Depends(require_admin)):
    clear_admin_cookie(response)
    return {"ok": True}


@router.get("/me")
async def admin_me(
    vw_admin_session: str | None = Cookie(default=None, alias=ADMIN_COOKIE),
):
    return {
        "authenticated": is_valid_admin_token(vw_admin_session),
        "configured": admin_credentials_configured(),
    }


@router.get("/users")
async def admin_users(_: None = Depends(require_admin)) -> dict[str, Any]:
    return {"users": list_users()}


@router.get("/users/{user_id}")
async def admin_user_detail(user_id: str, _: None = Depends(require_admin)) -> dict[str, Any]:
    detail = get_user_detail(user_id.strip())
    if not detail:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return detail


@router.delete("/users/{user_id}")
async def admin_delete_user(user_id: str, _: None = Depends(require_admin)) -> dict[str, bool]:
    uid = user_id.strip()
    if not uid:
        raise HTTPException(status_code=400, detail="Не указан пользователь")
    if not delete_user_account(uid):
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return {"ok": True}
