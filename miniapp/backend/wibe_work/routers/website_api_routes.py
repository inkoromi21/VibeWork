"""HTTP API веб-части: /api/analyze, /api/chat, … (тот же процесс, что и миниаппа).

Код в `website/app` (в `miniapp/run.py` папка `website/` в sys.path как пакет `app`)."""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Query

from wibe_work.services.hh_client import suggest_areas
from wibe_work.services.hh_web_link import build_hh_web_search_url

try:
    from app.api_schemas import (  # type: ignore
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
    from app.career_advisor import (  # type: ignore
        build_analysis,
        career_chat,
        llm_configured,
        load_vacancies_for_match,
        match_jobs,
        mts_preview_rank,
        quiz_questions_bundle,
        simulator_advance,
        simulator_start,
    )
    from app.mts_tracks_catalog import MtsTrack, load_mts_tracks  # type: ignore
    from app.questionnaire_fields import get_profile_schema  # type: ignore
except Exception as e:  # pragma: no cover
    # Нет папки website/ или не ставили зависимости — роутер есть, но вызовы упадут.
    _IMPORT_ERROR = e
else:
    _IMPORT_ERROR = None


router = APIRouter(tags=["website"])


def _ensure_imports() -> None:
    if _IMPORT_ERROR is not None:
        raise HTTPException(
            status_code=500,
            detail=f"website modules not importable: {_IMPORT_ERROR}",
        )


@router.get("/api/health")
async def health():
    return {"status": "ok"}


@router.get("/api/profile/schema")
async def profile_schema():
    _ensure_imports()
    return get_profile_schema()


@router.get("/api/health/llm")
async def health_llm():
    from wibe_work.services.llm_health import build_llm_health_payload

    return build_llm_health_payload()


@router.get("/api/mts/tracks")
async def mts_tracks():
    _ensure_imports()
    return list(load_mts_tracks())


@router.get("/api/quiz/questions")
async def quiz_questions(
    interest: str = Query(..., description="Значение из профиля: IT, дизайн, маркетинг, …"),
    target_mts_role_id: str | None = Query(None, description="id роли из /api/mts/tracks"),
    education_detail: str | None = Query(None, description="id уровня образования из анкеты"),
    course_grade: str | None = Query(None, description="Класс или курс"),
    age: int | None = Query(None, ge=10, le=80),
):
    """Вопросы теста под интерес, образование и класс/курс (как на standalone-сайте)."""
    _ensure_imports()
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


@router.post("/api/mts/preview")
async def mts_preview(body: MtsPreviewPayload):
    _ensure_imports()
    try:
        return mts_preview_rank(body)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.post("/api/chat")
async def chat(body: ChatRequest):
    _ensure_imports()
    try:
        text, source, notice = await career_chat(body)
        return ChatResponse(reply=text, source=source, notice=notice)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Не удалось получить ответ") from e


@router.post("/api/analyze")
async def analyze(payload: DiagnosisPayload):
    _ensure_imports()
    try:
        return await build_analysis(payload)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера") from e


@router.get("/api/jobs")
async def jobs(
    profession: str | None = Query(None),
    level: str | None = Query(None),
    city: str | None = Query(None),
    work_format: str | None = Query(None, description="удалённо | офис | гибрид"),
    salary_bracket: str | None = Query(None, description="low | medium | high"),
    interest: str = Query("IT", description="Код из профиля: IT, дизайн, маркетинг, …"),
):
    _ensure_imports()
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
        raise HTTPException(status_code=500, detail="Не удалось загрузить вакансии") from e


@router.post("/api/jobs/match")
async def jobs_match(body: JobMatchRequest):
    _ensure_imports()
    try:
        return await match_jobs(body)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Не удалось подобрать вакансии") from e


@router.get("/api/hh/area-suggest")
async def hh_area_suggest(q: str = Query("", max_length=120)):
    """Подсказки городов и регионов РФ (префиксный поиск hh.ru)."""
    return {"items": suggest_areas(q.strip(), limit=15)}


@router.get("/api/hh/search-url")
async def hh_search_url(
    profession: str | None = Query(None, description="id сферы анкеты"),
    interest: str | None = Query(None, description="Код интереса: IT, дизайн, маркетинг, …"),
    level: str | None = Query(None),
    city: str | None = Query(None),
    work_format: str | None = Query(None, description="удалённо | офис | гибрид"),
    salary_bracket: str | None = Query(None, description="low | medium | high"),
    track_hint: str | None = Query(None, max_length=400),
):
    """
    Ссылка на web-поиск hh.ru по текущим фильтрам сайта.
    Никаких запросов к API hh.ru (важно при блокировках).
    """
    from app.hh_search_templates import search_text_for_match

    txt = search_text_for_match(
        interest=interest,
        profession=profession,
        track_hint=track_hint,
    )
    from app.hh_client import normalize_job_experience

    only_remote = bool(work_format and ("удал" in work_format.lower() or "remote" in work_format.lower()))
    hh_exp = normalize_job_experience(level)
    only_entry = hh_exp == "noExperience"
    # salary_bracket маппится внутри build_hh_web_search_url (через int-попытку не пройдёт),
    # поэтому конвертируем вручную для предсказуемости:
    min_salary = None
    if salary_bracket:
        b = salary_bracket.strip().lower()
        if b == "low":
            min_salary = 50000
        elif b == "medium":
            min_salary = 80000
        elif b == "high":
            min_salary = 120000
    url = build_hh_web_search_url(
        text=txt,
        city=city,
        only_remote=only_remote,
        only_entry_level=only_entry,
        hh_experience=hh_exp,
        min_salary=min_salary,
        work_format=work_format,
    )
    return {"url": url}


@router.get("/api/simulator/options")
async def sim_options():
    from wibe_work.services.workday_simulator import list_simulator_options

    return {"options": list_simulator_options()}


@router.get("/api/simulator/start")
async def sim_start(role: str = Query("it_dev", description="id сферы анкеты или ключ сценария")):
    _ensure_imports()
    try:
        return simulator_start(role)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка симулятора") from e


@router.post("/api/simulator/step")
async def sim_step(body: SimulatorAdvance):
    _ensure_imports()
    try:
        return simulator_advance(body)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка симулятора") from e

