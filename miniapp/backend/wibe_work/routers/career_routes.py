from typing import Optional

import requests
from fastapi import APIRouter, HTTPException, Request

from wibe_work.bearer_auth import require_bearer_matches_user
from wibe_work.sqlite_db import get_db
from wibe_work.api_schemas import CompetencyBulkRequest
from wibe_work.services.agent_orchestrator import build_full_report
from wibe_work.services.career_navigator import build_navigator
from wibe_work.services.diagnostics import run_diagnostics
from wibe_work.services.hh_client import search_vacancies, slim_vacancy_items
from wibe_work.services.hh_filter import (
    build_filter_bundle,
    can_finalize_hh_filter,
    fetch_live_hh_vacancies,
    load_user_hh_state,
    regenerate_user_hh_bundle,
    save_user_hh_state,
)
from wibe_work.services.hh_web_link import build_hh_web_search_url, demo_hh_items
from wibe_work.services.job_search import match_jobs_for_user
from wibe_work.services.mts_match import match_mts_roles
from wibe_work.services.user_pain_mapping import align_pains
from wibe_work.services.recommendations import run_recommendations
from wibe_work.services.user_context import load_competencies, load_profile

router = APIRouter(prefix="/career", tags=["career_agent"])


def _v(request: Request, user_id: str) -> None:
    require_bearer_matches_user(request, user_id)


@router.get("/diagnostics/{user_id}")
async def get_diagnostics(user_id: str, request: Request):
    _v(request, user_id)
    profile = load_profile(user_id)
    competencies = load_competencies(user_id)
    return run_diagnostics(profile, competencies)


@router.get("/recommendations/{user_id}")
async def get_recommendations(user_id: str, request: Request):
    _v(request, user_id)
    profile = load_profile(user_id)
    competencies = load_competencies(user_id)
    return run_recommendations(profile, competencies)


@router.get("/navigator/{user_id}")
async def get_navigator(
    user_id: str, request: Request, target_direction: Optional[str] = None
):
    _v(request, user_id)
    profile = load_profile(user_id)
    competencies = load_competencies(user_id)
    return build_navigator(profile, competencies, target_direction=target_direction)


@router.get("/jobs/{user_id}")
async def get_jobs(
    user_id: str,
    request: Request,
    max_listing_age_days: int = 120,
    only_remote: bool = False,
    only_entry_level: bool = False,
    min_salary: Optional[int] = None,
    strict_work_format: bool = False,
):
    _v(request, user_id)
    profile = load_profile(user_id)
    competencies = load_competencies(user_id)
    return match_jobs_for_user(
        user_id,
        profile,
        competencies,
        max_age_days=max_listing_age_days,
        only_remote=only_remote,
        only_entry_level=only_entry_level,
        min_salary=min_salary,
        strict_work_format=strict_work_format,
    )


@router.get("/jobs/hh-live/{user_id}")
async def get_hh_live_jobs(
    user_id: str,
    request: Request,
    page: int = 0,
    per_page: int = 15,
    only_remote: bool = False,
    only_entry_level: bool = False,
    min_salary: Optional[int] = None,
    strict_work_format: bool = False,
    hh_city: Optional[str] = None,
    search_direction: Optional[str] = None,
):
    """Вакансии с hh.ru по профилю (без POST finalize)."""
    _v(request, user_id)
    try:
        return fetch_live_hh_vacancies(
            user_id,
            only_remote=only_remote,
            only_entry_level=only_entry_level,
            min_salary=min_salary,
            strict_work_format=strict_work_format,
            page=page,
            per_page=per_page,
            city_override=hh_city,
            search_direction=search_direction,
        )
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response is not None else None
        # Фоллбек: если hh API заблокирован/403 — показываем демо и даём web-ссылку.
        profile = load_profile(user_id) or {}
        text = (
            (profile.get("target_direction") or "")
            or (profile.get("profession") or "")
            or (profile.get("interest") or "")
            or "вакансии"
        )
        city = hh_city or profile.get("city")
        hh_url = build_hh_web_search_url(
            text=str(text),
            city=str(city) if city else None,
            only_remote=only_remote,
            only_entry_level=only_entry_level,
            min_salary=min_salary,
            work_format="remote" if only_remote else None,
            level="стажер" if only_entry_level else None,
        )
        items = demo_hh_items(hh_url)
        return {
            "source": "demo",
            "notice": "hh.ru API недоступен (часто блокировка по сети/провайдеру). Показаны демо-вакансии — откройте поиск на hh.ru по кнопке.",
            "hh_search_url": hh_url,
            "search_hint": {"text": str(text), "city": str(city) if city else None},
            "found": len(items),
            "pages": 1,
            "page": 0,
            "per_page": per_page,
            "items": items,
        }
    except requests.RequestException as e:
        profile = load_profile(user_id) or {}
        text = (
            (profile.get("target_direction") or "")
            or (profile.get("profession") or "")
            or (profile.get("interest") or "")
            or "вакансии"
        )
        city = hh_city or profile.get("city")
        hh_url = build_hh_web_search_url(
            text=str(text),
            city=str(city) if city else None,
            only_remote=only_remote,
            only_entry_level=only_entry_level,
            min_salary=min_salary,
            work_format="remote" if only_remote else None,
            level="стажер" if only_entry_level else None,
        )
        items = demo_hh_items(hh_url)
        return {
            "source": "demo",
            "notice": "Сеть до hh.ru недоступна. Показаны демо-вакансии — откройте поиск на hh.ru по кнопке.",
            "hh_search_url": hh_url,
            "search_hint": {"text": str(text), "city": str(city) if city else None},
            "found": len(items),
            "pages": 1,
            "page": 0,
            "per_page": per_page,
            "items": items,
        }


@router.get("/pains/{user_id}")
async def get_pain_alignment(user_id: str, request: Request):
    _v(request, user_id)
    profile = load_profile(user_id)
    return align_pains(profile)


@router.get("/mts-match/{user_id}")
async def get_mts_match(user_id: str, request: Request, top_n: int = 5):
    _v(request, user_id)
    profile = load_profile(user_id)
    competencies = load_competencies(user_id)
    return match_mts_roles(profile, competencies, top_n=top_n)


@router.get("/report/{user_id}")
async def get_full_report(user_id: str, request: Request):
    _v(request, user_id)
    return build_full_report(user_id)


@router.get("/competencies/{user_id}")
async def list_competencies(user_id: str, request: Request):
    _v(request, user_id)
    return {"user_id": user_id, "items": load_competencies(user_id)}


@router.post("/hh/finalize/{user_id}")
async def hh_finalize_filter(user_id: str, request: Request, force: bool = False):
    _v(request, user_id)
    ok, msg, extra = can_finalize_hh_filter(user_id, force=force)
    if not ok:
        raise HTTPException(status_code=400, detail={"message": msg, **extra})
    bundle = build_filter_bundle(user_id)
    save_user_hh_state(user_id, bundle, tests_completed=True)
    return {"status": "ok", "message": "Фильтр сохранён. Используйте GET /career/hh/vacancies/", **bundle}


@router.post("/hh/regenerate/{user_id}")
async def hh_regenerate_filter(user_id: str, request: Request, force: bool = True):
    """Сбросить сохранённый hh-фильтр и собрать заново из анкеты (как finalize, но с удалением старого)."""
    _v(request, user_id)
    ok, msg, extra = regenerate_user_hh_bundle(user_id, force=force)
    if not ok:
        raise HTTPException(status_code=400, detail={"message": msg, **{k: v for k, v in extra.items() if k != "bundle"}})
    bundle = extra.get("bundle") or {}
    return {
        "status": "ok",
        "message": "Фильтр сброшен и пересобран из анкеты.",
        **bundle,
    }


@router.get("/hh/filter/{user_id}")
async def hh_get_saved_filter(user_id: str, request: Request):
    _v(request, user_id)
    st = load_user_hh_state(user_id)
    if not st or not st.get("tests_completed"):
        raise HTTPException(
            status_code=404,
            detail="Фильтр не создан. Вызовите POST /career/hh/finalize/{user_id}",
        )
    return st


@router.get("/hh/vacancies/{user_id}")
async def hh_search_vacancies(
    user_id: str, request: Request, page: int = 0, per_page: int = 20
):
    _v(request, user_id)
    st = load_user_hh_state(user_id)
    if not st or not st.get("tests_completed"):
        raise HTTPException(
            status_code=403,
            detail="Сначала зафиксируйте фильтр: POST /career/hh/finalize/{user_id}",
        )
    filt = st.get("filter") or {}
    params = dict(filt.get("query_params") or {})
    params["page"] = max(0, page)
    params["per_page"] = min(100, max(1, per_page))
    try:
        raw = search_vacancies(params)
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response is not None else None
        if code == 403:
            raise HTTPException(
                status_code=502,
                detail=(
                    "Ошибка API hh.ru: 403 Forbidden. "
                    "hh.ru требует корректный заголовок User-Agent с контактом разработчика. "
                    "Задайте в .env: HH_USER_AGENT=MyApp/1.0 (you@example.com) и перезапустите API."
                ),
            ) from e
        raise HTTPException(
            status_code=502,
            detail=f"Ошибка API hh.ru: {e.response.status_code if e.response else e}",
        ) from e
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Сеть: {e}") from e
    return {
        "user_id": user_id,
        "request_params": params,
        "found": raw.get("found"),
        "pages": raw.get("pages"),
        "page": raw.get("page"),
        "per_page": raw.get("per_page"),
        "items": slim_vacancy_items(raw),
        "hh_api_note": "Документация: https://api.hh.ru/openapi/redoc",
    }


@router.post("/competencies/{user_id}")
async def replace_competencies(
    user_id: str, body: CompetencyBulkRequest, request: Request
):
    _v(request, user_id)
    with get_db() as conn:
        conn.execute("DELETE FROM user_competencies WHERE user_id = ?", (user_id,))
        for item in body.items:
            conn.execute(
                """INSERT INTO user_competencies (user_id, name, level)
                   VALUES (?, ?, ?)""",
                (user_id, item.name.strip(), item.level),
            )
        conn.commit()
    return {"status": "ok", "count": len(body.items)}
