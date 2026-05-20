"""Контекст анкеты для разбора и обучения: школа / СПО / вуз."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from wibe_work.questionnaire_fields import (
    AUDIENCE_CAREER,
    AUDIENCE_SCHOOL,
    SCHOOL_SUBJECT_OPTIONS,
    parse_favorite_subjects,
    questionnaire_audience,
)
from wibe_work.services.aptitude_quiz_grading import compute_quiz_grade, quiz_grade_label
from wibe_work.services.user_context import parse_interest_spheres

_SUBJECT_LABELS: Dict[str, str] = {s["id"]: s["label"] for s in SCHOOL_SUBJECT_OPTIONS}

_POST_SCHOOL_GOAL_RU: Dict[str, str] = {
    "after_9_college": "После 9 класса — в колледж (СПО)",
    "after_9_school": "После 9 класса — остаться в 10–11 классе",
    "after_11_university": "После 11 класса — в вуз",
    "after_11_college": "После 11 класса — в колледж (СПО)",
    "undecided": "Пока не решил(а)",
}

_EXAM_FOCUS_RU: Dict[str, str] = {
    "oge_9": "ОГЭ (9 класс)",
    "ege_11": "ЕГЭ (11 класс)",
    "both": "ОГЭ и ЕГЭ впереди",
    "profile_only": "Выбор профиля без экзаменов сейчас",
    "none": "Не готовлюсь к экзаменам сейчас",
}

_STUDY_FORM_RU: Dict[str, str] = {
    "fulltime": "очная",
    "parttime": "заочная",
    "evening": "вечерняя",
    "online": "онлайн",
}

_WORK_FORMAT_RU: Dict[str, str] = {
    "office": "офис",
    "remote": "удалённо",
    "hybrid": "гибрид",
    "any": "не важно",
}

_WORK_SCHEDULE_RU: Dict[str, str] = {
    "weekends": "только выходные",
    "after_classes": "после пар",
    "full_day": "полный день",
    "flex": "свободный график",
}

_PREP_RU: Dict[str, str] = {
    "weak": "слабая",
    "medium": "средняя",
    "strong": "сильная",
}

_EDUCATION_DETAIL_RU: Dict[str, str] = {
    "school_8_11": "школьник (8–11 кл.)",
    "spo": "студент СПО (колледж)",
    "univ_bachelor": "студент вуза (бакалавр)",
    "univ_master": "студент вуза (магистр)",
    "graduate": "выпускник",
}

# id любимого предмета → подпись в разрыве / обучении
SUBJECT_GAP_LABELS: Dict[str, str] = {
    "math": "Математика (алгебра, логика)",
    "russian": "Русский язык",
    "literature": "Литература",
    "physics": "Физика",
    "chemistry": "Химия",
    "biology": "Биология",
    "informatics": "Информатика / программирование",
    "history": "История",
    "social": "Обществознание",
    "geography": "География",
    "english": "Английский",
    "art": "Искусство / МХК",
    "other": "Другие предметы",
}

_CAREER_RESOURCE_BLOCK = re.compile(
    r"резюме|собеседован|отклик|hh\.ru|ваканс|трудоустройств|job-?сайт",
    re.I,
)


def analysis_mode_for_profile(profile: Dict[str, Any]) -> str:
    return "school" if compute_quiz_grade(profile) == "school" else "career"


def education_grade(profile: Dict[str, Any]) -> str:
    return compute_quiz_grade(profile or {})


def _label(map_: Dict[str, str], key: Any) -> str:
    k = str(key or "").strip().lower()
    return map_.get(k, str(key or "").strip())


def favorite_subjects_labels(profile: Dict[str, Any]) -> List[str]:
    return [_SUBJECT_LABELS.get(sid, sid) for sid in parse_favorite_subjects(profile)]


def school_questionnaire_lines(profile: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    fav = favorite_subjects_labels(profile)
    if fav:
        lines.append(f"Любимые предметы: {', '.join(fav)}")
    psg = (profile.get("post_school_goal") or "").strip()
    if psg:
        lines.append(f"План после школы: {_label(_POST_SCHOOL_GOAL_RU, psg)}")
    ef = (profile.get("exam_focus") or "").strip()
    if ef:
        lines.append(f"Подготовка к экзаменам: {_label(_EXAM_FOCUS_RU, ef)}")
    adm = (profile.get("admission_target") or "").strip()
    if adm:
        lines.append(f"Куда мечтает поступить: {adm[:200]}")
    hw = profile.get("hours_per_week")
    if hw is not None and str(hw).strip() != "":
        lines.append(f"Часов в неделю на подготовку: {hw}")
    weak = (profile.get("dislike_to_do") or "").strip()
    if weak:
        lines.append(f"Тяжелее даётся: {weak[:160]}")
    extra = (profile.get("extra_education") or "").strip()
    if extra:
        lines.append(f"Кружки / олимпиады: {extra[:200]}")
    return lines


def career_questionnaire_lines(profile: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    sf = (profile.get("study_form") or "").strip()
    if sf:
        lines.append(f"Форма обучения: {_label(_STUDY_FORM_RU, sf)}")
    wf = (profile.get("work_format_preference") or profile.get("work_format_pref") or "")
    if str(wf).strip():
        wfs = str(wf).strip()
        lines.append(f"Формат работы: {_label(_WORK_FORMAT_RU, wfs)}")
    ws = (profile.get("work_schedule") or "").strip()
    if ws:
        lines.append(f"График: {_label(_WORK_SCHEDULE_RU, ws)}")
    sal = profile.get("target_salary")
    if sal is not None and str(sal).strip() != "":
        lines.append(f"Целевая зарплата: {sal} ₽/мес")
    ir = (profile.get("internship_ready") or "").strip()
    if ir:
        lines.append(f"Стагировка: {ir}")
    cp = (profile.get("career_priority") or "").strip()
    if cp:
        lines.append(f"Приоритет: {cp}")
    return lines


def build_profile_summary_for_analysis(
    profile: Dict[str, Any],
    interest: str,
    preparation_level: str,
    *,
    profile_extra: Optional[Dict[str, Any]] = None,
) -> str:
    """Полный текст профиля для LLM, чата и персональных советов."""
    from wibe_work.services.user_context import coach_profile_snippet

    p = dict(profile or {})
    if profile_extra:
        for k, v in profile_extra.items():
            if v is not None and k not in p:
                p[k] = v

    grade = education_grade(p)
    aud = questionnaire_audience(profile=p)
    lines: List[str] = []

    base = coach_profile_snippet(p)
    if base:
        lines.append(base)

    edu = _label(_EDUCATION_DETAIL_RU, p.get("education_detail") or p.get("education_level"))
    spheres = parse_interest_spheres(p)
    sphere_txt = ", ".join(spheres) if spheres else (interest or "—")
    prep = _label(_PREP_RU, preparation_level) if preparation_level in _PREP_RU else preparation_level

    lines.append(
        f"Уровень для разбора: {quiz_grade_label(grade)} ({edu or '—'}). "
        f"Сфера теста/разбора: {interest or sphere_txt}. "
        f"Подготовка к цели: {prep}."
    )
    if aud == AUDIENCE_SCHOOL:
        lines.append(
            "Фокус разбора: куда учиться после школы, профильные предметы, ОГЭ/ЕГЭ — не вакансии."
        )
    elif grade == "vocational":
        lines.append(
            "Фокус разбора: специальность в СПО, практика, первые шаги в профессию по сфере."
        )
    else:
        lines.append(
            "Фокус разбора: роль и вакансии, навыки, стажировка/работа по выбранной сфере."
        )

    return "\n".join(lines)


def analysis_mode_note(analysis_mode: str, education_grade_val: str) -> str:
    if analysis_mode == "school":
        return (
            "Режим: ШКОЛЬНИК — варианты A/B/C это маршруты обучения (колледж, 11 класс, вуз), "
            "не профессии. Учитывай любимые предметы, план после 9/11 класса и ОГЭ/ЕГЭ из анкеты."
        )
    if education_grade_val == "vocational":
        return (
            "Режим: СПО / колледж — траектория по специальности, практика и первые шаги в профессию. "
            "Без школьных ОГЭ/ЕГЭ; учитывай формат работы, график и целевую зарплату из анкеты."
        )
    return (
        "Режим: вуз / выпускник — варианты A/B/C ближе к карьерным трекам, роль и выход на рынок труда. "
        "Учитывай формат работы, зарплату, стажировку из анкеты."
    )


def career_resource_blocked_for_school(resource: Dict[str, Any]) -> bool:
    title = str(resource.get("title") or "")
    desc = str(resource.get("description") or "")
    rid = str(resource.get("id") or "")
    blob = f"{title} {desc} {rid}"
    return bool(_CAREER_RESOURCE_BLOCK.search(blob))
