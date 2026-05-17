import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

from wibe_work.miniapp_paths import ADMIN_HTML, MINIAPP_HTML, PROJECT_ROOT, RESET_PASSWORD_HTML

# Сначала корневой .env репозитория (рядом с miniapp/), затем при необходимости — отдельный файл (systemd: VIBEWORK_ENV_FILE=/opt/.../.env).
load_dotenv(PROJECT_ROOT / ".env")
_extra_env = os.environ.get("VIBEWORK_ENV_FILE", "").strip()
if _extra_env:
    load_dotenv(Path(_extra_env).expanduser(), override=True)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from wibe_work.sqlite_db import init_db
from wibe_work import config as cfg
from wibe_work.routers import (
    account_link_routes,
    assessment_routes,
    career_routes,
    email_auth_routes,
    poll_routes,
    profile_routes,
    telegram_auth_routes,
)
from wibe_work.routers.admin_routes import router as admin_router
from wibe_work.routers.session_routes import router as session_router
from wibe_work.routers.website_auth_compat_routes import router as website_auth_compat_router
from wibe_work.routers.website_api_routes import router as website_api_router
from wibe_work.services.llm_client import get_llm_settings

app = FastAPI(title="VibeWork", description="Карьерный помощник")

def _parse_cors_origins(raw: str) -> list[str]:
    # Comma/space separated list
    parts: list[str] = []
    for chunk in (raw or "").replace(" ", ",").split(","):
        o = chunk.strip()
        if o:
            parts.append(o)
    return parts


_cors_origins = _parse_cors_origins(cfg.CORS_ALLOW_ORIGINS)
_cors_has_wildcard = any(o == "*" for o in _cors_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins if _cors_origins else [],
    # credentials нельзя сочетать с allow_origins=["*"] — FastAPI/Starlette всё равно отрежет;
    # оставляем True только при явных origin-ах.
    allow_credentials=False if _cors_has_wildcard else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_WEBSITE_FRONTEND_DIR = PROJECT_ROOT / "website" / "frontend"
_FAVICON_PNG = _WEBSITE_FRONTEND_DIR / "favicon.png"
if _WEBSITE_FRONTEND_DIR.is_dir():
    # Старая веб-статика (style.css, script.js) — на случай прямых ссылок; корень отдаёт тот же UI, что миниапп
    app.mount("/static", StaticFiles(directory=str(_WEBSITE_FRONTEND_DIR)), name="website_static")


app.include_router(account_link_routes.router)
app.include_router(email_auth_routes.router)
app.include_router(session_router)
app.include_router(profile_routes.router)
app.include_router(telegram_auth_routes.router)
app.include_router(poll_routes.router)
app.include_router(career_routes.router)
app.include_router(assessment_routes.router)
app.include_router(assessment_routes.miniapp_prefixed_router)
app.include_router(website_auth_compat_router)
app.include_router(website_api_router)
app.include_router(admin_router)

init_db()

def _bool_env(raw: str) -> bool | None:
    s = (raw or "").strip().lower()
    if not s:
        return None
    if s in ("1", "true", "yes", "y", "on"):
        return True
    if s in ("0", "false", "no", "n", "off"):
        return False
    return None


def _validate_security_config() -> None:
    """
    Строгие проверки только в prod, чтобы не ломать локальную разработку.
    """
    if cfg.VIBEWORK_ENV != "prod":
        return

    issues: list[str] = []

    # JWT
    if not cfg.JWT_SECRET or cfg.JWT_SECRET.strip() == "dev-change-me-in-production-vibework":
        issues.append("JWT_SECRET не задан (или остался dev-дефолт).")

    # Telegram
    require_tg = _bool_env(cfg.REQUIRE_TELEGRAM_BOT_TOKEN)
    if require_tg is None:
        require_tg = True
    if require_tg and not os.environ.get("TELEGRAM_BOT_TOKEN", "").strip():
        issues.append("TELEGRAM_BOT_TOKEN не задан, а REQUIRE_TELEGRAM_BOT_TOKEN=true (по умолчанию в prod).")

    # CORS
    if not _cors_origins:
        issues.append("CORS_ALLOW_ORIGINS пуст — браузерные клиенты не смогут ходить в API (или вы случайно отключили CORS).")
    if _cors_has_wildcard:
        issues.append("CORS_ALLOW_ORIGINS содержит '*': это опасно для прод-окружения.")

    if issues:
        msg = "Безопасность: конфиг для prod некорректен:\n- " + "\n- ".join(issues)
        raise RuntimeError(msg)


_validate_security_config()

try:
    from wibe_work.services.transactional_email import transactional_email_configured

    _env_path = PROJECT_ROOT / ".env"
    print(
        "[vibework] transactional email: "
        f"{'OK' if transactional_email_configured() else 'NOT CONFIGURED'} · "
        f"{_env_path} exists={_env_path.is_file()}"
        + (
            f" · also VIBEWORK_ENV_FILE={_extra_env!r}"
            if _extra_env
            else ""
        ),
        flush=True,
    )
except Exception as _e:
    print(f"[vibework] email startup check: {_e}", flush=True)


def _html_no_cache(content: str) -> HTMLResponse:
    return HTMLResponse(
        content,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        },
    )


def _read_miniapp_html() -> str:
    path = MINIAPP_HTML
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Miniapp HTML not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _read_reset_password_html() -> str:
    path = RESET_PASSWORD_HTML
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Reset password HTML not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _read_admin_html() -> str:
    path = ADMIN_HTML
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Admin HTML not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _resend_nonempty_from_env_file(path: Path) -> dict[str, bool] | None:
    """Как dotenv читает файл с диска (без секретов — только флаг «не пусто»)."""
    if not path.is_file():
        return None
    raw = dotenv_values(path, encoding="utf-8")
    keys = ("EMAIL_FROM", "RESEND_API_KEY")
    return {k: bool(str(raw.get(k) or "").strip()) for k in keys}


@app.get("/api/health/email")
async def health_email():
    """Диагностика сброса пароля: что видит процесс (без секретов)."""
    from wibe_work import config as cfg
    from wibe_work.services.resend_send import resend_configured
    from wibe_work.services.transactional_email import transactional_email_configured

    root_env = PROJECT_ROOT / ".env"
    in_file = _resend_nonempty_from_env_file(root_env)
    return {
        "transactional_ok": transactional_email_configured(),
        "resend_ready": resend_configured(),
        "resend_fields_set": {
            "EMAIL_FROM": bool(cfg.EMAIL_FROM),
            "RESEND_API_KEY": bool(cfg.RESEND_API_KEY),
        },
        "resend_nonempty_in_dotenv_file": in_file,
        "dotenv_project_root": str(PROJECT_ROOT),
        "dotenv_file_exists": root_env.is_file(),
        "vibework_env_file": os.environ.get("VIBEWORK_ENV_FILE", "") or None,
        "hint": (
            "Если resend_nonempty_in_dotenv_file показывает false — в .env на сервере нет RESEND_API_KEY/EMAIL_FROM или они пустые. "
            "Если в файле true, а resend_fields_set false — перезапустите API после правок .env."
        ),
    }


@app.get("/api/health/llm")
async def health_llm():
    """Проверка LLM: облачный или локальный OpenAI-совместимый эндпоинт."""
    cfg = get_llm_settings()
    out: dict = {
        "llm_configured": cfg is not None,
    }
    if cfg:
        out["model"] = cfg[2]
    return out


@app.get("/api/health/hh")
async def health_hh():
    """Диагностика hh.ru: конфиг и лёгкий запрос к API (без секретов в ответе)."""
    from wibe_work import config as hh_cfg
    from wibe_work.services import hh_client

    if hh_cfg.HH_APP_ACCESS_TOKEN:
        auth_mode = "app_token"
        oauth_ok = True
    elif hh_cfg.HH_CLIENT_ID and hh_cfg.HH_CLIENT_SECRET:
        auth_mode = "client_credentials"
        oauth_ok = True
    elif hh_cfg.HH_CLIENT_ID or hh_cfg.HH_CLIENT_SECRET:
        auth_mode = "incomplete"
        oauth_ok = False
    else:
        auth_mode = "none"
        oauth_ok = False

    out: dict = {
        "hh_user_agent_set": bool(str(hh_cfg.HH_USER_AGENT or "").strip()),
        "hh_oauth_configured": oauth_ok,
        "hh_auth_mode": auth_mode,
        "hint": (
            "После одобрения на dev.hh.ru задайте HH_CLIENT_ID и HH_CLIENT_SECRET в корневом .env "
            "и перезапустите API. User-Agent должен совпадать с заявкой. "
            "CLI: python scripts/test_hh_api.py"
        ),
    }

    try:
        areas = hh_client.suggest_areas("Моск", limit=1)
        out["api_ok"] = bool(areas)
        if areas:
            out["sample_area"] = areas[0]
    except Exception as e:
        out["api_ok"] = False
        out["api_error"] = str(e)[:300]

    if oauth_ok and not hh_cfg.HH_APP_ACCESS_TOKEN:
        try:
            hh_client._fetch_client_credentials_token()
            out["token_ok"] = True
        except Exception as e:
            out["token_ok"] = False
            out["token_error"] = str(e)[:300]

    return out


@app.get("/favicon.ico", include_in_schema=False)
async def favicon_ico():
    """Табы и боты часто запрашивают /favicon.ico по умолчанию — отдаём тот же PNG."""
    if not _FAVICON_PNG.is_file():
        raise HTTPException(status_code=404, detail="favicon not found")
    return FileResponse(_FAVICON_PNG, media_type="image/png")


@app.get("/miniapp/", response_class=HTMLResponse)
async def miniapp():
    return _html_no_cache(_read_miniapp_html())


@app.get("/", response_class=HTMLResponse)
async def website_index():
    """Главная сайта — тот же UI, что мини-приложение в Telegram (miniapp/frontend/index.html)."""
    return _html_no_cache(_read_miniapp_html())


@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page():
    """Сброс пароля по ссылке из письма (Resend)."""
    return _html_no_cache(_read_reset_password_html())


@app.get("/admin", response_class=HTMLResponse)
@app.get("/admin/", response_class=HTMLResponse)
async def admin_page():
    """Панель администратора (отдельный вход из .env)."""
    return _html_no_cache(_read_admin_html())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
