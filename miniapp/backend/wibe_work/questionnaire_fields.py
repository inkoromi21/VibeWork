"""Схема анкеты VibeWork (блоки из продуктовой таблицы + поля БД ProfileData)."""

from __future__ import annotations

from typing import Any, Dict, List

# Сферы для мультивыбора (до 5) — id совпадают с тестом и hh-подбором
# id сферы анкеты → значение Interest в веб-API (тест, разбор, вакансии)
SPHERE_TO_WEB_INTEREST: Dict[str, str] = {
    "it_dev": "IT",
    "marketing": "маркетинг",
    "design": "дизайн",
    "sales": "продажи",
    "logistics": "логистика",
    "medicine": "поддержка_и_сервис",
    "education": "HR_и_рекрутинг",
    "engineering": "инженерия",
    "creative": "дизайн",
    "sport": "бизнес",
    "data": "данные_и_AI",
    "mgmt": "бизнес",
    "finance": "финансы_и_контроль",
    "hr_edu": "HR_и_рекрутинг",
    "other": "IT",
}


def sphere_to_web_interest(sphere_id: str) -> str:
    return SPHERE_TO_WEB_INTEREST.get((sphere_id or "").strip(), "IT")


# Короткие подписи (одна строка в сетке) — сверху; длинные — внизу.
INTEREST_SPHERES: List[Dict[str, str]] = [
    {"id": "it_dev", "label": "IT"},
    {"id": "marketing", "label": "Маркетинг"},
    {"id": "design", "label": "Дизайн"},
    {"id": "sales", "label": "Продажи"},
    {"id": "logistics", "label": "Логистика"},
    {"id": "medicine", "label": "Медицина"},
    {"id": "education", "label": "Образование"},
    {"id": "creative", "label": "Творчество"},
    {"id": "sport", "label": "Спорт"},
    {"id": "finance", "label": "Финансы"},
    {"id": "hr_edu", "label": "HR и обучение"},
    {"id": "other", "label": "Другое"},
    {"id": "engineering", "label": "Рабочие специальности"},
    {"id": "data", "label": "Данные и аналитика"},
    {"id": "mgmt", "label": "Менеджмент и проекты"},
]

# Минимум для «анкета заполнена» (чип в шапке, тест, вакансии)
COMPLETION_REQUIRED: List[str] = [
    "age",
    "city",
    "education_detail",
    "course_grade",
    "study_form",
    "like_to_do",
    "work_format_preference",
    "work_schedule",
    "target_salary",
    "hours_per_week",
]

# Хотя бы одно: interest_spheres (JSON) или legacy main_sphere
COMPLETION_ANY_OF: List[List[str]] = [["interest_spheres", "main_sphere"]]


def normalize_profile_for_completion(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Свести legacy-поля к id из схемы v2 перед проверкой заполненности."""
    p = dict(profile or {})
    if not (p.get("course_grade") or "").strip() and p.get("course_or_grade") not in (None, ""):
        p["course_grade"] = str(p["course_or_grade"]).strip()
    if not (p.get("work_format_preference") or "").strip():
        wfp = p.get("work_format_pref")
        if isinstance(wfp, list) and wfp:
            p["work_format_preference"] = str(wfp[0]).strip()
        elif isinstance(wfp, str) and wfp.strip():
            part = wfp.split(",")[0].strip()
            if part:
                p["work_format_preference"] = part
    if not (p.get("education_detail") or "").strip():
        _edu_ru = {
            "школа": "school_8_11",
            "колледж": "spo",
            "вуз": "univ_bachelor",
        }
        for raw in (p.get("education_level"), p.get("education")):
            if raw is None or not str(raw).strip():
                continue
            key = str(raw).strip().lower()
            if key in _edu_ru:
                p["education_detail"] = _edu_ru[key]
                break
            if "_" in str(raw):
                p["education_detail"] = str(raw).strip()
                break
    if not (p.get("like_to_do") or "").strip() and (p.get("interests") or "").strip():
        p["like_to_do"] = str(p["interests"]).strip()
    return p


def _value_filled(value: Any) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, (int, float)):
        return not (isinstance(value, float) and value != value)
    if isinstance(value, str):
        return bool(value.strip())
    return True


def profile_field_filled(profile: Dict[str, Any], field_id: str) -> bool:
    from wibe_work.services.user_context import parse_interest_spheres

    if not profile:
        return False
    if field_id == "interest_spheres":
        return bool(parse_interest_spheres(profile) or (profile.get("main_sphere") or "").strip())
    if field_id == "course_grade":
        return _value_filled(profile.get("course_grade")) or _value_filled(profile.get("course_or_grade"))
    if field_id == "work_format_preference":
        return _value_filled(profile.get("work_format_preference")) or _value_filled(profile.get("work_format_pref"))
    if field_id == "education_detail":
        return _value_filled(profile.get("education_detail")) or _value_filled(profile.get("education_level"))
    if field_id == "like_to_do":
        return _value_filled(profile.get("like_to_do")) or _value_filled(profile.get("interests"))
    return _value_filled(profile.get(field_id))


def is_profile_complete(profile: Dict[str, Any]) -> bool:
    p = normalize_profile_for_completion(profile)
    for fid in COMPLETION_REQUIRED:
        if not profile_field_filled(p, fid):
            return False
    for group in COMPLETION_ANY_OF:
        if not any(profile_field_filled(p, fid) for fid in group):
            return False
    return True


def get_profile_schema() -> Dict[str, Any]:
    sphere_opts = [{"id": s["id"], "label": s["label"]} for s in INTEREST_SPHERES]

    return {
        "version": 2,
        "wizard": True,
        "interest_spheres": INTEREST_SPHERES,
        "sphere_to_web_interest": dict(SPHERE_TO_WEB_INTEREST),
        "completion": {
            "required": list(COMPLETION_REQUIRED),
            "any_of": list(COMPLETION_ANY_OF),
        },
        "sections": [
            {
                "id": "base",
                "theme": "Личные данные",
                "title": "Базовые данные",
                "fields": [
                    {
                        "id": "age",
                        "type": "number",
                        "label": "Возраст",
                        "placeholder": "17",
                        "min": 14,
                        "max": 30,
                        "required": True,
                    },
                    {
                        "id": "city",
                        "type": "text",
                        "label": "Город",
                        "placeholder": "Москва, Казань…",
                        "required": True,
                    },
                    {
                        "id": "education_detail",
                        "type": "select",
                        "label": "Уровень образования",
                        "required": True,
                        "options": [
                            {
                                "id": "school_8_11",
                                "label": "Школьник (8–11 кл.)",
                                "maps_education": "школа",
                            },
                            {"id": "spo", "label": "Студент СПО", "maps_education": "колледж"},
                            {
                                "id": "univ_bachelor",
                                "label": "Студент вуза (бакалавр)",
                                "maps_education": "вуз",
                            },
                            {
                                "id": "univ_master",
                                "label": "Студент вуза (магистр)",
                                "maps_education": "вуз",
                            },
                            {"id": "graduate", "label": "Выпускник", "maps_education": "вуз"},
                        ],
                    },
                    {
                        "id": "course_grade",
                        "type": "text",
                        "label": "Курс / класс",
                        "placeholder": "10 класс, 2 курс…",
                        "required": True,
                    },
                    {
                        "id": "study_form",
                        "type": "select",
                        "label": "Форма обучения",
                        "required": True,
                        "options": [
                            {"id": "fulltime", "label": "Очная"},
                            {"id": "parttime", "label": "Заочная"},
                            {"id": "evening", "label": "Вечерняя"},
                            {"id": "online", "label": "Онлайн"},
                        ],
                    },
                    {
                        "id": "education_level",
                        "type": "hidden",
                        "label": "",
                        "sync_from": "education_detail",
                    },
                ],
            },
            {
                "id": "pain",
                "theme": "Ваша ситуация",
                "title": "Что сейчас больше всего мешает?",
                "optional": True,
                "fields": [
                    {
                        "id": "primary_pain",
                        "type": "radio",
                        "label": "",
                        "required": False,
                        "options": [
                            {"id": "pain_career", "label": "Не знаю, кем стать"},
                            {"id": "pain_no_exp", "label": "Нет опыта — не возьмут"},
                            {"id": "pain_region", "label": "Мало вакансий в моём городе"},
                            {"id": "pain_money_courses", "label": "Нет денег на курсы"},
                            {"id": "pain_interview", "label": "Боюсь собеседований"},
                            {"id": "pain_overload", "label": "Слишком много информации"},
                            {"id": "pain_low_confidence", "label": "Кажется, что ничего не умею"},
                            {"id": "pain_gap_skills", "label": "Умею многое, но работу не дают"},
                        ],
                    },
                ],
            },
            {
                "id": "interests",
                "theme": "Предпочтения",
                "title": "Интересы и склонности",
                "fields": [
                    {
                        "id": "interest_spheres",
                        "type": "multiselect",
                        "label": "Сферы интересов (до 5)",
                        "max_select": 5,
                        "required": True,
                        "options": sphere_opts,
                    },
                    {
                        "id": "like_to_do",
                        "type": "textarea",
                        "label": "Чем нравится заниматься",
                        "placeholder": "Собирать ПК, рисовать, вести соцсети, помогать людям…",
                        "required": True,
                    },
                    {
                        "id": "dislike_to_do",
                        "type": "textarea",
                        "label": "Что не нравится делать",
                        "placeholder": "Холодные звонки, сидеть без движения, считать цифры…",
                    },
                    {
                        "id": "work_format_preference",
                        "type": "select",
                        "label": "Предпочитаемый формат работы",
                        "required": True,
                        "options": [
                            {"id": "office", "label": "В офисе"},
                            {"id": "remote", "label": "Удалённо"},
                            {"id": "hybrid", "label": "Гибрид"},
                            {"id": "any", "label": "Не важно"},
                        ],
                    },
                    {
                        "id": "relocation_ready",
                        "type": "select",
                        "label": "Готовность к переезду",
                        "options": [
                            {"id": "yes", "label": "Да"},
                            {"id": "no", "label": "Нет"},
                            {"id": "big_cities", "label": "Только в крупные города"},
                        ],
                    },
                    {
                        "id": "work_schedule",
                        "type": "select",
                        "label": "График работы",
                        "required": True,
                        "options": [
                            {"id": "weekends", "label": "Только выходные"},
                            {"id": "after_classes", "label": "После пар"},
                            {"id": "full_day", "label": "Полный день"},
                            {"id": "flex", "label": "Свободный график"},
                        ],
                    },
                ],
            },
            {
                "id": "skills_hard",
                "theme": "Навыки",
                "title": "Навыки (профессиональные)",
                "optional": True,
                "fields": [
                    {
                        "id": "software_skills",
                        "type": "textarea",
                        "label": "Программы и инструменты",
                        "placeholder": "Excel, Figma, Python, Canva — и уровень 1–5 при желании",
                    },
                    {
                        "id": "languages",
                        "type": "text",
                        "label": "Иностранные языки",
                        "placeholder": "English B1, Deutsch A2…",
                    },
                    {
                        "id": "programming_skills",
                        "type": "textarea",
                        "label": "Программирование",
                        "placeholder": "HTML/CSS, Python…",
                    },
                    {
                        "id": "social_media_skills",
                        "type": "textarea",
                        "label": "Соцсети и digital",
                        "placeholder": "Telegram-канал, таргет, SMM…",
                    },
                    {
                        "id": "extra_education",
                        "type": "textarea",
                        "label": "Дополнительное обучение",
                        "placeholder": "Курсы, школы, олимпиады…",
                    },
                ],
            },
            {
                "id": "skills_soft",
                "theme": "Личные качества",
                "title": "Личные качества (1–5)",
                "optional": True,
                "fields": [
                    {
                        "id": "soft_communication",
                        "type": "scale",
                        "label": "Коммуникабельность",
                        "scale_min": 1,
                        "scale_max": 5,
                        "default": 3,
                    },
                    {
                        "id": "soft_teamwork",
                        "type": "scale",
                        "label": "Работа в команде",
                        "scale_min": 1,
                        "scale_max": 5,
                        "default": 3,
                    },
                    {
                        "id": "soft_organization",
                        "type": "scale",
                        "label": "Самоорганизация",
                        "scale_min": 1,
                        "scale_max": 5,
                        "default": 3,
                    },
                    {
                        "id": "soft_stress",
                        "type": "scale",
                        "label": "Стрессоустойчивость",
                        "scale_min": 1,
                        "scale_max": 5,
                        "default": 3,
                    },
                    {
                        "id": "soft_creativity",
                        "type": "scale",
                        "label": "Креативность",
                        "scale_min": 1,
                        "scale_max": 5,
                        "default": 3,
                    },
                    {
                        "id": "soft_analytical",
                        "type": "scale",
                        "label": "Аналитическое мышление",
                        "scale_min": 1,
                        "scale_max": 5,
                        "default": 3,
                    },
                ],
            },
            {
                "id": "experience",
                "theme": "Опыт",
                "title": "Опыт",
                "optional": True,
                "fields": [
                    {
                        "id": "experience_official",
                        "type": "textarea",
                        "label": "Официальная работа",
                        "placeholder": "Должность, срок…",
                    },
                    {
                        "id": "experience_side",
                        "type": "textarea",
                        "label": "Подработки / фриланс",
                        "placeholder": "Курьер, Kwork…",
                    },
                    {
                        "id": "experience_volunteer",
                        "type": "textarea",
                        "label": "Волонтёрство",
                    },
                    {
                        "id": "experience_projects",
                        "type": "textarea",
                        "label": "Личные проекты",
                        "placeholder": "Канал, сайт, хакатон…",
                    },
                    {
                        "id": "achievements",
                        "type": "textarea",
                        "label": "Достижения",
                        "placeholder": "Олимпиады, сертификаты…",
                    },
                ],
            },
            {
                "id": "goals",
                "theme": "Цели",
                "title": "Цели и работа",
                "fields": [
                    {
                        "id": "target_salary",
                        "type": "number",
                        "label": "Целевой доход (₽/мес)",
                        "placeholder": "30000",
                        "min": 0,
                        "max": 500000,
                        "required": True,
                    },
                    {
                        "id": "internship_ready",
                        "type": "select",
                        "label": "Готовность к стажировке",
                        "options": [
                            {"id": "yes", "label": "Да"},
                            {"id": "no", "label": "Нет"},
                            {"id": "paid_only", "label": "Только оплачиваемая"},
                        ],
                    },
                    {
                        "id": "hours_per_week",
                        "type": "number",
                        "label": "Свободных часов в неделю на работу/учёбу",
                        "placeholder": "10, 20, 40",
                        "min": 0,
                        "max": 80,
                        "required": True,
                    },
                    {
                        "id": "has_resume_portfolio",
                        "type": "select",
                        "label": "Есть резюме / портфолио",
                        "options": [
                            {"id": "yes", "label": "Да"},
                            {"id": "no", "label": "Нет"},
                        ],
                    },
                    {
                        "id": "career_priority",
                        "type": "select",
                        "label": "Что сейчас важнее",
                        "options": [
                            {"id": "learning", "label": "Обучение и рост"},
                            {"id": "money", "label": "Деньги и стабильный доход"},
                            {"id": "balance", "label": "Баланс жизни и работы"},
                        ],
                    },
                    {
                        "id": "acquisition_source",
                        "type": "text",
                        "label": "Откуда узнали о VibeWork",
                        "placeholder": "Telegram, университет, друзья…",
                    },
                ],
            },
            {
                "id": "extra",
                "theme": "Дополнительно",
                "title": "Дополнительно",
                "optional": True,
                "fields": [
                    {
                        "id": "preparation_level",
                        "type": "select",
                        "label": "Уровень подготовки к профессии",
                        "options": [
                            {"id": "weak", "label": "Слабый — только начинаю"},
                            {"id": "medium", "label": "Средний — есть база"},
                            {"id": "strong", "label": "Сильный — уверенно"},
                        ],
                    },
                    {
                        "id": "motivation_ai",
                        "type": "textarea",
                        "label": "Почему выбрали это направление",
                        "placeholder": "Коротко, до 500 символов",
                        "max_length": 500,
                    },
                ],
            },
        ],
    }
