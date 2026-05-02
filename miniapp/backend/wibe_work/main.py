from dotenv import load_dotenv

from wibe_work.miniapp_paths import MINIAPP_HTML, PROJECT_ROOT

load_dotenv(PROJECT_ROOT / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from wibe_work.sqlite_db import init_db
from wibe_work.routers import (
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

app = FastAPI(title="Wibe work", description="Карьерный помощник")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_WEBSITE_FRONTEND_DIR = PROJECT_ROOT / "website" / "frontend"
if _WEBSITE_FRONTEND_DIR.is_dir():
    # website/frontend/index.html ожидает /static/style.css и /static/script.js
    app.mount("/static", StaticFiles(directory=str(_WEBSITE_FRONTEND_DIR)), name="website_static")


@app.middleware("http")
async def add_ngrok_header(request, call_next):
    response = await call_next(request)
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response


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
    path = MINIAPP_HTML
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Miniapp HTML not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/", response_class=HTMLResponse)
async def website_index():
    """Главная страница сайта CareerCompass (website/frontend/index.html)."""
    path = PROJECT_ROOT / "website" / "frontend" / "index.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Website index not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
