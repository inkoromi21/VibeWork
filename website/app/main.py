"""VibeWork: веб-часть (FastAPI), карьерный навигатор 16–22."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.hh_client import suggest_areas
from app.career_advisor import (
    build_analysis,
    career_chat,
    load_vacancies_for_match,
    llm_configured,
    match_jobs,
    mts_preview_rank,
    quiz_questions_bundle,
    simulator_advance,
    simulator_start,
)
from app.workday_simulator_bridge import simulator_options_list
from app.mts_tracks_catalog import MtsTrack, load_mts_tracks
from app.questionnaire_fields import get_profile_schema
from app.sqlite_async_session import engine, init_db
from app.api_schemas import (
    AnalysisResult,
    ChatRequest,
    ChatResponse,
    DiagnosisPayload,
    Interest,
    JobMatchRequest,
    MockVacancy,
    MtsMatrixMatch,
    MtsPreviewPayload,
    SimulatorAdvance,
    VacancyEnriched,
)

# Явный путь: иначе .env не находится при другом cwd или uvicorn --reload
ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT.parent
MINIAPP_BACKEND = REPO_ROOT / "miniapp" / "backend"
load_dotenv(REPO_ROOT / ".env")
load_dotenv(ROOT / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FRONTEND_DIR = ROOT / "frontend"

_PORT = int(os.environ.get("PORT", "8765"))
_CORS_ORIGINS = [
    f"http://127.0.0.1:{_PORT}",
    f"http://localhost:{_PORT}",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await engine.dispose()


app = FastAPI(title="VibeWork", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _mount_unified_auth() -> None:
    """Те же /auth/email/* и /api/auth/*, что при python miniapp/run.py."""
    if not MINIAPP_BACKEND.is_dir():
        logger.warning(
            "miniapp/backend не найден — регистрация только через python miniapp/run.py "
            "или VIBEWORK_FULL_STACK=1"
        )
        from app.account_auth_routes import router as legacy_auth_router

        app.include_router(legacy_auth_router)
        return
    import sys

    backend_s = str(MINIAPP_BACKEND)
    if backend_s not in sys.path:
        sys.path.insert(0, backend_s)
    from wibe_work.routers.email_auth_routes import router as email_auth_router
    from wibe_work.routers.website_auth_compat_routes import router as web_auth_router

    app.include_router(email_auth_router)
    app.include_router(web_auth_router)


_mount_unified_auth()

if FRONTEND_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
async def serve_index():
    index = FRONTEND_DIR / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=404, detail="frontend/index.html не найден")
    return FileResponse(index)


@app.get("/register")
async def serve_register():
    page = FRONTEND_DIR / "register.html"
    if not page.is_file():
        raise HTTPException(status_code=404, detail="frontend/register.html не найден")
    return FileResponse(page)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/profile/schema")
async def profile_schema():
    """Поля профиля по структуре Google Sheet (можно править app/questionnaire_fields.py)."""
    return get_profile_schema()


@app.get("/api/health/llm")
async def health_llm():
    """Показывает, задан ли ключ/URL для реального LLM (иначе чат и нарратив — заглушки)."""
    return {"llm_configured": llm_configured()}


@app.get("/api/mts/tracks", response_model=list[MtsTrack])
async def mts_tracks() -> list[MtsTrack]:
    return list(load_mts_tracks())


@app.get("/api/quiz/questions")
async def quiz_questions(
    interest: str = Query(..., description="Значение из профиля: IT, дизайн, маркетинг, …"),
    target_mts_role_id: str | None = Query(None, description="id роли из /api/mts/tracks"),
    education_detail: str | None = Query(None, description="id уровня образования из анкеты"),
    course_grade: str | None = Query(None, description="Класс или курс"),
    age: int | None = Query(None, ge=10, le=80),
):
    """Вопросы теста под интерес, образование и класс/курс."""
    profile: dict = {}
    if education_detail:
        profile["education_detail"] = education_detail
    if course_grade is not None:
        profile["course_grade"] = course_grade
    if age is not None:
        profile["age"] = age
    use_profile = bool(education_detail or course_grade is not None or age is not None)
    return quiz_questions_bundle(
        interest, target_mts_role_id, profile=profile if use_profile else None
    )


@app.post("/api/mts/preview", response_model=list[MtsMatrixMatch])
async def mts_preview(body: MtsPreviewPayload) -> list[MtsMatrixMatch]:
    try:
        return mts_preview_rank(body)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.post("/api/chat", response_model=ChatResponse)
async def chat(body: ChatRequest) -> ChatResponse:
    try:
        text, source, notice = await career_chat(body)
        return ChatResponse(reply=text, source=source, notice=notice)
    except Exception as e:
        logger.exception("Чат ИИ")
        raise HTTPException(status_code=500, detail="Не удалось получить ответ") from e


@app.post("/api/analyze", response_model=AnalysisResult)
async def analyze(payload: DiagnosisPayload) -> AnalysisResult:
    try:
        return await build_analysis(payload)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        logger.exception("Ошибка анализа")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера") from e


@app.get("/api/jobs", response_model=list[MockVacancy])
async def jobs(
    profession: str | None = Query(None),
    level: str | None = Query(None),
    city: str | None = Query(None),
    work_format: str | None = Query(None, description="удалённо | офис | гибрид"),
    salary_bracket: str | None = Query(None, description="low | medium | high"),
    interest: str = Query("IT", description="Код из профиля: IT, дизайн, маркетинг, …"),
) -> list[MockVacancy]:
    try:
        try:
            intr = Interest(interest)
        except ValueError:
            intr = Interest.IT
        body = JobMatchRequest(
            skills=[],
            interests=[intr],
            profession=profession,
            level=level,
            city=city,
            work_format=work_format,
            salary_bracket=salary_bracket,
        )
        return await load_vacancies_for_match(body)
    except Exception as e:
        logger.exception("Ошибка выдачи вакансий")
        raise HTTPException(status_code=500, detail="Не удалось загрузить вакансии") from e


@app.get("/api/hh/area-suggest")
async def hh_area_suggest(q: str = Query("", max_length=120)):
    """Подсказки городов и регионов РФ (префиксный поиск hh.ru)."""
    return {"items": await suggest_areas(q.strip(), limit=15)}


@app.get("/api/hh/search-url")
async def hh_search_url(
    profession: str | None = Query(None, description="id сферы анкеты (marketing, it_dev, …)"),
    interest: str | None = Query(None, description="Код Interest из API"),
    level: str | None = Query(None),
    city: str | None = Query(None),
    work_format: str | None = Query(None, description="удалённо | офис | гибрид"),
    salary_bracket: str | None = Query(None, description="low | medium | high"),
    track_hint: str | None = Query(None, max_length=400),
):
    """Ссылка на web-поиск hh.ru по фильтрам вкладки «Вакансии» (без запроса к API)."""
    import sys

    repo = ROOT.parent
    backend = repo / "miniapp" / "backend"
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))
    from wibe_work.services.hh_web_link import build_hh_web_search_url

    from app.hh_search_templates import search_text_for_match

    txt = search_text_for_match(
        interest=interest,
        profession=profession,
        track_hint=track_hint,
    )
    only_remote = bool(
        work_format and ("удал" in work_format.lower() or "remote" in work_format.lower())
    )
    from app.hh_client import normalize_job_experience

    hh_exp = normalize_job_experience(level)
    min_salary = None
    if salary_bracket:
        b = salary_bracket.strip().lower()
        if b == "low":
            min_salary = 50_000
        elif b == "medium":
            min_salary = 80_000
        elif b == "high":
            min_salary = 120_000
    url = build_hh_web_search_url(
        text=txt,
        city=city,
        only_remote=only_remote,
        only_entry_level=hh_exp == "noExperience",
        hh_experience=hh_exp,
        min_salary=min_salary,
        work_format=work_format,
    )
    return {"url": url}


@app.post("/api/jobs/match", response_model=list[VacancyEnriched])
async def jobs_match(body: JobMatchRequest) -> list[VacancyEnriched]:
    try:
        return await match_jobs(body)
    except Exception as e:
        logger.exception("Ошибка персонального матчинга")
        raise HTTPException(status_code=500, detail="Не удалось подобрать вакансии") from e


@app.get("/api/simulator/options")
async def sim_options():
    """Сферы из анкеты и профессии для симулятора дня."""
    return {"options": simulator_options_list()}


@app.get("/api/simulator/start")
async def sim_start(
    role: str = Query("it_dev", description="id сферы анкеты или ключ сценария"),
):
    try:
        return simulator_start(role)
    except Exception as e:
        logger.exception("Симулятор")
        raise HTTPException(status_code=500, detail="Ошибка симулятора") from e


@app.post("/api/simulator/step")
async def sim_step(body: SimulatorAdvance):
    try:
        return simulator_advance(body)
    except Exception as e:
        logger.exception("Симулятор шаг")
        raise HTTPException(status_code=500, detail="Ошибка симулятора") from e


if __name__ == "__main__":
    import os

    import uvicorn

    port = int(os.environ.get("PORT", "8765"))
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=False)
