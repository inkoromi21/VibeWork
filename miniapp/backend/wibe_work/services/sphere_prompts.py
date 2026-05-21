"""Промпт-слои по сфере интереса: изоляция лексики и сценариев (медицина ≠ IT)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from wibe_work.services.assessment_routing import uses_job_search_assessment
from wibe_work.services.profile_analysis_context import (
    SUBJECT_GAP_LABELS,
    analysis_mode_for_profile,
    favorite_subjects_labels,
)
from wibe_work.services.user_context import parse_interest_spheres

# id сферы анкеты (main_sphere / interest_spheres)
SPHERE_LABELS_RU: Dict[str, str] = {
    "it_dev": "Разработка и IT",
    "data": "Аналитика и данные",
    "design": "Дизайн и UX/UI",
    "creative": "Креатив и медиа",
    "marketing": "Маркетинг и реклама",
    "sales": "Продажи",
    "mgmt": "Управление и менеджмент",
    "finance": "Финансы и учёт",
    "hr_edu": "HR и обучение персонала",
    "logistics": "Логистика и цепочки поставок",
    "medicine": "Медицина и здоровье",
    "education": "Педагогика и образование",
    "engineering": "Инженерия (не только IT)",
    "sport": "Спорт и физкультура",
    "other": "Общая профориентация",
}

# Сферы, где уместны вакансии, junior, hh, резюме под работу (взрослый карьерный режим)
_JOB_SEARCH_SPHERES = frozenset(
    {
        "it_dev",
        "data",
        "design",
        "creative",
        "marketing",
        "sales",
        "mgmt",
        "finance",
        "hr_edu",
        "logistics",
        "engineering",
    }
)

# Чужая лексика по сфере (запрещено вводить, если не в данных пользователя)
_FORBIDDEN_LEXICON: Dict[str, tuple[str, ...]] = {
    "medicine": (
        "junior",
        "джун",
        "middle",
        "сеньор",
        "backend",
        "бэкенд",
        "frontend",
        "devops",
        "python",
        "javascript",
        "git",
        "github",
        "figma",
        "pet-project",
        "pet project",
        "hh.ru",
        "отклик на ваканс",
        "разработчик",
        "программист",
    ),
    "education": (
        "junior",
        "джун",
        "backend",
        "devops",
        "figma",
        "отоларинголог",
        "хирург",
        "медсестра",
        "клиническ",
    ),
    "sport": (
        "junior",
        "джун",
        "backend",
        "figma",
        "отоларинголог",
        "медколледж",
        "бухгалтер",
    ),
    "it_dev": (
        "отоларинголог",
        "оториноларинголог",
        "медсестра",
        "фельдшер",
        "клиническая ординатура",
        "гистология",
        "физиотерапевт",
        "стоматолог",
        "педиатр",
    ),
    "data": (
        "отоларинголог",
        "медсестра",
        "стоматолог",
        "figma",
        "ux research",
    ),
    "design": (
        "отоларинголог",
        "медсестра",
        "fastapi",
        "django",
        "kubernetes",
        "sql injection",
    ),
    "marketing": (
        "отоларинголог",
        "медсестра",
        "хирург",
        "анатомия",
        "физиология",
    ),
    "sales": (
        "отоларинголог",
        "медсестра",
        "хирург",
        "figma",
        "react",
    ),
    "finance": (
        "отоларинголог",
        "медсестра",
        "figma",
        "react",
        "devops",
    ),
    "engineering": (
        "отоларинголог",
        "медсестра",
        "figma",
        "smm",
    ),
    "other": (
        "отоларинголог",
    ),
}

_SPHERE_BRIEF: Dict[str, str] = {
    "it_dev": (
        "Фокус: программирование, проекты, репозитории, стажировки/роль разработчика. "
        "Материалы — только IT (код, API, базы, алгоритмы). Не медицина, не педагогика."
    ),
    "data": (
        "Фокус: данные, SQL, аналитика, визуализация, метрики. "
        "Не чистый дизайн в Figma и не клиническая медицина."
    ),
    "design": (
        "Фокус: UX/UI, макеты, прототипы, портфолио дизайнера. "
        "Не backend-курсы и не медицинские программы."
    ),
    "medicine": (
        "Фокус: медицинское образование, биология/химия, практика в здравоохранении, "
        "поступление в медколледж/вуз, профильные предметы. "
        "Запрещено: IT-курсы, вакансии junior-разработчика, hh как главный шаг, Figma, Git."
    ),
    "education": (
        "Фокус: педагогика, предметная подготовка, практика в школе/вузе, портфолио педагога. "
        "Не IT-вакансии и не клинические роли."
    ),
    "sport": (
        "Фокус: спорт, тренерство, физподготовка, секции, учебные программы по физкультуре. "
        "Не офисная IT-карьера и не медицинские курсы для врачей."
    ),
    "marketing": (
        "Фокус: маркетинг, контент, реклама, аналитика кампаний, портфолио кейсов. "
        "Не медицина и не разработка ПО как основной путь."
    ),
    "sales": (
        "Фокус: продажи, переговоры, CRM, отраслевые знания. Не разработка и не клиника."
    ),
    "mgmt": (
        "Фокус: управление, проекты, команды, процессы. Не узкая медицина и не только код."
    ),
    "finance": (
        "Фокус: финансы, учёт, анализ, отчётность. Не IT-разработка и не клиника."
    ),
    "hr_edu": (
        "Фокус: HR, подбор, обучение сотрудников, коммуникации. Не разработка и не врач."
    ),
    "logistics": (
        "Фокус: логистика, склад, цепочки, процессы. Не дизайн и не медицина."
    ),
    "engineering": (
        "Фокус: инженерные специальности (механика, электроника, строительство — по данным). "
        "Не путать с «только программирование», если сфера не IT."
    ),
    "creative": (
        "Фокус: креатив, контент, медиа, монтаж, визуал. Не backend и не медицина."
    ),
    "other": (
        "Фокус: общая профориентация по данным теста. Не навязывай одну чужую сферу без оснований."
    ),
}

_ISOLATION_CORE = """ИЗОЛЯЦИЯ СФЕР (ОБЯЗАТЕЛЬНО)
- Главная сфера пользователя указана ниже. Все выводы, шаги, материалы и примеры — ТОЛЬКО для неё.
- Нельзя рекомендовать другой профессиональный мир как основной путь (медику — IT-курсы; IT — медколледж).
- Нельзя использовать профессиональный жаргон чужой сферы (см. «Запрещённая лексика»).
- Если в данных нет термина — не вводите его (не выдумывайте диагнозы, должности, технологии).
- Планы A/B/C — варианты внутри ЭТОЙ сферы или смежного выбора из разбора, не случайный микс."""

_SCHOOL_CORE = """РЕЖИМ ШКОЛЬНИК
- Варианты A/B/C — куда учиться (колледж, 11 класс, вуз), не штатные должности.
- Не вакансии junior, не массовые отклики на hh, не «карьера senior» — кроме осторожного совета про подработку.
- Любимые предметы из анкеты — главный ориентир для шагов и материалов."""


def primary_sphere_id(profile: Optional[Dict[str, Any]], interest: str = "") -> str:
    p = profile or {}
    spheres = parse_interest_spheres(p)
    if spheres:
        return str(spheres[0]).strip()
    ms = (p.get("main_sphere") or "").strip()
    if ms:
        return ms
    return (interest or "other").strip() or "other"


def sphere_allows_job_search(profile: Optional[Dict[str, Any]]) -> bool:
    if not profile:
        return False
    if not uses_job_search_assessment(profile):
        return False
    sid = primary_sphere_id(profile)
    return sid in _JOB_SEARCH_SPHERES


def build_sphere_prompt_layer(
    profile: Optional[Dict[str, Any]],
    *,
    interest: str = "",
    education_grade: str = "university",
    analysis_mode: str = "",
) -> str:
    """Текст для вставки в system/user промпты LLM."""
    sid = primary_sphere_id(profile, interest)
    label = SPHERE_LABELS_RU.get(sid, sid)
    brief = _SPHERE_BRIEF.get(sid, _SPHERE_BRIEF["other"])
    forbidden = _FORBIDDEN_LEXICON.get(sid, ())
    forb_line = ", ".join(forbidden[:18]) if forbidden else "—"

    lines = [
        _ISOLATION_CORE,
        "",
        f"=== СФЕРА ПОЛЬЗОВАТЕЛЯ: {label} (id: {sid}) ===",
        brief,
        f"Запрещённая лексика (не использовать): {forb_line}.",
    ]
    mode = (analysis_mode or "").strip().lower()
    if mode == "school" or education_grade == "school":
        lines.append(_SCHOOL_CORE)
        fav = favorite_subjects_labels(profile or {})
        if fav:
            lines.append(f"Любимые предметы (приоритет в советах): {', '.join(fav)}.")
    elif education_grade == "vocational":
        lines.append(
            "Режим СПО: специальность и практика по сфере; первые шаги в профессию — без чужой сферы."
        )
    else:
        if sphere_allows_job_search(profile):
            lines.append(
                "Режим карьеры: уместны стажировка, резюме, отклики — в рамках ЭТОЙ сферы, без чужих профессий."
            )
        else:
            lines.append(
                "Режим без поиска IT-вакансий: не предлагайте junior-разработчика, hh и типичный IT-найм как главный шаг."
            )

    return "\n".join(lines)


def school_subject_layer(profile: Dict[str, Any]) -> str:
    """Дополнение по школьным предметам."""
    ids = []
    from wibe_work.questionnaire_fields import parse_favorite_subjects

    for sid in parse_favorite_subjects(profile):
        lab = SUBJECT_GAP_LABELS.get(sid, sid)
        ids.append(lab)
    if not ids:
        return ""
    return (
        "ПРЕДМЕТЫ ШКОЛЬНИКА: советы и материалы привязывайте к "
        + ", ".join(ids)
        + ". Не подменяйте предмет другой сферой (информатика ≠ вся медицина; биология ≠ весь IT)."
    )
