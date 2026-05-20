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
    _ensure_imports()
    return {"llm_configured": llm_configured()}


@router.get("/api/mts/tracks")
async def mts_tracks():
    _ensure_imports()
    return list(load_mts_tracks())


@router.get("/api/quiz/questions")
async def quiz_questions(
    interest: str = Query(..., description="Значение из профиля: IT, дизайн, маркетинг, …"),
    target_mts_role_id: str | None = Query(None, description="id роли из /api/mts/tracks"),
):
    _ensure_imports()
    return quiz_questions_bundle(interest, target_mts_role_id)


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
    profession: str | None = Query(None),
    interest: str | None = Query(None, description="Код интереса: IT, дизайн, маркетинг, …"),
    level: str | None = Query(None),
    city: str | None = Query(None),
    work_format: str | None = Query(None, description="удалённо | офис | гибрид"),
    salary_bracket: str | None = Query(None, description="low | medium | high"),
):
    """
    Ссылка на web-поиск hh.ru по текущим фильтрам сайта.
    Никаких запросов к API hh.ru (важно при блокировках).
    """
    txt = (profession or "").strip()
    if not txt and interest:
        try:
            from app.hh_client import _INTEREST_SEARCH  # type: ignore

            intr = Interest(interest.strip())
            tmpl = _INTEREST_SEARCH.get(intr, "")
            if tmpl:
                txt = re.sub(r"\s+OR\s+", " ", tmpl, flags=re.IGNORECASE).strip()[:120]
        except (ValueError, ImportError):
            txt = interest.strip().replace("_", " ")
    if not txt:
        txt = "вакансии"
    only_remote = bool(work_format and ("удал" in work_format.lower() or "remote" in work_format.lower()))
    only_entry = bool(level and ("стаж" in level.lower() or "intern" in level.lower()))
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
        min_salary=min_salary,
        work_format=work_format,
        level=level,
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

