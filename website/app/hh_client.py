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
HH_SUGGEST_AREAS_URL = "https://api.hh.ru/suggests/areas"

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


def _primary_profession_tag(interest: Interest) -> str:
    """Канонический тег как в демо-вакансиях (для матчинга по интересу)."""
    m = {
        Interest.IT: "IT",
        Interest.DATA_AI: "IT",
        Interest.DEVOPS: "IT",
        Interest.DESIGN: "дизайн",
        Interest.MARKETING: "маркетинг",
        Interest.SALES: "маркетинг",
        Interest.SUPPORT: "маркетинг",
        Interest.PRODUCT: "маркетинг",
        Interest.ENGINEERING: "инженерия",
        Interest.SCIENCE: "наука",
        Interest.LOGISTICS: "инженерия",
        Interest.BUSINESS: "бизнес",
        Interest.FINANCE: "бизнес",
        Interest.HR: "бизнес",
        Interest.LEGAL: "бизнес",
        Interest.PROCUREMENT: "бизнес",
        Interest.REAL_ESTATE: "бизнес",
        Interest.ADMIN: "бизнес",
    }
    return m.get(interest, "бизнес")


def _infer_profession_tag(title: str, reqs: list[str], primary: Interest) -> str:
    """Тег области по заголовку и требованиям (не подставляем код интереса целиком)."""
    blob = (title + " " + " ".join(reqs)).lower()
    if re.search(
        r"(дизайнер|ux\b|ui\b|figma|product design|графическ)",
        blob,
    ):
        return "дизайн"
    if re.search(
        r"(маркетолог|smm|таргет|performance|digital marketing|копирайт|pr-менедж)",
        blob,
    ):
        return "маркетинг"
    if re.search(
        r"(программист|разработчик|developer|devops|sre|frontend|backend|"
        r"fullstack|тестировщик|qa engineer|python|golang|\.net|mobile)",
        blob,
    ):
        return "IT"
    if re.search(
        r"(аналитик данных|data analyst|data scientist|bi analyst|machine learning)",
        blob,
    ):
        return "IT"
    if re.search(r"(инженер|проектировщик|cad|сварщ|монтажник|электромонт)", blob):
        return "инженерия"
    if re.search(r"(лаборант|научн|исследовател|биолог|химик)", blob):
        return "наука"
    if re.search(
        r"(менеджер по продажам|sales manager|b2b|account manager|коммерческ)",
        blob,
    ):
        return "маркетинг"
    if re.search(
        r"(hr\b|рекрутер|подбор персонала|кадров|обучени[ея] персонал)",
        blob,
    ):
        return "бизнес"
    if re.search(r"(юрист|legal counsel|комплаенс)", blob):
        return "бизнес"
    if re.search(r"(бухгалтер|финансов|экономист|казначей)", blob):
        return "бизнес"
    if re.search(r"(логист|склад|supply chain|экспедитор)", blob):
        return "инженерия"
    if re.search(r"(product manager|продакт|product owner)", blob):
        return "маркетинг"
    if re.search(r"(поддержк|support|customer service|call.?center)", blob):
        return "маркетинг"
    return _primary_profession_tag(primary)


def _build_search_text(req: JobMatchRequest) -> str:
    if req.profession and req.profession.strip():
        p = req.profession.strip()
        # Короткая подпись сферы («Маркетинг») — ищем по шаблону интереса, не дословно.
        if len(p) < 40 and " or " not in p.lower():
            templ = _INTEREST_SEARCH.get(req.interests[0])
            if templ:
                return templ
        return p
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
    tag = _infer_profession_tag(name, reqs, primary)
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


async def suggest_areas(text: str, *, limit: int = 15) -> list[dict[str, str]]:
    """Подсказки городов и регионов РФ через API hh.ru (/suggests/areas)."""
    t = (text or "").strip()
    if len(t) < 2:
        return []
    headers = {"User-Agent": _user_agent(), "Accept": "application/json"}
    timeout = float(os.getenv("HH_REQUEST_TIMEOUT", "12"))
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(HH_SUGGEST_AREAS_URL, params={"text": t}, headers=headers)
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, ValueError) as e:
        logger.debug("hh.ru area suggest failed: %s", e)
        return []

    raw_items = data.get("items") or []
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for it in raw_items:
        tid = it.get("id")
        name = (it.get("text") or "").strip()
        if tid is None or not name:
            continue
        sid = str(tid)
        key = sid + "\n" + name.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append({"id": sid, "text": name})

    prefix = t.lower()
    pref_match = [x for x in out if x["text"].lower().startswith(prefix)]
    if not pref_match:
        pref_match = [x for x in out if prefix in x["text"].lower()]
    return pref_match[:limit] if pref_match else out[:limit]


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
