"""Исключение из теста вопросов, уже закрытых анкетой (по полю или смыслу)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Pattern, Tuple

from wibe_work.questionnaire_fields import profile_field_filled
from wibe_work.services.aptitude_quiz_grading import compute_quiz_grade

WRow = List[tuple]

# Поле анкеты → regex по тексту вопроса (если поле заполнено — вопрос не показываем)
_OVERLAP_BY_FIELD: Dict[str, List[Tuple[str, Tuple[str, ...]]]] = {
    "work_format_preference": [
        (r"формат работ", ("university", "vocational")),
        (r"гибкий график и свобода формата", ("university", "vocational")),
        (r"стабильный офис с понятными правилами", ("university", "vocational")),
    ],
    "preparation_level": [
        (r"приблизит вас к желаемой должности", ("university",)),
        (r"уровень позиции", ("university",)),
    ],
    "post_school_goal": [
        (r"после 9 или 11 класса", ("school",)),
        (r"принять решение \(профиль, колледж, вуз\)", ("school",)),
    ],
    "target_salary": [
        (r"зарплата, график и условия", ("university", "vocational")),
    ],
    "work_schedule": [
        (r"график работ", ("university", "vocational")),
    ],
    "internship_ready": [
        (r"первую работу или стажировку", ("university",)),
    ],
}

# Целиком модуль профориентации, если в анкете уже есть любимые предметы
_SKIP_MODULES_WHEN_FILLED: Dict[str, str] = {
    "favorite_subjects": "profil",
}

# Маркеры «чужого» уровня в тексте вопроса
_LEVEL_FORBIDDEN: Dict[str, List[Pattern[str]]] = {
    "school": [
        re.compile(p, re.I)
        for p in (
            r"ваканс",
            r"должност",
            r"job-?сайт",
            r"резюме",
            r"собеседован",
            r"зарплат",
            r"стажировк.*специальност",
        )
    ],
    "vocational": [
        re.compile(p, re.I)
        for p in (
            r"одноклассник",
            r"после 9 или 11",
            r"огэ",
            r"егэ",
            r"классн",
        )
    ],
    "university": [
        re.compile(p, re.I)
        for p in (
            r"одноклассник",
            r"после 9 или 11",
            r"огэ",
            r"классн",
            r"школьн",
        )
    ],
}


def _grade(profile: Dict[str, Any]) -> str:
    return compute_quiz_grade(profile or {})


def _compiled_rules() -> List[Tuple[str, Pattern[str], Tuple[str, ...]]]:
    out: List[Tuple[str, Pattern[str], Tuple[str, ...]]] = []
    for field, rows in _OVERLAP_BY_FIELD.items():
        for pattern, grades in rows:
            out.append((field, re.compile(pattern, re.I), grades))
    return out


_RULES = _compiled_rules()


def question_overlaps_filled_profile_field(
    question: Dict[str, Any],
    profile: Dict[str, Any],
    *,
    grade: Optional[str] = None,
    module_id: str = "",
) -> Optional[str]:
    """Вернуть id поля анкеты, из‑за которого вопрос скрыт, или None."""
    g = grade or _grade(profile)
    text = str(question.get("text") or "")

    skip_mod = (question.get("skip_if_profile_field") or "").strip()
    if skip_mod and profile_field_filled(profile, skip_mod):
        return skip_mod

    for field, mod in _SKIP_MODULES_WHEN_FILLED.items():
        if module_id == mod and profile_field_filled(profile, field):
            return field

    for field, pattern, grades in _RULES:
        if g not in grades:
            continue
        if not profile_field_filled(profile, field):
            continue
        if pattern.search(text):
            return field
    return None


def should_skip_question(
    question: Dict[str, Any],
    profile: Dict[str, Any],
    *,
    grade: Optional[str] = None,
    module_id: str = "",
) -> bool:
    return question_overlaps_filled_profile_field(
        question, profile, grade=grade, module_id=module_id
    ) is not None


def filter_question_list(
    profile: Dict[str, Any],
    questions: List[Dict[str, Any]],
    weights: List[WRow],
    *,
    module_id: str = "",
) -> tuple[List[Dict[str, Any]], List[WRow]]:
    if len(questions) != len(weights):
        return questions, weights
    g = _grade(profile)
    out_q: List[Dict[str, Any]] = []
    out_w: List[WRow] = []
    for q, w in zip(questions, weights):
        if should_skip_question(q, profile, grade=g, module_id=module_id):
            continue
        cleaned = dict(q)
        cleaned.pop("skip_if_profile_field", None)
        out_q.append(cleaned)
        out_w.append(w)
    return out_q, out_w


def question_matches_level(question: Dict[str, Any], grade: str) -> bool:
    text = str(question.get("text") or "")
    for pat in _LEVEL_FORBIDDEN.get(grade, []):
        if pat.search(text):
            return False
    aud = question.get("audience")
    if aud == "school" and grade != "school":
        return False
    if aud == "adult" and grade == "school":
        return False
    return True


def question_matches_interest_meta(question: Dict[str, Any], interest: str) -> bool:
    """Проверка only_interests / skip_interests на отформатированном вопросе."""
    key = (interest or "").strip() or "other"
    only = question.get("only_interests")
    if only and key not in only:
        return False
    skip = question.get("skip_interests") or ()
    if key in skip:
        return False
    return True
