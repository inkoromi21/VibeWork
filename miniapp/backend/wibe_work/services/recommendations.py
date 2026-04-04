import re
from typing import Any, Dict, List, Set, Tuple

from wibe_work.services.user_context import (
    education_rank,
    merge_skills_from_profile,
    parse_interest_spheres,
)

_DIRECTION_KEYWORDS: List[Tuple[str, List[str]]] = [
    (
        "IT / разработка",
        [
            "код",
            "программ",
            "python",
            "java",
            "frontend",
            "backend",
            "devops",
            "данн",
            "машинн",
            "ai",
            "игр",
            "it",
        ],
    ),
    (
        "Аналитика и данные",
        ["аналит", "sql", "excel", "bi", "отчёт", "метрик", "данн"],
    ),
    (
        "Дизайн и креатив",
        ["дизайн", "ui", "ux", "figma", "иллюстр", "креатив", "моушн"],
    ),
    (
        "Маркетинг и продажи",
        ["маркет", "продаж", "smm", "таргет", "реклам", "клиент", "логист"],
    ),
    (
        "Управление и продукт",
        ["продукт", "project", "проект", "менедж", "руковод", "team"],
    ),
    (
        "Инженерия и производство",
        ["инженер", "станок", "производ", "чертеж", "cad", "электрон", "кабель"],
    ),
    (
        "Образование и наука",
        ["препод", "обучен", "наук", "исслед", "университет"],
    ),
    (
        "HR и подбор",
        ["hr", "рекрут", "персонал", "резюме", "соискател"],
    ),
    (
        "Юриспруденция",
        ["юрист", "право", "закон", "договор"],
    ),
]

_SPHERE_TO_DIRECTION = {
    "it": "IT / разработка",
    "айти": "IT / разработка",
    "маркетинг": "Маркетинг и продажи",
    "дизайн": "Дизайн и креатив",
    "продажи": "Маркетинг и продажи",
    "логистика": "Маркетинг и продажи",
    "медицина": "Универсальные роли",
    "образование": "Образование и наука",
    "творчество": "Дизайн и креатив",
    "спорт": "Универсальные роли",
}


def _tokenize(text: str) -> Set[str]:
    return {t for t in re.split(r"[^\wёЁа-яА-Яa-zA-Z]+", text.lower()) if len(t) > 2}


def _score_directions(text_blob: str) -> List[Dict[str, Any]]:
    tokens = _tokenize(text_blob)
    scored: List[Tuple[str, float]] = []
    for direction, kws in _DIRECTION_KEYWORDS:
        hits = sum(1 for kw in kws if kw in text_blob.lower() or any(kw in t for t in tokens))
        score = min(1.0, 0.15 * hits + 0.05 * len([k for k in kws if k in text_blob.lower()]))
        if hits:
            scored.append((direction, score))
    scored.sort(key=lambda x: -x[1])
    if not scored:
        return [
            {
                "direction": "Универсальные роли",
                "score": 0.4,
                "reason": "Добавьте интересы и предпочтения — пока слабые сигналы для узкой специализации.",
            }
        ]
    return [
        {
            "direction": d,
            "score": round(min(1.0, s), 2),
            "reason": "Совпадение с вашими интересами и описанием предпочтений.",
        }
        for d, s in scored[:5]
    ]


def _boost_from_spheres(spheres: List[str]) -> str:
    extra: List[str] = []
    for s in spheres:
        low = s.lower()
        for key, direction in _SPHERE_TO_DIRECTION.items():
            if key in low:
                extra.append(direction)
                break
        else:
            extra.append(s)
    return " ".join(extra)


def _skill_plan_for_direction(
    direction: str, user_skills_lower: Set[str]
) -> List[Dict[str, Any]]:
    plans: Dict[str, List[str]] = {
        "IT / разработка": [
            "Git",
            "Python или JavaScript",
            "Структуры данных и алгоритмы",
            "Тестирование",
            "Базы данных и SQL",
        ],
        "Аналитика и данные": ["SQL", "Excel / Google Sheets", "Статистика", "Визуализация", "A/B-тесты"],
        "Дизайн и креатив": ["Figma", "Композиция и типографика", "UI-паттерны", "Портфолио"],
        "Маркетинг и продажи": ["Копирайтинг", "Аналитика воронки", "CRM", "Переговоры"],
        "Управление и продукт": ["User stories", "Roadmap", "Приоритизация", "Stakeholder management"],
        "Инженерия и производство": ["Чтение чертежей", "CAD", "Охрана труда", "Контроль качества"],
        "Образование и наука": ["Методики обучения", "Презентации", "Научная грамотность"],
        "HR и подбор": ["Скрининг резюме", "Поиск кандидатов", "Коммуникация с кандидатами", "Excel / ATS"],
        "Юриспруденция": ["Трудовое право", "Договорная работа", "Исследование практики", "Документооборот"],
    }
    target_skills = plans.get(direction, ["Коммуникация", "Планирование", "Работа в команде"])
    out: List[Dict[str, Any]] = []
    for i, skill in enumerate(target_skills, start=1):
        have = skill.lower() in user_skills_lower or any(
            skill.lower() in u or u in skill.lower() for u in user_skills_lower
        )
        free_track = None
        if not have and i <= 3:
            free_track = "Бесплатно: документация инструмента, Stepik/YouTube по теме (методич. «нет денег на курсы»)."
        actions = (
            ["Закрепить в проекте или пет-проекте"]
            if not have
            else ["Углубить: менторство или production-задачи"]
        )
        if free_track:
            actions.append(free_track)
        out.append(
            {
                "priority": i,
                "skill": skill,
                "status": "есть база" if have else "к развитию",
                "suggested_actions": actions,
            }
        )
    return out


def _first_offer_skills(plan: List[Dict[str, Any]]) -> List[str]:
    need = [p["skill"] for p in plan if p.get("status") == "к развитию"]
    return need[:3]


def run_recommendations(
    profile: Dict[str, Any], competencies: List[Dict[str, Any]]
) -> Dict[str, Any]:
    spheres = parse_interest_spheres(profile)
    blob_parts = [
        str(profile.get("interests") or ""),
        str(profile.get("like_to_do") or ""),
        str(profile.get("software_skills") or ""),
        str(profile.get("programming_skills") or ""),
        _boost_from_spheres(spheres),
    ]
    blob = " ".join(blob_parts)
    inclinations = _score_directions(blob)
    top_direction = inclinations[0]["direction"]

    names, _ = merge_skills_from_profile(competencies, profile)
    user_lower = {n.lower() for n in names}

    edu_rank = education_rank(profile.get("education_level"))
    edu_note = None
    if edu_rank == 0:
        edu_note = "Укажите уровень образования в профиле — это влияет на отбор вакансий и формальные требования."
    elif edu_rank < 3:
        edu_note = "При выборе направлений учитывайте программы ДПО/бакалавриата для формальных требований работодателей."

    plan = _skill_plan_for_direction(top_direction, user_lower)

    return {
        "professional_inclinations": inclinations,
        "suitable_directions": inclinations[:3],
        "top_professions_preview": inclinations[:3],
        "skill_development_plan": plan,
        "skills_for_first_offer": _first_offer_skills(plan),
        "education_context_note": edu_note,
        "primary_direction": top_direction,
        "methodology_refs": [
            "Сферы интересов (до 5) — как в опроснике Google Sheets",
            "Топ-3 навыка для первого оффера — user story «нет опыта»",
        ],
    }
