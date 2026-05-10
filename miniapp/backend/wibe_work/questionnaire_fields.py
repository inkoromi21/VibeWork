"""Схема динамической анкеты (зеркало структуры Google Sheet). Источник правды для GET /api/profile/schema."""

from typing import Any, Dict, List

# Направления (главная сфера) — enum для UI
INTEREST_SPHERES: List[Dict[str, str]] = [
    {"id": "it_dev", "label": "IT и разработка"},
    {"id": "data", "label": "Данные и аналитика"},
    {"id": "design", "label": "Дизайн и креатив"},
    {"id": "marketing", "label": "Маркетинг и коммуникации"},
    {"id": "sales", "label": "Продажи и работа с клиентами"},
    {"id": "mgmt", "label": "Менеджмент и проекты"},
    {"id": "engineering", "label": "Инженерия и техника"},
    {"id": "finance", "label": "Финансы и экономика"},
    {"id": "hr_edu", "label": "HR и обучение"},
    {"id": "other", "label": "Другое / в поиске"},
]


def get_profile_schema() -> Dict[str, Any]:
    """Секции с полями; колонка «зачем» в API не отдаётся — только label, placeholder, validation."""
    return {
        "version": 1,
        "interest_spheres": INTEREST_SPHERES,
        "sections": [
            {
                "id": "base",
                "title": "БАЗОВЫЕ ДАННЫЕ",
                "fields": [
                    {
                        "id": "age",
                        "type": "number",
                        "label": "Возраст",
                        "placeholder": "от 14 до 30",
                        "min": 14,
                        "max": 30,
                        "required": True,
                    },
                    {
                        "id": "main_sphere",
                        "type": "select",
                        "label": "Главная сфера интереса",
                        "required": True,
                        "options_from": "interest_spheres",
                    },
                    {
                        "id": "city",
                        "type": "text",
                        "label": "Город",
                        "placeholder": "Начните ввод — подсказки как во вкладке «Вакансии» (напр. кем → Кемерово)",
                        "required": False,
                    },
                    {
                        "id": "education_detail",
                        "type": "select",
                        "label": "Уровень образования",
                        "required": True,
                        "options": [
                            {"id": "school_9", "label": "Школа (9 классов)", "maps_education": "школа"},
                            {"id": "school_11", "label": "Школа (11 классов)", "maps_education": "школа"},
                            {"id": "college", "label": "Колледж / техникум", "maps_education": "колледж"},
                            {"id": "univ_bachelor", "label": "Вуз, бакалавриат", "maps_education": "вуз"},
                            {"id": "univ_master", "label": "Вуз, магистратура", "maps_education": "вуз"},
                            {"id": "univ_incomplete", "label": "Вуз незаконченный", "maps_education": "вуз"},
                        ],
                    },
                    {
                        "id": "education",
                        "type": "hidden",
                        "label": "",
                        "sync_from": "education_detail",
                        "maps": {
                            "school_9": "школа",
                            "school_11": "школа",
                            "college": "колледж",
                            "univ_bachelor": "вуз",
                            "univ_master": "вуз",
                            "univ_incomplete": "вуз",
                        },
                    },
                    {
                        "id": "preparation_level",
                        "type": "select",
                        "label": "Уровень подготовки к профессии",
                        "required": True,
                        "options": [
                            {"id": "weak", "label": "Слабый — только начинаю"},
                            {"id": "medium", "label": "Средний — есть база"},
                            {"id": "strong", "label": "Сильный — уверенно чувствую себя"},
                        ],
                    },
                    {
                        "id": "motivation_ai",
                        "type": "textarea",
                        "label": "Почему выбрали это направление",
                        "placeholder": "Коротко: что вас к этому привело (до 500 символов)",
                        "max_length": 500,
                        "required": False,
                    },
                ],
            },
            {
                "id": "desired_work_format",
                "title": "ФОРМАТ ЖЕЛАЕМОЙ РАБОТЫ",
                "fields": [
                    {
                        "id": "work_format_pref",
                        "type": "multiselect",
                        "label": "Формат работы",
                        "max_select": 3,
                        "options": [
                            {"id": "office", "label": "Офис"},
                            {"id": "remote", "label": "Удалённо"},
                            {"id": "hybrid", "label": "Гибрид"},
                        ],
                    },
                    {
                        "id": "hours_per_week",
                        "type": "number",
                        "label": "Часов в неделю на развитие",
                        "placeholder": "например, 10",
                        "min": 0,
                        "max": 60,
                    },
                ],
            },
            {
                "id": "priority_now",
                "title": "ПРИОРИТЕТ СЕЙЧАС",
                "fields": [
                    {
                        "id": "career_priority",
                        "type": "select",
                        "label": "Что сейчас важнее",
                        "required": False,
                        "options": [
                            {"id": "learning", "label": "Обучение и рост"},
                            {"id": "money", "label": "Деньги и стабильный доход"},
                            {"id": "balance", "label": "Баланс жизни и работы"},
                        ],
                    },
                ],
            },
            {
                "id": "skills_soft",
                "title": "НАВЫКИ И СОФТ-СКИЛЛЫ",
                "fields": [
                    {
                        "id": "languages",
                        "type": "text",
                        "label": "Языки",
                        "placeholder": "Русский, English — уровни",
                    },
                    {
                        "id": "soft_communication",
                        "type": "scale",
                        "label": "Коммуникация",
                        "scale_min": 1,
                        "scale_max": 5,
                    },
                    {
                        "id": "soft_teamwork",
                        "type": "scale",
                        "label": "Работа в команде",
                        "scale_min": 1,
                        "scale_max": 5,
                    },
                    {
                        "id": "soft_analytical",
                        "type": "scale",
                        "label": "Аналитическое мышление",
                        "scale_min": 1,
                        "scale_max": 5,
                    },
                ],
            },
            {
                "id": "experience",
                "title": "ОПЫТ",
                "fields": [
                    {
                        "id": "experience_projects",
                        "type": "textarea",
                        "label": "Проекты и инициативы",
                        "placeholder": "Учебные, личные, волонтёрство",
                    },
                    {
                        "id": "achievements",
                        "type": "textarea",
                        "label": "Достижения",
                        "placeholder": "Конкурсы, сертификаты, победы",
                    },
                    {
                        "id": "internship_ready",
                        "type": "select",
                        "label": "Готовность к стажировке",
                        "options": [
                            {"id": "yes", "label": "Да, в ближайшие 3 месяца"},
                            {"id": "later", "label": "Да, позже"},
                            {"id": "unsure", "label": "Пока не уверен(а)"},
                        ],
                    },
                ],
            },
        ],
    }
