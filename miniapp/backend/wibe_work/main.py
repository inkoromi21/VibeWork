import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

from wibe_work.miniapp_paths import MINIAPP_HTML, PROJECT_ROOT, RESET_PASSWORD_HTML

# Сначала корневой .env репозитория (рядом с miniapp/), затем при необходимости — отдельный файл (systemd: VIBEWORK_ENV_FILE=/opt/.../.env).
load_dotenv(PROJECT_ROOT / ".env")
_extra_env = os.environ.get("VIBEWORK_ENV_FILE", "").strip()
if _extra_env:
    load_dotenv(Path(_extra_env).expanduser(), override=True)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from wibe_work.sqlite_db import init_db
from wibe_work.routers import (
    account_link_routes,
    assessment_routes,
    career_routes,
    email_auth_routes,
    poll_routes,
    profile_routes,
    telegram_auth_routes,
)
from wibe_work.routers.website_auth_compat_routes import router as website_auth_compat_router
from wibe_work.routers.website_api_routes import router as website_api_router
from wibe_work.services.llm_client import get_llm_settings, ollama_mode_enabled

app = FastAPI(title="VibeWork", description="Карьерный помощник")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_WEBSITE_FRONTEND_DIR = PROJECT_ROOT / "website" / "frontend"
if _WEBSITE_FRONTEND_DIR.is_dir():
    # Старая веб-статика (style.css, script.js) — на случай прямых ссылок; корень отдаёт тот же UI, что миниапп
    app.mount("/static", StaticFiles(directory=str(_WEBSITE_FRONTEND_DIR)), name="website_static")


app.include_router(account_link_routes.router)
app.include_router(email_auth_routes.router)
app.include_router(profile_routes.router)
app.include_router(telegram_auth_routes.router)
app.include_router(poll_routes.router)
app.include_router(career_routes.router)
app.include_router(assessment_routes.router)
app.include_router(assessment_routes.miniapp_prefixed_router)
app.include_router(website_auth_compat_router)
app.include_router(website_api_router)

init_db()

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


def _smtp_nonempty_from_env_file(path: Path) -> dict[str, bool] | None:
    """Как dotenv читает файл с диска (без секретов — только флаг «не пусто»)."""
    if not path.is_file():
        return None
    raw = dotenv_values(path, encoding="utf-8")
    keys = (
        "EMAIL_FROM",
        "EMAIL_SMTP_HOST",
        "EMAIL_SMTP_USER",
        "EMAIL_SMTP_PASSWORD",
        "RESEND_API_KEY",
        "UNISENDER_API_KEY",
        "UNISENDER_LIST_ID",
    )
    return {k: bool(str(raw.get(k) or "").strip()) for k in keys}


@app.get("/api/health/email")
async def health_email():
    """Диагностика сброса пароля: что видит процесс (без секретов)."""
    from wibe_work import config as cfg
    from wibe_work.services.mailgun_send import mailgun_configured
    from wibe_work.services.resend_send import resend_configured
    from wibe_work.services.smtp_send import smtp_configured
    from wibe_work.services.transactional_email import transactional_email_configured
    from wibe_work.services.unisender_go_send import unisender_go_configured
    from wibe_work.services.unisender_send_email import unisender_web_configured

    root_env = PROJECT_ROOT / ".env"
    in_file = _smtp_nonempty_from_env_file(root_env)
    return {
        "transactional_ok": transactional_email_configured(),
        "smtp_ready": smtp_configured(),
        "resend_ready": resend_configured(),
        "unisender_ready": unisender_web_configured() or unisender_go_configured(),
        "unisender_web_ready": unisender_web_configured(),
        "unisender_go_ready": unisender_go_configured(),
        "mailgun_ready": mailgun_configured(),
        "smtp_fields_set": {
            "EMAIL_FROM": bool(cfg.EMAIL_FROM),
            "EMAIL_SMTP_HOST": bool(cfg.EMAIL_SMTP_HOST),
            "EMAIL_SMTP_USER": bool(cfg.EMAIL_SMTP_USER),
            "EMAIL_SMTP_PASSWORD": bool(cfg.EMAIL_SMTP_PASSWORD),
            "RESEND_API_KEY": bool(cfg.RESEND_API_KEY),
            "UNISENDER_API_KEY": bool(cfg.UNISENDER_API_KEY),
            "UNISENDER_LIST_ID": bool(cfg.UNISENDER_LIST_ID),
        },
        "smtp_nonempty_in_dotenv_file": in_file,
        "dotenv_project_root": str(PROJECT_ROOT),
        "dotenv_file_exists": root_env.is_file(),
        "vibework_env_file": os.environ.get("VIBEWORK_ENV_FILE", "") or None,
        "hint": (
            "Если smtp_nonempty_in_dotenv_file показывает HOST/USER=false — в .env на сервере нет этих строк или они пустые (добавьте EMAIL_SMTP_HOST=smtp.gmail.com и EMAIL_SMTP_USER=...). "
            "Если в файле true, а smtp_fields_set false — перезапустите API после правок .env."
        ),
    }


@app.get("/api/health/llm")
async def health_llm():
    """Проверка LLM: облако или локальная Ollama (USE_OLLAMA=1)."""
    cfg = get_llm_settings()
    out: dict = {
        "llm_configured": cfg is not None,
        "ollama_mode": ollama_mode_enabled(),
    }
    if cfg:
        out["model"] = cfg[2]
    return out


@app.get("/miniapp/", response_class=HTMLResponse)
async def miniapp():
    return _read_miniapp_html()


@app.get("/", response_class=HTMLResponse)
async def website_index():
    """Главная сайта — тот же UI, что мини-приложение в Telegram (miniapp/frontend/index.html)."""
    return _read_miniapp_html()


@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page():
    """Сброс пароля по ссылке из письма (Mailgun)."""
    return _read_reset_password_html()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
