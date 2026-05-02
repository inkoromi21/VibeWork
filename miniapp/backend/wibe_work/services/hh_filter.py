import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from wibe_work.sqlite_db import get_db
from wibe_work.services.diagnostics import run_diagnostics
from wibe_work.services.recommendations import run_recommendations
from wibe_work.services.hh_client import search_vacancies, slim_vacancy_items, suggest_area_id
from wibe_work.services.user_context import (
    load_competencies,
    load_profile,
    merge_skills_from_profile,
    parse_interest_spheres,
)


def _has_any_skill(profile: Dict[str, Any], competencies: List[Dict[str, Any]]) -> bool:
    if competencies:
        return True
    for k in (
        "software_skills",
        "programming_skills",
        "social_media_skills",
    ):
        if profile.get(k) and str(profile.get(k)).strip():
            return True
    return False


def _has_interests(profile: Dict[str, Any]) -> bool:
    if profile.get("interests") and str(profile["interests"]).strip():
        return True
    if profile.get("like_to_do") and str(profile["like_to_do"]).strip():
        return True
    if parse_interest_spheres(profile):
        return True
    return False


def count_distinct_poll_answers(user_id: str) -> int:
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(DISTINCT question_id) AS c FROM answers WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return int(row["c"]) if row else 0


def can_finalize_hh_filter(
    user_id: str, force: bool = False
) -> Tuple[bool, str, Dict[str, Any]]:
    if force:
        return True, "force", {}
    profile = load_profile(user_id)
    competencies = load_competencies(user_id)
    diag = run_diagnostics(profile, competencies)
    score = float(diag.get("profile_completeness_score") or 0)
    from wibe_work.config import HH_FINALIZE_MIN_COMPLETENESS, HH_MIN_POLL_ANSWERS

    if score < HH_FINALIZE_MIN_COMPLETENESS:
        return (
            False,
            f"Низкая полнота профиля ({score}); заполните анкету или передайте force=true.",
            {"diagnostics": diag},
        )
    if not _has_interests(profile):
        return False, "Укажите интересы, «что нравится» или сферы interest_spheres.", {
            "diagnostics": diag
        }
    if not _has_any_skill(profile, competencies):
        return (
            False,
            "Добавьте навыки (компетенции или поля программ/кода).",
            {"diagnostics": diag},
        )
    n_ans = count_distinct_poll_answers(user_id)
    if HH_MIN_POLL_ANSWERS > 0 and n_ans < HH_MIN_POLL_ANSWERS:
        return (
            False,
            f"Нужно минимум {HH_MIN_POLL_ANSWERS} ответов в опросах (сейчас {n_ans}).",
            {"diagnostics": diag, "poll_answers_distinct": n_ans},
        )
    return True, "ok", {"diagnostics": diag, "poll_answers_distinct": n_ans}


def _map_experience(profile: Dict[str, Any]) -> str:
    off = profile.get("experience_official")
    if off and str(off).strip():
        low = str(off).lower()
        if any(x in low for x in ("год", "лет", "12 ", "24 ", "36 ")):
            return "between1And3"
        return "between1And3"
    return "noExperience"


def _map_schedule(profile: Dict[str, Any]) -> Optional[str]:
    pref = (profile.get("work_format_preference") or "").lower()
    if "удал" in pref:
        return "remote"
    return None


def _map_employment(profile: Dict[str, Any]) -> Optional[str]:
    sched = (profile.get("work_schedule") or "").lower()
    hours = profile.get("hours_per_week")
    try:
        h = int(hours) if hours is not None else None
    except (TypeError, ValueError):
        h = None
    if h is not None and h <= 24:
        return "part"
    if "выходн" in sched or "после пар" in sched or "неполн" in sched:
        return "part"
    return "full"


# Паттерны для извлечения стека из анкеты (не использовать «навыки к первому офферу» — там учебные фразы).
_HH_STACK_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\bpython\b", re.I), "Python"),
    (re.compile(r"\bdjango\b|\bflask\b|\bfastapi\b|\bpytorch\b", re.I), "Python"),
    (re.compile(r"\bjavascript\b", re.I), "JavaScript"),
    (re.compile(r"\btypescript\b", re.I), "TypeScript"),
    (re.compile(r"(?<![\w/])js(?![\w/])", re.I), "JavaScript"),
    (re.compile(r"\breact\b", re.I), "React"),
    (re.compile(r"\bvue\.?js\b|\bvue\b", re.I), "Vue"),
    (re.compile(r"\bnode\.?js\b|\bnodejs\b", re.I), "Node.js"),
    (re.compile(r"\bjava\b", re.I), "Java"),
    (re.compile(r"\bc\+\+\b", re.I), "C++"),
    (re.compile(r"\bc#\b", re.I), "C#"),
    (re.compile(r"\bgo\b|\bgolang\b", re.I), "Go"),
    (re.compile(r"\brust\b", re.I), "Rust"),
    (re.compile(r"\bkotlin\b", re.I), "Kotlin"),
    (re.compile(r"\bswift\b", re.I), "Swift"),
    (re.compile(r"\bphp\b", re.I), "PHP"),
    (re.compile(r"\bruby\b", re.I), "Ruby"),
    (re.compile(r"\b1c\b|\b1с\b", re.I), "1С"),
    (re.compile(r"\bsql\b", re.I), "SQL"),
]

_LABEL_PRIORITY: Dict[str, int] = {
    "Python": 100,
    "JavaScript": 95,
    "TypeScript": 92,
    "React": 90,
    "Node.js": 88,
    "Java": 85,
    "C#": 82,
    "C++": 80,
    "Go": 75,
    "Kotlin": 72,
    "Swift": 70,
    "PHP": 65,
    "Ruby": 63,
    "Rust": 60,
    "Vue": 58,
    "SQL": 55,
    "1С": 50,
}

_SPHERE_SLUGS_SKIP = frozenset(
    {
        "it",
        "it_dev",
        "dev",
        "other",
        "any",
        "прочее",
    }
)

# Для IT-выдачи: заголовок должен явно относиться к техролям (отсекает «начинающий сотрудник в ресторан» и т.п.).
_IT_TITLE_PATTERN = re.compile(
    r"(программист|разработчик|developer|devops|frontend|backend|"
    r"fullstack|full-stack|full\s+stack|тестиров|\bqa\b|software|"
    r"mobile|ios|android|1\s*[сc]\b|data\s+engineer|"
    r"java\b|python|golang|kotlin|typescript|\bphp\b|scala|rust|"
    r"\(it\))",
    re.I,
)


def _is_it_search_direction(direction: str) -> bool:
    d = (direction or "").lower()
    return "it" in d or "разработ" in d


def _profile_search_blob(profile: Dict[str, Any], skill_names: List[str]) -> str:
    parts = [
        str(profile.get("programming_skills") or ""),
        str(profile.get("software_skills") or ""),
        str(profile.get("interests") or ""),
        str(profile.get("like_to_do") or ""),
        " ".join(skill_names),
    ]
    return " ".join(p for p in parts if p)


def _extract_stack_labels(profile: Dict[str, Any], competencies: List[Dict[str, Any]]) -> List[str]:
    names, _ = merge_skills_from_profile(competencies, profile)
    blob = _profile_search_blob(profile, names)
    seen: set = set()
    hits: List[Tuple[int, str]] = []
    for rx, label in _HH_STACK_PATTERNS:
        if label in seen:
            continue
        if rx.search(blob):
            seen.add(label)
            hits.append((_LABEL_PRIORITY.get(label, 0), label))
    hits.sort(key=lambda x: -x[0])
    return [h[1] for h in hits]


def _usable_sphere_token(raw: str) -> Optional[str]:
    t = (raw or "").strip()
    if not t or len(t) > 32:
        return None
    low = re.sub(r"\s+", "_", t.lower())
    if low in _SPHERE_SLUGS_SKIP:
        return None
    if re.fullmatch(r"[a-z][a-z0-9_]{1,20}", low):
        return None
    return t


def _hh_search_phrase(
    direction: str, stack: List[str], spheres: List[str]
) -> str:
    """Короткая строка для поля text на hh.ru (роль + стек), без простыней из анкеты."""
    d = (direction or "").strip()
    dl = d.lower()
    if "it" in d or "разработ" in dl:
        if stack:
            return f"{stack[0]} разработчик"
        # Без «junior/начинающий» в text: иначе hh матчит по «начинающий» и тянет нерелевантные вакансии.
        return "разработчик программист"
    if "аналит" in dl:
        if "Python" in stack[:2]:
            return "аналитик данных Python"
        if "SQL" in stack[:2]:
            return "аналитик SQL"
        return "аналитик данных"
    if "дизайн" in dl:
        return "UX дизайнер"
    if "маркет" in dl or "продаж" in dl:
        return "маркетолог"
    if "продукт" in dl or "управлен" in dl:
        return "продакт менеджер"
    if "hr" in dl or "подбор" in dl:
        return "рекрутер"
    if "юрис" in dl:
        return "юрист"
    if "инженер" in dl:
        return "инженер"
    if "образован" in dl or "наук" in dl:
        return "преподаватель"
    for s in spheres[:2]:
        u = _usable_sphere_token(s)
        if u:
            return u[:40]
    return "стажировка начинающий специалист"


def _build_search_text(
    profile: Dict[str, Any],
    rec: Dict[str, Any],
    competencies: List[Dict[str, Any]],
) -> str:
    stack = _extract_stack_labels(profile, competencies)[:2]
    spheres = parse_interest_spheres(profile)
    direction = str(rec.get("primary_direction") or "")
    text = _hh_search_phrase(direction, stack, spheres)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:120] if text else "стажировка начинающий специалист"


# Как в OpenAPI hh.ru GET /vacancies, параметр experience
HH_EXPERIENCE_API_IDS = frozenset(
    {"noExperience", "between1And3", "between3And6", "moreThan6"}
)


def apply_user_experience_filter(
    params: Dict[str, Any],
    *,
    hh_experience: Optional[str] = None,
    only_entry_level: bool = False,
) -> None:
    """Учитывает фильтр «Опыт» из UI миниаппа (те же значения, что на hh.ru)."""
    if only_entry_level:
        params["experience"] = "noExperience"
        return
    if hh_experience is None:
        return
    s = str(hh_experience).strip()
    if not s or s.lower() == "any":
        params.pop("experience", None)
        return
    if s.lower() == "entry":
        params["experience"] = "noExperience"
        return
    if s in HH_EXPERIENCE_API_IDS:
        params["experience"] = s


def build_hh_query_params(
    profile: Dict[str, Any],
    rec: Dict[str, Any],
    area_id: Optional[str],
    competencies: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    comps = competencies if competencies is not None else []
    text = _build_search_text(profile, rec, comps)

    params: Dict[str, Any] = {
        "text": text or "стажер",
        "per_page": 20,
        "page": 0,
        "order_by": "publication_time",
    }
    if area_id:
        params["area"] = area_id
    sal = profile.get("target_salary")
    if sal:
        try:
            params["salary"] = int(sal)
            params["only_with_salary"] = "true"
        except (TypeError, ValueError):
            pass
    params["experience"] = _map_experience(profile)
    emp = _map_employment(profile)
    if emp:
        params["employment"] = emp
    sch = _map_schedule(profile)
    if sch:
        params["schedule"] = sch
    direction = str(rec.get("primary_direction") or "")
    if _is_it_search_direction(direction):
        params["search_field"] = "name"
    return params


def fetch_live_hh_vacancies(
    user_id: str,
    *,
    only_remote: bool = False,
    only_entry_level: bool = False,
    hh_experience: Optional[str] = None,
    min_salary: Optional[int] = None,
    strict_work_format: bool = False,
    page: int = 0,
    per_page: int = 15,
    city_override: Optional[str] = None,
    search_direction: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Поиск на hh.ru по профилю без отдельного шага «зафиксировать фильтр».
    city_override / search_direction — опциональные фильтры из UI миниаппа.
    """
    profile = load_profile(user_id)
    competencies = load_competencies(user_id)
    rec = run_recommendations(profile, competencies)
    sd = (search_direction or "").strip()
    if sd:
        rec = {**rec, "primary_direction": sd}
    city_raw = (city_override or "").strip() or (profile.get("city") or "")
    city = str(city_raw).strip() if city_raw else None
    area_id = suggest_area_id(str(city)) if city else None
    params = build_hh_query_params(profile, rec, area_id, competencies)

    if only_remote:
        params["schedule"] = "remote"
    elif strict_work_format:
        sch = _map_schedule(profile)
        if sch:
            params["schedule"] = sch

    apply_user_experience_filter(
        params, hh_experience=hh_experience, only_entry_level=only_entry_level
    )

    if min_salary is not None and min_salary > 0:
        params["salary"] = int(min_salary)
        params["only_with_salary"] = "true"

    params["page"] = max(0, page)
    params["per_page"] = min(50, max(5, per_page))

    raw = search_vacancies(params)
    items = slim_vacancy_items(raw)
    direction = str(rec.get("primary_direction") or "")
    if _is_it_search_direction(direction):
        items = [it for it in items if _IT_TITLE_PATTERN.search(it.get("name") or "")]
    return {
        "source": "hh.ru",
        "found": raw.get("found"),
        "pages": raw.get("pages"),
        "page": raw.get("page"),
        "per_page": raw.get("per_page"),
        "items": items,
        "search_hint": {
            "text": params.get("text"),
            "area_id": area_id,
            "city": city,
            "search_direction": rec.get("primary_direction"),
            "experience": params.get("experience"),
            "schedule": params.get("schedule"),
            "search_field": params.get("search_field"),
        },
    }


def build_filter_bundle(user_id: str) -> Dict[str, Any]:
    profile = load_profile(user_id)
    competencies = load_competencies(user_id)
    rec = run_recommendations(profile, competencies)

    city = profile.get("city")
    area_id = suggest_area_id(str(city)) if city else None
    query_params = build_hh_query_params(profile, rec, area_id, competencies)
    human = {
        "primary_direction": rec.get("primary_direction"),
        "skills_for_first_offer": rec.get("skills_for_first_offer"),
        "city": city,
        "hh_area_id": area_id,
        "experience": query_params.get("experience"),
        "employment": query_params.get("employment"),
        "schedule": query_params.get("schedule"),
        "salary_floor": query_params.get("salary"),
    }
    return {
        "user_id": user_id,
        "query_params": query_params,
        "human_readable": human,
        "built_at": datetime.now(timezone.utc).isoformat(),
    }


def save_user_hh_state(user_id: str, bundle: Dict[str, Any], tests_completed: bool = True):
    now = datetime.now(timezone.utc).isoformat()
    area = bundle.get("human_readable", {}).get("hh_area_id")
    with get_db() as conn:
        conn.execute(
            """INSERT INTO user_hh_state (user_id, tests_completed, tests_completed_at, hh_filter_json, hh_area_id, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 tests_completed = excluded.tests_completed,
                 tests_completed_at = excluded.tests_completed_at,
                 hh_filter_json = excluded.hh_filter_json,
                 hh_area_id = excluded.hh_area_id,
                 updated_at = excluded.updated_at""",
            (
                user_id,
                1 if tests_completed else 0,
                now if tests_completed else None,
                json.dumps(bundle, ensure_ascii=False),
                area,
                now,
            ),
        )
        conn.commit()


def load_user_hh_state(user_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM user_hh_state WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row:
            return None
        r = dict(row)
        if r.get("hh_filter_json"):
            try:
                r["filter"] = json.loads(r["hh_filter_json"])
            except json.JSONDecodeError:
                r["filter"] = None
        return r


def clear_user_hh_state(user_id: str) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM user_hh_state WHERE user_id = ?", (user_id,))
        conn.commit()


def regenerate_user_hh_bundle(user_id: str, *, force: bool = True) -> Tuple[bool, str, Dict[str, Any]]:
    """Сбросить сохранённый hh-фильтр и собрать заново из актуальной анкеты."""
    clear_user_hh_state(user_id)
    ok, msg, extra = can_finalize_hh_filter(user_id, force=force)
    if not ok:
        return False, msg, extra or {}
    bundle = build_filter_bundle(user_id)
    save_user_hh_state(user_id, bundle, tests_completed=True)
    out = dict(extra or {})
    out["bundle"] = bundle
    return True, "ok", out
