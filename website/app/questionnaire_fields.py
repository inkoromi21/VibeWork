"""
Структура профиля по Google Sheets (лист «база»).
Таблица: https://docs.google.com/spreadsheets/d/17QUdFlBvJLPe1R92zEgUsod3_kNBP81ZjwDNea7o0u0/edit
При изменении таблицы можно править этот файл или подставить свой JSON через /api/profile/schema.
"""

from __future__ import annotations

from typing import Any

# Каждое поле: id, label, description (зачем), type, + опции по типу
PROFILE_SCHEMA: list[dict[str, Any]] = [
    {
        "id": "base",
        "title": "1. Базовые данные",
        "fields": [
            {
                "id": "city",
                "label": "Город",
                "description": "Поиск вакансий рядом с домом / возможность переезда",
                "type": "text",
                "placeholder": "Москва, Казань, Владивосток…",
            },
            {
                "id": "education_detail",
                "label": "Уровень образования",
                "description": "Стажировки и должности без опыта",
                "type": "select",
                "options": [
                    {"value": "school_8_11", "label": "Школьник (8–11 кл.)"},
                    {"value": "spo", "label": "Студент СПО"},
                    {"value": "uni_bachelor", "label": "Студент вуза (бакалавр)"},
                    {"value": "uni_master", "label": "Студент вуза (магистр)"},
                    {"value": "graduate", "label": "Выпускник"},
                ],
                "maps_to_education": {
                    "school_8_11": "школа",
                    "spo": "колледж",
                    "uni_bachelor": "вуз",
                    "uni_master": "вуз",
                    "graduate": "вуз",
                },
            },
            {
                "id": "course_grade",
                "label": "Курс / класс",
                "description": "Сколько времени до выхода на рынок",
                "type": "text",
                "placeholder": "10 класс, 2 курс…",
            },
            {
                "id": "study_form",
                "label": "Форма обучения",
                "description": "Влияет на доступное время для работы",
                "type": "select",
                "options": [
                    {"value": "fulltime", "label": "Очная"},
                    {"value": "parttime", "label": "Заочная"},
                    {"value": "evening", "label": "Вечерняя"},
                    {"value": "online", "label": "Онлайн"},
                ],
            },
        ],
    },
    {
        "id": "interests",
        "title": "2. Интересы и склонности",
        "fields": [
            {
                "id": "spheres",
                "label": "Сферы интересов (до 5)",
                "description": "Направление поиска профессий",
                "type": "multiselect",
                "max": 5,
                "options": [
                    {"value": "IT", "label": "IT"},
                    {"value": "маркетинг", "label": "Маркетинг"},
                    {"value": "дизайн", "label": "Дизайн"},
                    {"value": "продажи", "label": "Продажи"},
                    {"value": "логистика", "label": "Логистика"},
                    {"value": "медицина", "label": "Медицина"},
                    {"value": "образование", "label": "Образование"},
                    {"value": "рабочие_спец", "label": "Рабочие специальности"},
                    {"value": "творчество", "label": "Творчество"},
                    {"value": "спорт", "label": "Спорт"},
                    {"value": "другое", "label": "Другое"},
                ],
            },
            {
                "id": "likes",
                "label": "Чем нравится заниматься",
                "description": "Ключевые слова для подбора профессий",
                "type": "textarea",
                "placeholder": "Например: собирать ПК, рисовать, вести соцсети…",
            },
            {
                "id": "dislikes",
                "label": "Что не нравится делать",
                "description": "Фильтр неподходящих профессий",
                "type": "textarea",
                "placeholder": "Например: холодные звонки, сидеть без движения…",
            },
            {
                "id": "work_format_pref",
                "label": "Предпочитаемый формат работы",
                "type": "select",
                "options": [
                    {"value": "office", "label": "В офисе"},
                    {"value": "remote", "label": "Удалённо"},
                    {"value": "hybrid", "label": "Гибрид"},
                    {"value": "any", "label": "Не важно"},
                ],
            },
            {
                "id": "relocation",
                "label": "Готовность к переезду",
                "type": "select",
                "options": [
                    {"value": "yes", "label": "Да"},
                    {"value": "no", "label": "Нет"},
                    {"value": "big_cities", "label": "Только в крупные города"},
                ],
            },
            {
                "id": "work_schedule",
                "label": "График работы",
                "type": "select",
                "options": [
                    {"value": "weekends", "label": "Только выходные"},
                    {"value": "after_classes", "label": "После пар"},
                    {"value": "full_day", "label": "Полный день"},
                    {"value": "flex", "label": "Свободный график"},
                ],
            },
        ],
    },
    {
        "id": "hard_skills",
        "title": "3.1 Hard skills",
        "fields": [
            {
                "id": "programs",
                "label": "Владение программами",
                "description": "Excel, Figma, Python…",
                "type": "textarea",
                "placeholder": "Перечислите программы и уровень (1–5), если хотите",
            },
            {
                "id": "languages",
                "label": "Иностранные языки",
                "type": "textarea",
                "placeholder": "English B1, Deutsch A2…",
            },
            {
                "id": "coding",
                "label": "Навыки программирования",
                "type": "textarea",
                "placeholder": "HTML/CSS, Python…",
            },
            {
                "id": "social_media_skills",
                "label": "Работа с соцсетями",
                "type": "textarea",
                "placeholder": "Таргет, ведение каналов…",
            },
            {
                "id": "extra_courses",
                "label": "Дополнительное образование",
                "type": "textarea",
                "placeholder": "Курсы, школы…",
            },
        ],
    },
    {
        "id": "soft_skills",
        "title": "3.2 Soft skills (1–5)",
        "fields": [
            {"id": "soft_communication", "label": "Коммуникабельность", "type": "scale_1_5"},
            {"id": "soft_team", "label": "Работа в команде", "type": "scale_1_5"},
            {"id": "soft_org", "label": "Самоорганизация", "type": "scale_1_5"},
            {"id": "soft_stress", "label": "Стрессоустойчивость", "type": "scale_1_5"},
            {"id": "soft_creative", "label": "Креативность", "type": "scale_1_5"},
            {"id": "soft_analytics", "label": "Аналитическое мышление", "type": "scale_1_5"},
        ],
    },
    {
        "id": "experience",
        "title": "4. Опыт",
        "fields": [
            {"id": "exp_official", "label": "Официальный опыт работы", "type": "textarea", "placeholder": "Должность, срок…"},
            {"id": "exp_side", "label": "Подработки / фриланс", "type": "textarea"},
            {"id": "exp_volunteer", "label": "Волонтёрство", "type": "textarea"},
            {"id": "exp_projects", "label": "Личные проекты", "type": "textarea"},
            {"id": "exp_achievements", "label": "Достижения", "type": "textarea"},
        ],
    },
    {
        "id": "extra",
        "title": "5. Дополнительно",
        "fields": [
            {
                "id": "target_income",
                "label": "Целевой доход (₽/мес)",
                "type": "number",
                "placeholder": "30000",
            },
            {
                "id": "internship_ready",
                "label": "Готовность к стажировке",
                "type": "select",
                "options": [
                    {"value": "yes", "label": "Да"},
                    {"value": "no", "label": "Нет"},
                    {"value": "paid_only", "label": "Только оплачиваемая"},
                ],
            },
            {
                "id": "hours_week",
                "label": "Свободных часов в неделю",
                "type": "number",
                "placeholder": "10, 20, 40…",
            },
            {
                "id": "has_resume",
                "label": "Есть резюме / портфолио",
                "type": "select",
                "options": [
                    {"value": "yes", "label": "Да"},
                    {"value": "no", "label": "Нет"},
                ],
            },
            {"id": "referral", "label": "Откуда узнали о сервисе", "type": "text", "placeholder": "Telegram, университет…"},
        ],
    },
]


def get_profile_schema() -> list[dict[str, Any]]:
    return PROFILE_SCHEMA
