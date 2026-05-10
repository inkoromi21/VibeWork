"""Грейд теста: школа / СПО / вуз — по образованию в анкете и при необходимости по возрасту."""

from typing import Any, Dict

from wibe_work.services.user_context import education_rank

_GRADE_LABELS = {
    "school": "Школьный уровень",
    "vocational": "СПО / колледж",
    "university": "Вуз / выпускник",
}

_GRADE_HINTS = {
    "school": "Формулировки для школьников: без «рынка труда» и офисного жаргона.",
    "vocational": "Учёт учебной практики, диплома и первых шагов по специальности.",
    "university": "Полная версия: карьера, резюме, старт на рынке труда.",
}

# id опции «Уровень образования» в анкете — приоритетнее education_level, если тот не синхронизирован
_EDUCATION_DETAIL_GRADE: Dict[str, str] = {
    "school_9": "school",
    "school_11": "school",
    "college": "vocational",
    "univ_bachelor": "university",
    "univ_master": "university",
    "univ_incomplete": "university",
}


def compute_quiz_grade(profile: Dict[str, Any]) -> str:
    """
    school — 9–11 класс, школьник в анкете.
    vocational — колледж, техникум, СПО.
    university — неполное высшее и выше.
    Если образование не указано — ориентир по возрасту (до 17 / до 21 / далее).
    """
    detail = profile.get("education_detail")
    if detail is not None and str(detail).strip():
        g = _EDUCATION_DETAIL_GRADE.get(str(detail).strip().lower())
        if g:
            return g

    raw = profile.get("education_level")
    rank = None
    if raw is not None and str(raw).strip():
        rank = education_rank(raw)

    age_val = profile.get("age")
    age = None
    if age_val is not None and str(age_val).strip() != "":
        try:
            age = int(age_val)
        except (TypeError, ValueError):
            age = None

    if rank is not None:
        if rank >= 3:
            return "university"
        if rank == 2:
            return "vocational"
        if rank == 1:
            return "school"
        # rank 0 — «не указано» / пусто в анкете; дальше возраст

    if age is not None:
        if age <= 17:
            return "school"
        if age <= 21:
            return "vocational"
        return "university"

    return "university"


def quiz_grade_label(grade: str) -> str:
    return _GRADE_LABELS.get(grade, grade)


def quiz_grade_hint(grade: str) -> str:
    return _GRADE_HINTS.get(grade, "")
