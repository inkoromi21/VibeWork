"""Маршрутизация профориентационных модулей по образованию и классу/курсу."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

from wibe_work.services.aptitude_quiz_grading import compute_quiz_grade
from wibe_work.services.user_context import education_rank

# Подтреки (детализация внутри school / vocational / university)
TRACK_SCHOOL_EARLY = "school_early"  # 8–9 кл.
TRACK_SCHOOL_GRADE9 = "school_grade9"
TRACK_SCHOOL_SENIOR = "school_senior"  # 10–11
TRACK_VOCATIONAL_EARLY = "vocational_early"
TRACK_VOCATIONAL = "vocational"
TRACK_UNIVERSITY = "university"
TRACK_UNIVERSITY_SENIOR = "university_senior"

TRACK_LABELS: Dict[str, str] = {
    TRACK_SCHOOL_EARLY: "Школа: 8–9 класс",
    TRACK_SCHOOL_GRADE9: "Школа: 9 класс (выбор после 9)",
    TRACK_SCHOOL_SENIOR: "Школа: 10–11 класс",
    TRACK_VOCATIONAL_EARLY: "СПО: 1–2 курс",
    TRACK_VOCATIONAL: "СПО / колледж",
    TRACK_UNIVERSITY: "Бакалавр и выше: роль и вакансии",
    TRACK_UNIVERSITY_SENIOR: "Выпускник / магистр: выход на работу",
}

TRACK_HINTS: Dict[str, str] = {
    TRACK_SCHOOL_EARLY: "Короткий блок про интересы к предметам и скрытые мотивы — без взрослых профессий.",
    TRACK_SCHOOL_GRADE9: "Учтён выбор после 9 класса: интересы, тип деятельности и готовность к решению.",
    TRACK_SCHOOL_SENIOR: "Полный школьный набор: деятельность, среда работы и мотивы перед выпуском.",
    TRACK_VOCATIONAL_EARLY: "Практика, ценности и среда — первые курсы колледжа.",
    TRACK_VOCATIONAL: "Сочетание практики, мотивов и типа рабочей среды под вашу специальность.",
    TRACK_UNIVERSITY: "",
    TRACK_UNIVERSITY_SENIOR: "Акцент на конкретную вакансию: уровень позиции, резюме, отклики и первые шаги.",
}

# Модули по треку: profil, klimov, jovaisa, holland, readiness (пусто = без блока профориентации)
TRACK_MODULES: Dict[str, Tuple[str, ...]] = {
    TRACK_SCHOOL_EARLY: ("profil", "jovaisa"),
    TRACK_SCHOOL_GRADE9: ("profil", "klimov", "readiness"),
    TRACK_SCHOOL_SENIOR: ("klimov", "holland", "jovaisa"),
    TRACK_VOCATIONAL_EARLY: ("jovaisa", "klimov", "holland"),
    TRACK_VOCATIONAL: ("klimov", "jovaisa", "holland"),
    TRACK_UNIVERSITY: (),
    TRACK_UNIVERSITY_SENIOR: (),
}

_MODULE_TITLES: Dict[str, str] = {
    "profil": "Интересы к учёбе",
    "klimov": "Что вам ближе по делу",
    "jovaisa": "Мотивы и ценности",
    "holland": "Тип рабочей среды",
    "readiness": "Готовность к выбору",
}

_RE_SCHOOL_CLASS = re.compile(
    r"(?:^|\s)(?:[сc]?\s*)?(8|9|10|11)\s*(?:класс|кл\.?|class)(?:\s|$)",
    re.IGNORECASE,
)
_RE_SCHOOL_CLASS_SHORT = re.compile(r"^\s*(8|9|10|11)\s*$")
_RE_COURSE = re.compile(
    r"(?:^|\s)(?:[сc]?\s*)?(\d)\s*(?:курс|к\.?)(?:\s|$)|(?:^|\s)(?:[сc]?\s*)?(\d)\s*(?:год|г\.?)(?:\s|$)",
    re.IGNORECASE,
)
_RE_MASTER = re.compile(r"магистр|master", re.IGNORECASE)
_RE_GRADUATE = re.compile(r"выпуск|graduate|оконч", re.IGNORECASE)


def module_title(module_id: str) -> str:
    return _MODULE_TITLES.get(module_id, module_id)


def parse_course_grade(text: Any) -> Dict[str, Optional[int]]:
    """Извлечь номер класса (8–11) или курса (1–6) из свободного текста."""
    raw = str(text or "").strip().lower()
    out: Dict[str, Optional[int]] = {"school_class": None, "course_year": None}
    if not raw:
        return out
    m = _RE_SCHOOL_CLASS.search(raw) or _RE_SCHOOL_CLASS_SHORT.match(raw)
    if m:
        out["school_class"] = int(m.group(1))
        return out
    if _RE_MASTER.search(raw):
        out["course_year"] = 5
        return out
    if _RE_GRADUATE.search(raw) and "школ" not in raw:
        out["course_year"] = 6
        return out
    cm = _RE_COURSE.search(raw)
    if cm:
        yr = cm.group(1) or cm.group(2)
        if yr:
            out["course_year"] = int(yr)
    return out


def resolve_assessment_track(profile: Dict[str, Any]) -> str:
    """
    school_early | school_grade9 | school_senior |
    vocational_early | vocational |
    university | university_senior
    """
    detail = str(profile.get("education_detail") or "").strip().lower()
    parsed = parse_course_grade(profile.get("course_grade"))
    school_class = parsed.get("school_class")
    course_year = parsed.get("course_year")
    grade = compute_quiz_grade(profile)

    if detail == "graduate" or _RE_GRADUATE.search(str(profile.get("course_grade") or "")):
        return TRACK_UNIVERSITY_SENIOR

    if grade == "school" or detail in ("school_8_11", "school_9", "school_11"):
        if school_class == 8:
            return TRACK_SCHOOL_EARLY
        if school_class == 9:
            return TRACK_SCHOOL_GRADE9
        if school_class in (10, 11):
            return TRACK_SCHOOL_SENIOR
        # эвристика по возрасту
        age = _profile_age(profile)
        if age is not None:
            if age <= 15:
                return TRACK_SCHOOL_EARLY
            if age == 15:
                return TRACK_SCHOOL_GRADE9
        return TRACK_SCHOOL_SENIOR

    if grade == "vocational" or detail in ("spo", "college"):
        if course_year is not None and course_year <= 2:
            return TRACK_VOCATIONAL_EARLY
        return TRACK_VOCATIONAL

    if detail in ("univ_master",):
        return TRACK_UNIVERSITY_SENIOR
    if course_year is not None and course_year >= 4:
        return TRACK_UNIVERSITY_SENIOR
    if course_year is not None and course_year >= 3:
        return TRACK_UNIVERSITY_SENIOR
    return TRACK_UNIVERSITY


def _profile_age(profile: Dict[str, Any]) -> Optional[int]:
    try:
        a = profile.get("age")
        if a is None or str(a).strip() == "":
            return None
        return int(a)
    except (TypeError, ValueError):
        return None


def track_modules(track_id: str) -> Tuple[str, ...]:
    return TRACK_MODULES.get(track_id, TRACK_MODULES[TRACK_UNIVERSITY])


def uses_job_search_assessment(profile: Dict[str, Any]) -> bool:
    """Бакалавр и выше: сфера задана, нужен поиск роли/должности, не профориентация."""
    return compute_quiz_grade(profile) == "university"


def career_block_title(profile: Dict[str, Any]) -> str:
    if uses_job_search_assessment(profile):
        return "Роль, должность и выход на работу"
    return "Карьера и мотивы"


def track_meta(profile: Dict[str, Any]) -> Dict[str, Any]:
    track = resolve_assessment_track(profile)
    grade = compute_quiz_grade(profile)
    parsed = parse_course_grade(profile.get("course_grade"))
    return {
        "track_id": track,
        "track_label": TRACK_LABELS.get(track, track),
        "track_hint": TRACK_HINTS.get(track, ""),
        "test_grade": grade,
        "school_class": parsed.get("school_class"),
        "course_year": parsed.get("course_year"),
        "module_ids": list(track_modules(track)),
    }
