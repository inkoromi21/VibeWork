import json
import re
from typing import Any, Dict, List, Optional, Tuple

from wibe_work.sqlite_db import get_db

EDUCATION_RANK: Dict[str, int] = {
    "": 0,
    "не указано": 0,
    "основное": 0,
    # Сводное значение из анкеты (maps_education) — должно совпадать с рангом вуза / школы
    "школа": 1,
    "вуз": 3,
    "школьник": 1,
    "9 классов": 1,
    "среднее": 1,
    "11 классов": 1,
    "студент спо": 2,
    "среднее специальное": 2,
    "колледж": 2,
    "техникум": 2,
    "неполное высшее": 3,
    "студент вуза (бакалавр)": 3,
    "бакалавр": 4,
    "студент вуза (магистр)": 4,
    "специалист": 4,
    "магистр": 5,
    "выпускник": 4,
    "аспирантура": 6,
    "докторантура": 7,
}


def normalize_education(level: Optional[str]) -> str:
    if not level:
        return "не указано"
    return re.sub(r"\s+", " ", str(level).strip().lower())


def education_rank(level: Optional[str]) -> int:
    key = normalize_education(level)
    return EDUCATION_RANK.get(key, 2)


def load_profile(user_id: str) -> Dict[str, Any]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else {}


_PRIORITY_RU = {
    "learning": "обучение и рост",
    "money": "деньги и стабильный доход",
    "balance": "баланс жизни и работы",
}


_PAIN_LABELS: Dict[str, str] = {
    "pain_career": "Не знаю, кем стать",
    "pain_no_exp": "Нет опыта",
    "pain_region": "Мало вакансий в городе",
    "pain_money_courses": "Нет денег на курсы",
    "pain_interview": "Боюсь собеседований",
    "pain_overload": "Слишком много информации",
    "pain_low_confidence": "Кажется, что ничего не умею",
    "pain_gap_skills": "Умею многое, но работу не дают",
}

_WORK_FORMAT_RU = {
    "office": "офис",
    "remote": "удалённо",
    "hybrid": "гибрид",
    "any": "не важно",
}


def coach_profile_snippet(profile: Dict[str, Any]) -> str:
    """Краткий текст для ИИ-чата: поля анкеты."""
    if not profile:
        return ""
    lines: List[str] = []
    age = profile.get("age")
    if age is not None and str(age).strip() != "":
        lines.append(f"Возраст: {age}")
    city = (profile.get("city") or "").strip()
    if city:
        lines.append(f"Город: {city}")
    spheres = parse_interest_spheres(profile)
    if spheres:
        lines.append(f"Сферы интересов: {', '.join(spheres)}")
    elif (profile.get("main_sphere") or "").strip():
        lines.append(f"Главная сфера: {profile.get('main_sphere')}")
    cg = (profile.get("course_grade") or profile.get("course_or_grade") or "")
    if str(cg).strip():
        lines.append(f"Курс/класс: {cg}")
    edu = (profile.get("education_detail") or profile.get("education_level") or "").strip()
    if edu:
        lines.append(f"Образование: {edu}")
    like = (profile.get("like_to_do") or "").strip()
    if like:
        lines.append(f"Нравится: {like[:200]}")
    dislike = (profile.get("dislike_to_do") or "").strip()
    if dislike:
        lines.append(f"Не нравится: {dislike[:160]}")
    prep_prof = (profile.get("preparation_level") or "").strip()
    if prep_prof:
        lines.append(f"Подготовка: {prep_prof}")
    pr = (profile.get("career_priority") or "").strip().lower()
    if pr:
        lines.append(f"Приоритет сейчас: {_PRIORITY_RU.get(pr, pr)}")
    pain = (profile.get("primary_pain") or "").strip()
    if pain:
        lines.append(f"Главная сложность: {_PAIN_LABELS.get(pain, pain)}")
    from wibe_work.questionnaire_fields import (
        AUDIENCE_CAREER,
        AUDIENCE_SCHOOL,
        questionnaire_audience,
    )
    from wibe_work.services.profile_analysis_context import (
        career_questionnaire_lines,
        school_questionnaire_lines,
    )

    aud = questionnaire_audience(profile=profile)
    if aud == AUDIENCE_SCHOOL:
        lines.extend(school_questionnaire_lines(profile))
    else:
        lines.extend(career_questionnaire_lines(profile))
    return "\n".join(lines)


def load_competencies(user_id: str) -> List[Dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT name, level FROM user_competencies WHERE user_id = ? ORDER BY name",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def parse_skills_text(software_skills: Optional[str]) -> List[str]:
    if not software_skills:
        return []
    parts = re.split(r"[,;\n]+", str(software_skills))
    return [p.strip() for p in parts if p.strip()]


def profile_skill_blob(profile: Optional[Dict[str, Any]]) -> Optional[str]:
    if not profile:
        return None
    bits = [
        profile.get("software_skills"),
        profile.get("programming_skills"),
        profile.get("social_media_skills"),
    ]
    joined = ", ".join(str(b).strip() for b in bits if b and str(b).strip())
    return joined or None


def parse_interest_spheres(profile: Dict[str, Any]) -> List[str]:
    raw = profile.get("interest_spheres")
    if not raw:
        return []
    s = str(raw).strip()
    if not s:
        return []
    if s.startswith("["):
        try:
            data = json.loads(s)
            if isinstance(data, list):
                return [str(x).strip() for x in data if str(x).strip()]
        except (json.JSONDecodeError, TypeError):
            pass
    return [p.strip() for p in re.split(r"[,;\n]+", s) if p.strip()]


def merge_skill_sources(
    competencies: List[Dict[str, Any]], software_skills: Optional[str]
) -> Tuple[List[str], Dict[str, int]]:
    """Return display names (stable order) and map lowercase name -> level 1-5."""
    levels: Dict[str, int] = {}
    display_order: List[str] = []
    seen_lower: set = set()

    for c in competencies:
        name = (c.get("name") or "").strip()
        if not name:
            continue
        lv = int(c.get("level") or 3)
        lv = max(1, min(5, lv))
        key = name.lower()
        levels[key] = max(levels.get(key, 0), lv)
        if key not in seen_lower:
            seen_lower.add(key)
            display_order.append(name)

    for raw in parse_skills_text(software_skills):
        key = raw.lower()
        levels.setdefault(key, 3)
        if key not in seen_lower:
            seen_lower.add(key)
            display_order.append(raw.strip())

    return display_order, levels


def merge_skills_from_profile(
    competencies: List[Dict[str, Any]], profile: Dict[str, Any]
) -> Tuple[List[str], Dict[str, int]]:
    blob = profile_skill_blob(profile)
    return merge_skill_sources(competencies, blob)


def normalize_work_format_token(pref: Optional[str]) -> Optional[str]:
    if not pref:
        return None
    t = str(pref).lower()
    if "не важно" in t or "любой" in t:
        return None
    if "удал" in t:
        return "remote"
    if "гибрид" in t:
        return "hybrid"
    if "офис" in t:
        return "office"
    return None


def work_format_compatible(user_pref: Optional[str], job_format: Optional[str]) -> bool:
    j = (job_format or "any").lower().strip()
    if j in ("", "any", "не важно"):
        return True
    u = normalize_work_format_token(user_pref)
    if u is None:
        return True
    if j == u:
        return True
    if j == "hybrid" and u in ("remote", "office"):
        return True
    return False
