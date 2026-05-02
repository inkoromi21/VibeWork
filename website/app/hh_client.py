"""
Клиент поиска вакансий через API hh.ru.
Документация: https://api.hh.ru/openapi/redoc
Обязательный заголовок User-Agent (см. раздел «Общая информация»).
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any
import httpx

from app.api_schemas import EducationLevel, Interest, JobMatchRequest, MockVacancy, WorkFormat

logger = logging.getLogger(__name__)

HH_VACANCIES_URL = "https://api.hh.ru/vacancies"

# Населённые пункты: id из справочника areas (частые города РФ)
_CITY_TO_AREA: dict[str, str] = {
    "москва": "1",
    "мск": "1",
    "санкт-петербург": "2",
    "спб": "2",
    "питер": "2",
    "екатеринбург": "3",
    "новосибирск": "4",
    "нижний новгород": "66",
    "казань": "88",
    "самара": "78",
    "омск": "68",
    "ростов-на-дону": "76",
    "ростов": "76",
    "уфа": "99",
    "красноярск": "54",
    "воронеж": "26",
    "пермь": "72",
    "волгоград": "24",
    "краснодар": "53",
    "сочи": "237",
    "тюмень": "95",
    "челябинск": "104",
    "иркутск": "35",
    "барнаул": "11",
    "хабаровск": "28",
    "ярославль": "112",
    "тула": "92",
    "калининград": "41",
}

_INTEREST_SEARCH: dict[Interest, str] = {
    Interest.IT: "программист OR разработчик OR developer",
    Interest.DATA_AI: "аналитик данных OR data analyst OR BI",
    Interest.DEVOPS: "DevOps OR SRE OR инженер инфраструктуры",
    Interest.DESIGN: "дизайнер UX OR UI OR figma",
    Interest.MARKETING: "маркетолог OR digital marketing OR SMM",
    Interest.SALES: "менеджер по продажам OR sales",
    Interest.ENGINEERING: "инженер OR проектировщик CAD",
    Interest.SCIENCE: "лаборант OR научный сотрудник OR исследователь",
    Interest.BUSINESS: "менеджер проектов OR project manager OR ассистент",
    Interest.FINANCE: "финансовый аналитик OR бухгалтер OR экономист",
    Interest.HR: "HR OR рекрутер OR специалист по подбору",
    Interest.LEGAL: "юрист OR legal counsel",
    Interest.PROCUREMENT: "закупки OR снабжение",
    Interest.LOGISTICS: "логист OR склад OR supply chain",
    Interest.REAL_ESTATE: "недвижимость OR эксплуатация зданий",
    Interest.ADMIN: "офис-менеджер OR администратор",
    Interest.PRODUCT: "product manager OR продакт",
    Interest.SUPPORT: "техподдержка OR support OR customer service",
}


def hh_enabled() -> bool:
    return os.getenv("HH_VACANCIES_DISABLED", "").strip().lower() not in ("1", "true", "yes")


def _user_agent() -> str:
    ua = os.getenv("HH_USER_AGENT", "").strip()
    if ua:
        return ua
    return "VibeWork/1.0 (dev@localhost)"


def _norm_city(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def _area_id_for_city(city: str | None) -> str | None:
    if not city or not city.strip():
        return None
    n = _norm_city(city)
    if n in ("удалённо", "удаленно", "remote", "дистанцион"):
        return None
    return _CITY_TO_AREA.get(n)


def _build_search_text(req: JobMatchRequest) -> str:
    if req.profession and req.profession.strip():
        return req.profession.strip()
    return _INTEREST_SEARCH.get(req.interests[0], "специалист")


def _experience_params(level: str | None) -> list[tuple[str, str]]:
    if not level or not level.strip():
        return []
    l = level.strip().lower()
    if l == EducationLevel.INTERN.value:
        return [("experience", "noExperience")]
    if l == EducationLevel.JUNIOR.value:
        return [("experience", "noExperience"), ("experience", "between1And3")]
    if l == EducationLevel.MIDDLE.value:
        return [("experience", "between3And6")]
    if l == EducationLevel.SENIOR.value:
        return [("experience", "moreThan6")]
    return []


def _schedule_param(work_format: str | None) -> str | None:
    if not work_format or not work_format.strip():
        return None
    wf = work_format.strip().lower()
    if wf == WorkFormat.REMOTE.value:
        return "remote"
    if wf == WorkFormat.OFFICE.value:
        return "fullDay"
    if wf == WorkFormat.HYBRID.value:
        return "flexible"
    return None


def _strip_html(s: str | None) -> str:
    if not s:
        return ""
    t = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", t).strip()


def _requirements_from_snippet(req_snip: str | None, resp_snip: str | None) -> list[str]:
    req_snip = _strip_html(req_snip)
    resp_snip = _strip_html(resp_snip)
    chunks: list[str] = []
    for block in (req_snip, resp_snip):
        if not block:
            continue
        for part in re.split(r"[•\n;]|(?<=[.!?])\s+", block):
            p = part.strip()
            if len(p) >= 12:
                chunks.append(p[:220])
        if len(chunks) >= 6:
            break
    if not chunks and req_snip:
        chunks = [req_snip[:400]]
    if not chunks and resp_snip:
        chunks = [resp_snip[:400]]
    if not chunks:
        chunks = ["Откройте полное описание на hh.ru"]
    return chunks[:6]


def _salary_from_item(sal: dict[str, Any] | None) -> tuple[str | None, int | None]:
    if not sal:
        return None, None
    cur = sal.get("currency")
    f = sal.get("from")
    t = sal.get("to")
    gross = sal.get("gross")
    g = " до вычета НДФЛ" if gross else " на руки"
    if cur != "RUR" and cur != "RUB":
        if f or t:
            return (f"{f or '?'}-{t or '?'} {cur}", int(f) if f else None)
        return None, None
    if f and t:
        hint = f"{f:,} – {t:,} ₽{g}".replace(",", " ")
        return hint, int(f)
    if f:
        hint = f"от {int(f):,} ₽{g}".replace(",", " ")
        return hint, int(f)
    if t:
        hint = f"до {int(t):,} ₽{g}".replace(",", " ")
        return hint, int(t)
    return None, None


def _schedule_to_work_format(sched: dict[str, Any] | None) -> WorkFormat:
    if not sched:
        return WorkFormat.HYBRID
    sid = (sched.get("id") or "").lower()
    name = (sched.get("name") or "").lower()
    if sid == "remote" or "удал" in name:
        return WorkFormat.REMOTE
    if sid == "flexible" or "гибк" in name:
        return WorkFormat.HYBRID
    return WorkFormat.OFFICE


def _exp_to_level(exp: dict[str, Any] | None) -> EducationLevel:
    if not exp:
        return EducationLevel.JUNIOR
    i = exp.get("id") or ""
    if i == "noExperience":
        return EducationLevel.INTERN
    if i == "between1And3":
        return EducationLevel.JUNIOR
    if i == "between3And6":
        return EducationLevel.MIDDLE
    if i == "moreThan6":
        return EducationLevel.SENIOR
    return EducationLevel.JUNIOR


def _item_to_mock(item: dict[str, Any], primary: Interest) -> MockVacancy:
    vid = str(item.get("id", ""))
    name = item.get("name") or "Вакансия"
    emp = item.get("employer") or {}
    company = emp.get("name") or "Компания"
    area = item.get("area") or {}
    city = area.get("name") or "Россия"
    snippet = item.get("snippet") or {}
    reqs = _requirements_from_snippet(snippet.get("requirement"), snippet.get("responsibility"))
    salary_hint, salary_min = _salary_from_item(item.get("salary"))
    wf = _schedule_to_work_format(item.get("schedule"))
    lvl = _exp_to_level(item.get("experience"))
    alt = item.get("alternate_url") or f"https://hh.ru/vacancy/{vid}"
    tag = primary.value.replace("_", " ")
    return MockVacancy(
        id=f"hh-{vid}",
        title=name[:200],
        company=company[:120],
        requirements=reqs,
        profession_tag=tag[:80],
        level=lvl,
        salary_hint=salary_hint,
        city=city[:80],
        work_format=wf,
        salary_min_rub=salary_min,
        source_url=alt,
    )


async def fetch_hh_vacancies(req: JobMatchRequest) -> list[MockVacancy]:
    if not hh_enabled():
        return []

    text = _build_search_text(req)
    params: list[tuple[str, str]] = [
        ("text", text),
        ("per_page", "25"),
        ("page", "0"),
        ("order_by", "relevance"),
        ("only_with_salary", "false"),
    ]

    aid = _area_id_for_city(req.city)
    if aid:
        params.append(("area", aid))

    params.extend(_experience_params(req.level))

    sched = _schedule_param(req.work_format)
    if sched:
        params.append(("schedule", sched))

    # Зарплатный коридор как подсказка API (мягкий)
    sb = (req.salary_bracket or "").strip().lower()
    if sb == "high":
        params.append(("salary", "120000"))
        params.append(("only_with_salary", "true"))
    elif sb == "medium":
        params.append(("salary", "70000"))
        params.append(("only_with_salary", "true"))
    elif sb == "low":
        params.append(("only_with_salary", "false"))

    headers = {"User-Agent": _user_agent(), "Accept": "application/json"}
    timeout = float(os.getenv("HH_REQUEST_TIMEOUT", "22"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(HH_VACANCIES_URL, params=params, headers=headers)
        r.raise_for_status()
        data = r.json()

    items = data.get("items") or []
    primary = req.interests[0]
    out = [_item_to_mock(it, primary) for it in items if it.get("id")]
    logger.info("hh.ru: получено вакансий: %s", len(out))
    return out
