from dotenv import load_dotenv

from wibe_work.miniapp_paths import MINIAPP_HTML, PROJECT_ROOT

load_dotenv(PROJECT_ROOT / ".env")

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


def _read_miniapp_html() -> str:
    path = MINIAPP_HTML
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Miniapp HTML not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
