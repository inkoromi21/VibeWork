"""Логика рекомендаций, матчинг вакансий, симулятор, чат через LLM (OpenAI-совместимый API)."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Literal

import httpx

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_MINIAPP_BACKEND = _REPO_ROOT / "miniapp" / "backend"
if _MINIAPP_BACKEND.is_dir() and str(_MINIAPP_BACKEND) not in sys.path:
    sys.path.insert(0, str(_MINIAPP_BACKEND))

try:
    from wibe_work.services.llm_prompts import (
        ANALYSIS_NARRATIVE_SYSTEM,
        CAREER_COACH_CHAT_SYSTEM,
        DEFAULT_GENERIC_SYSTEM,
        build_chat_user_instruction_suffix,
    )
except ImportError:
    CAREER_COACH_CHAT_SYSTEM = (
        "Ты карьерный консультант для молодёжи в России. Только русский язык. "
        "Не работодатель. Опирайся на контекст разбора. 6–12 предложений. Без HTML."
    )
    DEFAULT_GENERIC_SYSTEM = CAREER_COACH_CHAT_SYSTEM
    ANALYSIS_NARRATIVE_SYSTEM = (
        "Ты готовишь текст разбора по данным профиля. Только русский. Не противоречь переданным фактам."
    )

    def build_chat_user_instruction_suffix() -> str:
        return ""

from app.mts_tracks_catalog import load_mts_tracks
from app.api_schemas import (
    AiPipelineStep,
    AnalysisResult,
    CareerDirection,
    CareerStage,
    ChatRequest,
    DiagnosisPayload,
    Education,
    EmployerFeedbackHint,
    GapAnalysis,
    GapSkillBar,
    GradePlanRow,
    InsightTile,
    Interest,
    JobMatchRequest,
    LearningResource,
    MockVacancy,
    MtsMatrixMatch,
    MtsPreviewPayload,
    PERSONALITY_TEST_QUESTION_COUNT,
    PreparationBranch,
    StyleFitBar,
    TEST_QUESTION_COUNT,
    SimulatorAdvance,
    SimulatorChoice,
    SimulatorState,
    SimulatorStep,
    SkillKey,
    SkillPlanPhase,
    VacancyEnriched,
    VacancyMatchRow,
    WeekPlanItem,
    WorkFormat,
)
from app.profession_packs import format_grade_plan_rows, resolve_profession_pack
from app.aptitude_quiz_content import pick_personality_quiz_questions, pick_quiz_questions

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 45.0


def get_llm_settings() -> tuple[str, str, str] | None:
    """
    Настройки для реальной нейросети: URL chat/completions, API-ключ, model id.
    Любой провайдер с OpenAI-совместимым POST /v1/chat/completions (DeepSeek, OpenAI, Groq, …).

    Переменные (достаточно ключа и при необходимости URL/модели):
    - CHAT_API_KEY — общий ключ (приоритет)
    - CHAT_API_URL — полный URL, например https://api.deepseek.com/v1/chat/completions
    - CHAT_MODEL — например deepseek-chat, gpt-4o-mini

    Совместимость: DEEPSEEK_API_KEY / DEEPSEEK_API_URL / DEEPSEEK_MODEL, OPENAI_API_KEY / OPENAI_MODEL.
    Для локального совместимого сервера: CHAT_API_URL=http://127.0.0.1:…/v1/chat/completions, CHAT_API_KEY можно не задавать.
    """
    chat_key = os.getenv("CHAT_API_KEY", "").strip()
    ds_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    oa_key = os.getenv("OPENAI_API_KEY", "").strip()
    key = chat_key or ds_key or oa_key

    url = (
        os.getenv("CHAT_API_URL", "").strip()
        or os.getenv("DEEPSEEK_API_URL", "").strip()
    )
    if not url:
        if oa_key and not ds_key:
            url = "https://api.openai.com/v1/chat/completions"
        else:
            url = "https://api.deepseek.com/v1/chat/completions"

    local = "127.0.0.1" in url or "localhost" in url

    model = (
        os.getenv("CHAT_MODEL", "").strip()
        or os.getenv("DEEPSEEK_MODEL", "").strip()
        or os.getenv("OPENAI_MODEL", "").strip()
    )
    if not model:
        if "api.openai.com" in url:
            model = "gpt-4o-mini"
        elif local:
            model = "llama3.2"
        else:
            model = "deepseek-chat"

    if local:
        # Локальный URL не требует облачного ключа; Bearer только если задан CHAT_API_KEY
        key = chat_key

    if not key and not local:
        return None
    return (url, key, model)


def llm_configured() -> bool:
    return get_llm_settings() is not None

# Пул карьерных треков по направлению профиля (из них по склонностям теста выбираются три разных плана A/B/C).
DIRECTION_POOLS: dict[Interest, tuple[str, ...]] = {
    Interest.IT: (
        "Веб- и бэкенд-разработка",
        "Мобильные приложения",
        "Автотесты и качество ПО",
        "Внутренние сервисы и интеграции",
        "Системная аналитика в IT",
        "Поддержка и сопровождение продуктов",
    ),
    Interest.DATA_AI: (
        "Продуктовая и бизнес-аналитика",
        "Инженерия данных и витрины",
        "ML и рекомендательные системы",
        "Эксперименты и A/B-тесты",
        "MLOps и мониторинг моделей",
        "Качество данных и глоссарии",
    ),
    Interest.DEVOPS: (
        "CI/CD и релизы",
        "Облачная инфраструктура",
        "Наблюдаемость и инциденты",
        "Безопасность и доступы",
        "Контейнеры и оркестрация",
        "Платформенные сервисы для разработчиков",
    ),
    Interest.DESIGN: (
        "UI/UX продуктовых команд",
        "Графика и бренд-коммуникации",
        "Дизайн-системы и компоненты",
        "Исследования и юзабилити",
        "Моушн и презентационные форматы",
        "Прототипирование под разработку",
    ),
    Interest.MARKETING: (
        "Performance и платный трафик",
        "Контент и SMM",
        "CRM и удержание",
        "Продуктовый маркетинг",
        "Бренд и PR",
        "Аналитика маркетинга",
    ),
    Interest.SALES: (
        "B2B-продажи и пресейл",
        "Работа с ключевыми клиентами",
        "Холодные каналы и воронка",
        "Партнёрские программы",
        "Розница и точки контакта",
        "Сопровождение сделок и документы",
    ),
    Interest.ENGINEERING: (
        "Проектирование и CAD",
        "Энергетика и автоматизация",
        "Телеком и линейные объекты",
        "Производство и технологии",
        "Робототехника и мехатроника",
        "Технический надзор и ПНР",
    ),
    Interest.SCIENCE: (
        "Лабораторные исследования",
        "Био/хим анализ",
        "Научная коммуникация",
        "Документирование протоколов",
        "Статистика и воспроизводимость",
        "Полевые и измерительные работы",
    ),
    Interest.BUSINESS: (
        "Операции и процессы",
        "Стратегические проекты",
        "Предпринимательство и запуск",
        "Корпоративное развитие",
        "Риски и комплаенс (вводный уровень)",
        "Кросс-функциональная координация",
    ),
    Interest.FINANCE: (
        "Финансовый контроль и отчётность",
        "Бюджетирование и прогнозы",
        "Казначейство и платежи",
        "Управленческий учёт",
        "Налоги и закрытие периода",
        "Финансовая аналитика",
    ),
    Interest.HR: (
        "Рекрутмент и подбор",
        "Обучение и развитие",
        "HR-бренд и коммуникации",
        "Кадровое администрирование",
        "HR-аналитика",
        "Корпоративная культура",
    ),
    Interest.LEGAL: (
        "Трудовое право и кадры",
        "Договорная работа",
        "Корпоративное право",
        "Закупки и тендерное право",
        "Персональные данные и ИБ",
        "Судебная и претензионная работа",
    ),
    Interest.PROCUREMENT: (
        "Операционные закупки",
        "Категорийный менеджмент",
        "Контракты и сроки поставок",
        "Работа с поставщиками",
        "Тендеры и конкурентные процедуры",
        "Аналитика закупок",
    ),
    Interest.LOGISTICS: (
        "Склад и запасы",
        "Доставка и маршруты",
        "Импорт/экспорт и таможня",
        "Планирование спроса",
        "WMS и учёт",
        "Сервисная логистика",
    ),
    Interest.REAL_ESTATE: (
        "Эксплуатация зданий и активов",
        "Аренда и договоры",
        "Технический учёт",
        "Проекты модернизации",
        "Закупки для недвижимости",
        "Клиентский сервис по объектам",
    ),
    Interest.ADMIN: (
        "Офис-менеджмент",
        "Документооборот и архив",
        "Календари и протоколы",
        "Хозяйственное обеспечение",
        "Поддержка руководства",
        "Внутренние коммуникации",
    ),
    Interest.PRODUCT: (
        "Product management",
        "Дорожные карты и бэклог",
        "Метрики продукта",
        "Координация разработки и дизайна",
        "Исследования и инсайты",
        "Go-to-market",
    ),
    Interest.SUPPORT: (
        "Техподдержка пользователей",
        "L1/L2 обращения",
        "База знаний и скрипты",
        "Качество сервиса",
        "Онбординг клиентов",
        "Обратная связь в продукт",
    ),
}

ADJACENT_BY_DOMINANT: dict[str, tuple[str, ...]] = {
    "people": (
        "Клиентский успех и сопровождение",
        "Внутренние коммуникации и обучение",
        "Координация стейкхолдеров",
        "Переговоры и медиация",
    ),
    "analytical": (
        "Метрики и отчётность",
        "Процессная аналитика",
        "Финансовые модели (вводный уровень)",
        "Контроль качества данных",
    ),
    "creative": (
        "Контент и сторителлинг",
        "Визуальные концепции",
        "Продуктовые гипотезы",
        "Исследования пользователей",
    ),
}

TEST_WEIGHTS: dict[str, dict[str, int]] = {
    "A": {"analytical": 2, "creative": 0, "people": 1},
    "B": {"analytical": 0, "creative": 2, "people": 0},
    "C": {"analytical": 1, "creative": 0, "people": 2},
    "D": {"analytical": 2, "creative": 1, "people": 0},
}

SKILL_KEYWORDS: dict[SkillKey, tuple[str, ...]] = {
    SkillKey.PROGRAMMING: ("python", "java", "git", "docker", "go", "sql", "excel", "backend", "фронт", "код"),
    SkillKey.ANALYTICS: ("sql", "excel", "метрик", "аналит", "данн", "моделир", "процесс"),
    SkillKey.COMMUNICATION: ("коммуникац", "презентац", "smm", "копирайт", "веден", "диалог", "переговор"),
    SkillKey.DESIGN: ("figma", "дизайн", "ux", "ui", "визуал", "макет", "граф"),
    SkillKey.MANAGEMENT: ("agile", "проект", "документ", "организ", "команд"),
}

INTEREST_TO_MTS_TAG: dict[Interest, str] = {
    Interest.IT: "IT",
    Interest.DATA_AI: "IT",
    Interest.DEVOPS: "IT",
    Interest.DESIGN: "маркетинг",
    Interest.MARKETING: "маркетинг",
    Interest.SALES: "маркетинг",
    Interest.SUPPORT: "маркетинг",
    Interest.PRODUCT: "маркетинг",
    Interest.ENGINEERING: "инженерия",
    Interest.SCIENCE: "инженерия",
    Interest.LOGISTICS: "инженерия",
    Interest.BUSINESS: "бизнес",
    Interest.FINANCE: "бизнес",
    Interest.HR: "бизнес",
    Interest.LEGAL: "бизнес",
    Interest.PROCUREMENT: "бизнес",
    Interest.REAL_ESTATE: "бизнес",
    Interest.ADMIN: "бизнес",
}


def _people_heavy_title(title: str) -> bool:
    t = title.lower()
    return any(
        k in t
        for k in (
            " hr",
            "hr ",
            "продаж",
            "клиент",
            "корпоратив",
            "продавец",
            "маркетинг",
            "рекрут",
        )
    )


def _tech_track_title(title: str) -> bool:
    t = title.lower()
    return any(
        k in t
        for k in (
            " ai",
            "ai ",
            "ии ",
            "инженер",
            "кабель",
            "телеком",
            "сопровождении рабочих",
            "microsoft",
            "windows server",
            "закуп",
        )
    )


def rank_mts_tracks(
    primary_interest: Interest,
    skills: list[SkillKey],
    test_answers: list[Any] | None,
    target_mts_role_id: str | None = None,
    personality_test_answers: list[Any] | None = None,
) -> list[MtsMatrixMatch]:
    """Ранжирование 13 ролей МТС по интересу, навыкам и (если есть полный тест) ответам."""
    tracks = load_mts_tracks()
    if not tracks:
        return []

    user_tag = INTEREST_TO_MTS_TAG.get(primary_interest, "бизнес")
    test_scores = _test_scores_from_optional(test_answers, personality_test_answers)
    dominant: str | None = None
    if test_scores:
        dominant = max(test_scores, key=lambda k: test_scores[k])

    out: list[MtsMatrixMatch] = []
    for tr in tracks:
        sc = 22.0
        reasons: list[str] = []

        if tr.profession_tag == user_tag:
            sc += 38
            reasons.append("сфера совпадает с выбранным интересом")
        elif primary_interest == Interest.DESIGN and tr.profession_tag == "маркетинг":
            sc += 16
            reasons.append("при интересе «дизайн» усилены клиентские роли матрицы")

        blob = " ".join(tr.requirements + tr.duties).lower()
        skill_hits = 0
        for sk in skills:
            for kw in SKILL_KEYWORDS[sk]:
                if kw in blob:
                    skill_hits += 1
                    break
        if skill_hits:
            sc += min(36, skill_hits * 10)
            reasons.append(f"ваши навыки пересекаются с описанием ({skill_hits} направлений)")

        if target_mts_role_id and tr.id == target_mts_role_id:
            sc += 26
            reasons.append("целевая роль выбрана в профиле (матрица МТС)")

        if dominant == "analytical":
            if tr.profession_tag in ("IT", "инженерия"):
                sc += 14
                reasons.append("тест: аналитика → сильнее технологические роли")
            if "ai" in tr.title.lower() or "аналитик" in tr.title.lower():
                sc += 10
                reasons.append("тест: аналитика → ближе к ролям с анализом и цифрой")
            if _people_heavy_title(tr.title) and tr.profession_tag not in ("IT", "инженерия"):
                sc -= 5
                reasons.append("при сильной аналитике «людские» роли ниже в приоритете")
        elif dominant == "creative":
            if tr.profession_tag == "маркетинг" or "маркетинг" == tr.title.lower():
                sc += 14
                reasons.append("тест: креатив → маркетинг и развитие")
        elif dominant == "people":
            if _people_heavy_title(tr.title):
                sc += 18
                reasons.append("тест: коммуникации → HR, продажи, работа с клиентами")
            if _tech_track_title(tr.title) and not _people_heavy_title(tr.title):
                sc += 2

        rel = int(max(0, min(100, round(sc))))
        reason_str = "; ".join(reasons) if reasons else "базовая привязка к матрице компетенций"
        out.append(
            MtsMatrixMatch(
                id=tr.id,
                title=tr.title,
                profession_tag=tr.profession_tag,
                relevance=rel,
                reason=reason_str,
                requirements=list(tr.requirements),
                duties=list(tr.duties),
            )
        )

    out.sort(key=lambda m: m.relevance, reverse=True)
    return out


def mts_preview_rank(payload: MtsPreviewPayload) -> list[MtsMatrixMatch]:
    ta = payload.test_answers if len(payload.test_answers) == TEST_QUESTION_COUNT else None
    pt = (
        payload.personality_test_answers
        if len(payload.personality_test_answers) == PERSONALITY_TEST_QUESTION_COUNT
        else None
    )
    return rank_mts_tracks(
        payload.interests[0],
        payload.skills,
        ta,
        target_mts_role_id=payload.target_mts_role_id,
        personality_test_answers=pt,
    )


def quiz_questions_bundle(form_interest: str, target_mts_role_id: str | None) -> dict[str, Any]:
    qs, key = pick_quiz_questions(form_interest, target_mts_role_id)
    return {
        "quiz_key": key,
        "questions": qs,
        "personality_questions": pick_personality_quiz_questions(),
    }


def build_preparation_branch(payload: DiagnosisPayload) -> PreparationBranch:
    level = payload.preparation_level
    intr = payload.interests[0].value
    if level == "слабый":
        return PreparationBranch(
            level="слабый",
            headline="Ветка «база»: сначала опора и дисциплина",
            next_route="2–3 месяца: вводные курсы и еженедельный артефакт; затем стажировка или учебный заказ.",
            checklist=[
                "Один завершённый мини-проект в портфолио",
                "Фиксация прогресса раз в неделю",
                f"Вводный трек по области «{intr}» (не меньше 15 ч)",
            ],
        )
    if level == "сильный":
        return PreparationBranch(
            level="сильный",
            headline="Ветка «углубление»: кейсы и нетворк",
            next_route="Фокус на коммерческих доказательствах: хакатон, практика, open-source или летняя стажировка.",
            checklist=[
                "Метрика результата по одному живому кейсу",
                "Ревью от практика (код, дизайн или кейс)",
                "Не меньше двух контактов в индустрии в месяц",
            ],
        )
    return PreparationBranch(
        level="средний",
        headline="Ветка «рост»: баланс обучения и практики",
        next_route="Параллельно курс и проект с дедлайном; через 6–8 недель — отклики на стажировки.",
        checklist=[
            "20 ч/нед на ключевой навык",
            "Один проект с README и демо",
            "Резюме под выбранный трек",
        ],
    )


def build_employer_feedback_hint(top_direction: str) -> EmployerFeedbackHint:
    return EmployerFeedbackHint(
        headline="Фокус работодателя (до собеседования)",
        body=(
            f"Для направления вроде «{top_direction}» обычно смотрят портфолио, ясность мотивации и совпадение с требованиями вакансии. "
            "У кандидатов 16–22 ценят инициативу и готовность учиться."
        ),
        suggestion="Проверьте вкладку «Работа» с персональным матчингом и симулятор решений.",
    )


AI_PIPELINE_STEPS: tuple[AiPipelineStep, ...] = (
    AiPipelineStep(idx=1, label="Разрыв навыков", target_id="res-gap"),
    AiPipelineStep(idx=2, label="Маршрут", target_id="res-dirs"),
    AiPipelineStep(idx=3, label="Стили", target_id="res-style-fit"),
    AiPipelineStep(idx=4, label="Спринт", target_id="res-weekly"),
    AiPipelineStep(idx=5, label="Трекинг", target_id="res-stages"),
)


def _first_steps_for_level(plan_code: str, level: str, interest: Interest) -> list[str]:
    pack = resolve_profession_pack(interest)
    if level == "слабый":
        return [s.format(plan_code=plan_code) for s in pack.first_weak]
    if level == "сильный":
        return [s.format(plan_code=plan_code) for s in pack.first_strong]
    return [s.format(plan_code=plan_code) for s in pack.first_med]


MOCK_VACANCIES: list[MockVacancy] = [
    MockVacancy(
        id="v1",
        title="Junior Python-разработчик",
        company="TechStart",
        requirements=["Python", "SQL", "Git", "английский B1"],
        profession_tag="IT",
        level="джуниор",
        salary_hint="от 80 000 ₽",
        city="Москва",
        work_format=WorkFormat.HYBRID,
        salary_min_rub=80_000,
    ),
    MockVacancy(
        id="v2",
        title="Стажёр UI/UX",
        company="Design Lab",
        requirements=["Figma", "портфолио", "основы исследований"],
        profession_tag="дизайн",
        level="стажер",
        salary_hint="40 000 – 55 000 ₽",
        city="Санкт-Петербург",
        work_format=WorkFormat.REMOTE,
        salary_min_rub=45_000,
    ),
    MockVacancy(
        id="v3",
        title="Маркетолог (контент)",
        company="Grow Agency",
        requirements=["копирайт", "метрики", "SMM"],
        profession_tag="маркетинг",
        level="джуниор",
        salary_hint="70 000 – 95 000 ₽",
        city="Казань",
        work_format=WorkFormat.OFFICE,
        salary_min_rub=70_000,
    ),
    MockVacancy(
        id="v4",
        title="Инженер-проектировщик (CAD)",
        company="PromTech",
        requirements=["AutoCAD/SolidWorks", "чтение чертежей"],
        profession_tag="инженерия",
        level="мидл",
        salary_hint="от 120 000 ₽",
        city="Екатеринбург",
        work_format=WorkFormat.OFFICE,
        salary_min_rub=120_000,
    ),
    MockVacancy(
        id="v5",
        title="Лаборант / ассистент исследователя",
        company="BioResearch",
        requirements=["химия/биология", "аккуратность, документирование"],
        profession_tag="наука",
        level="стажер",
        city="Новосибирск",
        work_format=WorkFormat.HYBRID,
        salary_min_rub=35_000,
    ),
    MockVacancy(
        id="v6",
        title="Аналитик данных (junior)",
        company="DataWorks",
        requirements=["SQL", "Excel/Python", "визуализация"],
        profession_tag="IT",
        level="джуниор",
        salary_hint="от 90 000 ₽",
        city="Москва",
        work_format=WorkFormat.REMOTE,
        salary_min_rub=90_000,
    ),
    MockVacancy(
        id="v7",
        title="Product designer",
        company="AppCraft",
        requirements=["Figma", "дизайн-системы", "работа с продуктом"],
        profession_tag="дизайн",
        level="мидл",
        salary_hint="от 150 000 ₽",
        city="Москва",
        work_format=WorkFormat.HYBRID,
        salary_min_rub=150_000,
    ),
    MockVacancy(
        id="v8",
        title="Менеджер проектов (assistant)",
        company="ConsultPro",
        requirements=["коммуникации", "документация", "базовый agile"],
        profession_tag="бизнес",
        level="стажер",
        city="Санкт-Петербург",
        work_format=WorkFormat.HYBRID,
        salary_min_rub=55_000,
    ),
    MockVacancy(
        id="v9",
        title="Backend developer (middle)",
        company="CloudNine",
        requirements=["Python/Go", "микросервисы", "Docker"],
        profession_tag="IT",
        level="мидл",
        salary_hint="от 200 000 ₽",
        city="Удалённо",
        work_format=WorkFormat.REMOTE,
        salary_min_rub=200_000,
    ),
    MockVacancy(
        id="v10",
        title="Бизнес-аналитик",
        company="FinCore",
        requirements=["моделирование процессов", "SQL", "презентации"],
        profession_tag="бизнес",
        level="джуниор",
        salary_hint="от 95 000 ₽",
        city="Москва",
        work_format=WorkFormat.OFFICE,
        salary_min_rub=95_000,
    ),
]

SIMULATOR_BRANCHES: dict[str, list[dict[str, Any]]] = {
    "analyst": [
        {
            "title": "Утро аналитика",
            "narrative": "В 9:00 вам срочно прислали выгрузку: продажи упали на 12%. Нужно к обеду дать гипотезы.",
            "choices": [
                {"id": "a1", "label": "Сначала построю дашборд и сегментацию", "delta": 15},
                {"id": "a2", "label": "Сразу напишу в чат отдела продаж", "delta": 8},
                {"id": "a3", "label": "Попрошу ещё данные и отложу ответ", "delta": 4},
            ],
        },
        {
            "title": "Встреча с заказчиком",
            "narrative": "Заказчик просит «сделать красиво», но ТЗ размыто. Что делаете?",
            "choices": [
                {"id": "a4", "label": "Зафиксирую цели и метрики письмом", "delta": 12},
                {"id": "a5", "label": "Сделаю быстрый макет отчёта", "delta": 6},
                {"id": "a6", "label": "Откажусь без уточнений", "delta": -5},
            ],
        },
        {
            "title": "Финал дня",
            "narrative": "Директор хочет одну слайд-деку для совета директоров.",
            "choices": [
                {"id": "a7", "label": "3 слайда: проблема — данные — рекомендации", "delta": 18},
                {"id": "a8", "label": "30 страниц подробностей", "delta": -8},
            ],
        },
    ],
    "designer": [
        {
            "title": "День дизайнера",
            "narrative": "Продукт просит «ещё одну иконку», но без гайдлайна. Ваш шаг?",
            "choices": [
                {"id": "d1", "label": "Предложу минимальный паттерн в Figma", "delta": 14},
                {"id": "d2", "label": "Нарисую в изоляции, как нравится", "delta": 2},
                {"id": "d3", "label": "Откажусь без UX-исследования", "delta": 5},
            ],
        },
        {
            "title": "Ревью",
            "narrative": "Стейкхолдер говорит: «не цепляет». Что отвечаете?",
            "choices": [
                {"id": "d4", "label": "Задам вопросы про критерии успеха", "delta": 12},
                {"id": "d5", "label": "Переделаю всё ночью без вопросов", "delta": -6},
            ],
        },
    ],
}


def _score_test(answers: list[Any]) -> dict[str, int]:
    totals = {"analytical": 0, "creative": 0, "people": 0}
    for a in answers:
        w = TEST_WEIGHTS.get(a.choice, TEST_WEIGHTS["A"])
        for k, v in w.items():
            totals[k] += v
    return totals


def _test_scores_from_optional(
    test_answers: list[Any] | None,
    personality_test_answers: list[Any] | None,
) -> dict[str, int] | None:
    """Скоринг по тесту 1; если есть полный тест 2 — суммируем веса (общий профиль личности)."""
    if not test_answers or len(test_answers) != TEST_QUESTION_COUNT:
        return None
    s1 = _score_test(test_answers)
    if personality_test_answers and len(personality_test_answers) == PERSONALITY_TEST_QUESTION_COUNT:
        s2 = _score_test(personality_test_answers)
        return {k: s1[k] + s2[k] for k in s1}
    return s1


def _combined_ts(payload: DiagnosisPayload) -> dict[str, int]:
    sc = _test_scores_from_optional(payload.test_answers, payload.personality_test_answers)
    return sc if sc is not None else {"analytical": 1, "creative": 1, "people": 1}


def _behavioral_hint(payload: DiagnosisPayload) -> str | None:
    main_ms = [t.ms for t in payload.question_timings]
    pers_ms = [t.ms for t in payload.personality_question_timings]
    all_ms = main_ms + pers_ms
    if not all_ms:
        return None
    fast = sum(1 for ms in all_ms if ms < 4000)
    slow = sum(1 for ms in all_ms if ms > 25_000)
    parts = []
    if fast >= 3:
        parts.append("Часть ответов дана быстро — возможен импульсивный стиль или хорошая уверенность в теме.")
    if slow >= 2:
        parts.append("Есть вдумчивые ответы — склонность к рефлексии; при найме это можно подать как сильную сторону.")
    if not parts:
        parts.append("Темп ответов сбалансирован — хороший признак для ролей, где нужны и скорость, и точность.")
    return " ".join(parts)


def _answer_fingerprint(payload: DiagnosisPayload) -> int:
    """Детерминированный отпечаток ответов — разные комбинации → разные приоритеты и формулировки."""
    h = 0
    for a in sorted(payload.test_answers, key=lambda x: x.question_id):
        h = (h * 31 + a.question_id * 17 + ord(a.choice)) % (2**31 - 1)
    for a in sorted(payload.personality_test_answers, key=lambda x: x.question_id):
        h = (h * 31 + (a.question_id + 50) * 17 + ord(a.choice)) % (2**31 - 1)
    return int(h)


def build_style_fit(payload: DiagnosisPayload, ts: dict[str, int]) -> list[StyleFitBar]:
    fp = _answer_fingerprint(payload)
    tot = max(1, ts["analytical"] + ts["creative"] + ts["people"])
    ra = int(round(100 * ts["analytical"] / tot))
    rc = int(round(100 * ts["creative"] / tot))
    rp = max(0, 100 - ra - rc)
    j = (fp % 11) - 5
    ra = max(22, min(68, ra + j))
    rc = max(22, min(68, rc + (fp // 17) % 7 - 3))
    rp = max(22, min(68, 100 - ra - rc + ((fp // 5) % 5 - 2)))
    skill_n = len(payload.skills)
    edu_b = 8 if payload.education == Education.UNIVERSITY else 4 if payload.education == Education.COLLEGE else 0
    domain = max(35, min(94, 48 + skill_n * 7 + edu_b + (fp % 13)))
    sp = payload.interests[0].value.replace("_", " ")
    pack = resolve_profession_pack(payload.interests[0])
    (l1, h1), (l2, h2), (l3, h3) = pack.style_fit
    return [
        StyleFitBar(label=l1, percent=ra, hint=h1),
        StyleFitBar(label=l2, percent=rc, hint=h2),
        StyleFitBar(label=l3, percent=rp, hint=h3),
        StyleFitBar(label="Совпадение с выбранной сферой", percent=domain, hint=f"Интерес «{sp}» + навыки из профиля"),
    ]


def _score_direction_candidate(name: str, ts: dict[str, int], payload: DiagnosisPayload, fp: int, idx: int) -> int:
    n = name.lower()
    score = 44 + ((fp + idx * 17) % 23) + idx * 3
    a, cr, pe = ts["analytical"], ts["creative"], ts["people"]
    mx = max(a, cr, pe)
    if mx == a and mx > 0:
        score += sum(
            9
            for kw in (
                "данн",
                "sql",
                "python",
                "backend",
                "devops",
                "ml",
                "аналит",
                "систем",
                "контрол",
                "отчёт",
                "модел",
                "качеств",
                "тест",
                "авто",
                "процесс",
                "финанс",
                "метрик",
                "платформ",
                "api",
            )
            if kw in n
        )
    if mx == cr and mx > 0:
        score += sum(
            9
            for kw in (
                "дизайн",
                "ux",
                "ui",
                "контент",
                "продукт",
                "front",
                "бренд",
                "визуал",
                "исслед",
                "гипотез",
                "сторител",
                "коммуникац",
            )
            if kw in n
        )
    if mx == pe and mx > 0:
        score += sum(
            9
            for kw in (
                "клиент",
                "продаж",
                "поддерж",
                "hr",
                "команд",
                "проект",
                "партнёр",
                "обучен",
                "сопровожден",
                "успех",
                "сервис",
            )
            if kw in n
        )
    if SkillKey.PROGRAMMING in payload.skills and any(
        k in n for k in ("разработ", "backend", "data", "ml", "devops", "тест", "api", "инженер")
    ):
        score += 10
    if SkillKey.DESIGN in payload.skills and any(k in n for k in ("дизайн", "ux", "визуал", "контент", "бренд")):
        score += 10
    if SkillKey.COMMUNICATION in payload.skills and any(k in n for k in ("клиент", "продаж", "поддерж", "hr", "коммун")):
        score += 10
    if SkillKey.ANALYTICS in payload.skills and any(k in n for k in ("аналит", "данн", "метрик", "финанс", "контрол")):
        score += 10
    if SkillKey.MANAGEMENT in payload.skills and any(k in n for k in ("проект", "операц", "процесс", "координ")):
        score += 8
    if payload.education == Education.UNIVERSITY:
        score += 4
    elif payload.education == Education.SCHOOL:
        score -= 3
    return score


def _rationale_for_direction(
    code: str,
    track: str,
    dominant: str,
    interest: Interest,
    ts: dict[str, int],
    salt: int,
) -> str:
    tilt = {
        "analytical": "аналитика и структура",
        "creative": "креатив и визуал",
        "people": "люди и коммуникация",
    }[dominant]
    sp = interest.value.replace("_", " ")
    sec = sorted(("analytical", "creative", "people"), key=lambda k: ts[k], reverse=True)[1]
    sec_ru = {"analytical": "структура", "creative": "идеи", "people": "люди"}[sec]
    templates = (
        f"План {code}: по тесту сильнее «{tilt}». Трек «{track}» хорошо стыкуется с интересом «{sp}».",
        f"{code}: ответы теста тяготеют к «{tilt}»; «{track}» развивает эту линию в поле «{sp}».",
        f"План {code} — «{track}»: согласован с профилем ({tilt}) и сферой «{sp}».",
        f"Вариант {code}: «{track}» — следующий шаг; тест показывает «{tilt}», профиль — «{sp}».",
        f"{code}: «{track}»; опора на «{tilt}» (тест) при выборе «{sp}».",
    )
    base = templates[salt % len(templates)]
    if sec != dominant and salt % 2 == 0:
        base += f" Дополнительно прослеживается линия «{sec_ru}»."
    return base


def pick_directions(payload: DiagnosisPayload) -> list[tuple[str, str, int, str]]:
    """Три плана A/B/C: кандидаты из большого пула сферы + смежные треки по доминанте теста."""
    ts = _combined_ts(payload)
    fp = _answer_fingerprint(payload)
    primary = payload.interests[0]
    pool = list(DIRECTION_POOLS.get(primary, DIRECTION_POOLS[Interest.IT]))
    dominant = max(ts, key=lambda k: ts[k])
    pool = pool + list(ADJACENT_BY_DOMINANT.get(dominant, ()))
    seen: set[str] = set()
    uniq: list[str] = []
    for p in pool:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    scored = [(n, _score_direction_candidate(n, ts, payload, fp, i)) for i, n in enumerate(uniq)]
    scored.sort(key=lambda x: -x[1])
    top = scored[:3]
    fallback = list(DIRECTION_POOLS[Interest.BUSINESS])
    while len(top) < 3:
        for x in fallback:
            if x not in {t[0] for t in top}:
                top.append((x, 52))
                break
        else:
            break
    codes: list[Literal["A", "B", "C"]] = ["A", "B", "C"]
    top_three = top[:3]
    raw_values = [r for _, r in top_three]
    lo, hi = min(raw_values), max(raw_values)
    results: list[tuple[str, str, int, str]] = []
    for idx, ((name, raw), code) in enumerate(zip(top_three, codes)):
        if hi <= lo:
            match_score = 86 - idx * 9
        else:
            match_score = 52 + int(43 * (raw - lo) / (hi - lo))
        match_score = max(48, min(96, match_score + ((fp + idx * 13) % 3) - 1))
        if idx > 0 and match_score >= results[-1][2]:
            match_score = max(45, results[-1][2] - 6)
        why = _rationale_for_direction(code, name, dominant, primary, ts, fp + idx * 31)
        results.append((code, name, match_score, why))
    return results


INTEREST_SKILL_BIAS: dict[Interest, dict[SkillKey, int]] = {
    Interest.IT: {SkillKey.PROGRAMMING: 14, SkillKey.ANALYTICS: 10},
    Interest.DATA_AI: {SkillKey.ANALYTICS: 18, SkillKey.PROGRAMMING: 8},
    Interest.DEVOPS: {SkillKey.PROGRAMMING: 16, SkillKey.ANALYTICS: 8, SkillKey.MANAGEMENT: 4},
    Interest.DESIGN: {SkillKey.DESIGN: 20, SkillKey.COMMUNICATION: 6},
    Interest.MARKETING: {SkillKey.COMMUNICATION: 12, SkillKey.ANALYTICS: 8, SkillKey.DESIGN: 6},
    Interest.SALES: {SkillKey.COMMUNICATION: 16, SkillKey.ANALYTICS: 6, SkillKey.MANAGEMENT: 6},
    Interest.ENGINEERING: {SkillKey.ANALYTICS: 14, SkillKey.PROGRAMMING: 4, SkillKey.MANAGEMENT: 6},
    Interest.SCIENCE: {SkillKey.ANALYTICS: 18, SkillKey.DESIGN: 4},
    Interest.BUSINESS: {SkillKey.MANAGEMENT: 14, SkillKey.ANALYTICS: 10, SkillKey.COMMUNICATION: 6},
    Interest.FINANCE: {SkillKey.ANALYTICS: 18, SkillKey.MANAGEMENT: 10},
    Interest.HR: {SkillKey.COMMUNICATION: 16, SkillKey.MANAGEMENT: 12, SkillKey.ANALYTICS: 4},
    Interest.LEGAL: {SkillKey.ANALYTICS: 14, SkillKey.MANAGEMENT: 10, SkillKey.COMMUNICATION: 6},
    Interest.PROCUREMENT: {SkillKey.MANAGEMENT: 12, SkillKey.ANALYTICS: 12, SkillKey.COMMUNICATION: 4},
    Interest.LOGISTICS: {SkillKey.MANAGEMENT: 14, SkillKey.ANALYTICS: 12},
    Interest.REAL_ESTATE: {SkillKey.MANAGEMENT: 12, SkillKey.COMMUNICATION: 8, SkillKey.ANALYTICS: 6},
    Interest.ADMIN: {SkillKey.MANAGEMENT: 12, SkillKey.COMMUNICATION: 8, SkillKey.ANALYTICS: 4},
    Interest.PRODUCT: {SkillKey.COMMUNICATION: 10, SkillKey.ANALYTICS: 10, SkillKey.DESIGN: 6, SkillKey.MANAGEMENT: 8},
    Interest.SUPPORT: {SkillKey.COMMUNICATION: 16, SkillKey.PROGRAMMING: 4, SkillKey.MANAGEMENT: 4},
}


def _user_skill_strength(payload: DiagnosisPayload) -> dict[str, int]:
    """Проценты по 5 навыкам: из ответов теста + сферы (профиль), без ручных чекбоксов."""
    ts = _combined_ts(payload)
    fp = _answer_fingerprint(payload)
    interest = payload.interests[0]
    tot = max(1, ts["analytical"] + ts["creative"] + ts["people"])
    # База 40–58 с детерминированным разбросом
    scores: dict[str, int] = {}
    for i, k in enumerate(SkillKey):
        scores[k.value] = 40 + (fp >> (i * 5)) % 14

    dom = max(ts, key=lambda x: ts[x])
    if dom == "analytical":
        scores[SkillKey.ANALYTICS.value] += 14
        scores[SkillKey.PROGRAMMING.value] += 10
    elif dom == "creative":
        scores[SkillKey.DESIGN.value] += 16
        scores[SkillKey.COMMUNICATION.value] += 8
    else:
        scores[SkillKey.COMMUNICATION.value] += 14
        scores[SkillKey.MANAGEMENT.value] += 10

    scores[SkillKey.ANALYTICS.value] += int(18 * ts["analytical"] / tot)
    scores[SkillKey.DESIGN.value] += int(16 * ts["creative"] / tot)
    scores[SkillKey.COMMUNICATION.value] += int(12 * ts["people"] / tot)
    scores[SkillKey.MANAGEMENT.value] += int(10 * ts["people"] / tot)
    scores[SkillKey.PROGRAMMING.value] += int(10 * ts["analytical"] / tot)

    for sk, add in INTEREST_SKILL_BIAS.get(interest, {}).items():
        scores[sk.value] += add

    for sk in payload.skills:
        scores[sk.value] = min(95, scores[sk.value] + 6)

    for k in SkillKey:
        scores[k.value] = max(36, min(94, scores[k.value]))
    return scores


def _target_for_track(track_name: str) -> dict[str, int]:
    t = track_name.lower()
    targets = {k.value: 70 for k in SkillKey}
    if "python" in t or "данных" in t or "devops" in t:
        targets[SkillKey.PROGRAMMING.value] = 88
        targets[SkillKey.ANALYTICS.value] = 82
    elif "дизайн" in t or "ux" in t:
        targets[SkillKey.DESIGN.value] = 90
        targets[SkillKey.COMMUNICATION.value] = 65
    elif "маркетинг" in t or "crm" in t:
        targets[SkillKey.COMMUNICATION.value] = 85
        targets[SkillKey.ANALYTICS.value] = 70
    elif "инженер" in t or "робот" in t:
        targets[SkillKey.ANALYTICS.value] = 75
        targets[SkillKey.PROGRAMMING.value] = 55
    elif "наука" in t or "лаборатор" in t:
        targets[SkillKey.ANALYTICS.value] = 80
    elif "бизнес" in t or "финанс" in t:
        targets[SkillKey.MANAGEMENT.value] = 78
        targets[SkillKey.ANALYTICS.value] = 75
    return targets


def build_gap_analysis(payload: DiagnosisPayload, top_track: str, interest: Interest) -> GapAnalysis:
    user = _user_skill_strength(payload)
    target = _target_for_track(top_track)
    bars: list[GapSkillBar] = []
    gaps: list[int] = []
    pack = resolve_profession_pack(interest)
    labels = dict(pack.gap_bar_labels)
    for key in SkillKey:
        u = user[key.value]
        tg = target.get(key.value, 70)
        gap = max(0, tg - u)
        gaps.append(100 - min(100, gap))
        bars.append(
            GapSkillBar(
                label=labels[key.value],
                user_percent=u,
                target_percent=min(100, tg),
                gap_percent=min(100, gap),
            )
        )
    overall = sum(gaps) // len(gaps)
    weak = sorted(
        ((b.label, b.gap_percent) for b in bars if b.gap_percent > 15),
        key=lambda x: -x[1],
    )
    closing_labels = [w[0] for w in weak[:3]]
    return GapAnalysis(
        headline=pack.gap_headline,
        overall_hp=overall,
        bars=bars,
        closing_skills=closing_labels or ["Баланс близок — усильте портфолио и обратную связь"],
    )


def build_weekly_roadmap(direction_name: str, interest: Interest) -> list[WeekPlanItem]:
    low = direction_name.lower()
    pk = resolve_profession_pack(interest).key
    if pk == "tech" and ("python" in low or "java" in low or "данн" in low or "sql" in low):
        return [
            WeekPlanItem(week_range="Недели 1–2", topics=["Git + окружение", "основы языка + задачи"]),
            WeekPlanItem(week_range="Недели 3–4", topics=["SQL SELECT/JOIN", "мини-проект или скрипт"]),
        ]
    if pk == "design" or "дизайн" in low or "ux" in low:
        return [
            WeekPlanItem(week_range="Недели 1–2", topics=["Figma auto-layout", "редизайн одного экрана"]),
            WeekPlanItem(week_range="Недели 3–4", topics=["мини-кейс исследования", "портфолио: 3 работы"]),
        ]
    if pk == "marketing":
        return [
            WeekPlanItem(week_range="Недели 1–2", topics=["воронка и метрики", "один тестовый креатив"]),
            WeekPlanItem(week_range="Недели 3–4", topics=["отчёт по кампании", "согласование с продажами"]),
        ]
    if pk == "sales":
        return [
            WeekPlanItem(week_range="Недели 1–2", topics=["CRM и скрипты", "20 тренировочных диалогов"]),
            WeekPlanItem(week_range="Недели 3–4", topics=["продуктовый онбординг", "разбор возражений"]),
        ]
    if pk == "engineering":
        return [
            WeekPlanItem(week_range="Недели 1–2", topics=["нормы и ПО (CAD/учёт)", "учебный чертёж или ведомость"]),
            WeekPlanItem(week_range="Недели 3–4", topics=["участок проекта под наблюдением", "отчёт о проверке"]),
        ]
    if pk == "science":
        return [
            WeekPlanItem(week_range="Недели 1–2", topics=["протокол и журнал", "серия измерений"]),
            WeekPlanItem(week_range="Недели 3–4", topics=["обработка данных", "черновик отчёта/постера"]),
        ]
    if pk in ("office_finance", "hr", "legal"):
        return [
            WeekPlanItem(week_range="Недели 1–2", topics=["регламенты и шаблоны", "учебный кейс в таблицах"]),
            WeekPlanItem(week_range="Недели 3–4", topics=["сверка/документ/кандидат", "обратная связь наставника"]),
        ]
    if pk == "support":
        return [
            WeekPlanItem(week_range="Недели 1–2", topics=["продукт и база знаний", "тикеты по скрипту"]),
            WeekPlanItem(week_range="Недели 3–4", topics=["эскалации", "обратная связь в продукт"]),
        ]
    return [
        WeekPlanItem(week_range="Недели 1–2", topics=["рынок и вакансии", "один ключевой инструмент сферы"]),
        WeekPlanItem(week_range="Недели 3–4", topics=["кейс или проект", "резюме и сопроводительное"]),
    ]


def build_learning_resources(directions: list[str], interest: Interest) -> list[LearningResource]:
    name = directions[0] if directions else "карьера"
    pk = resolve_profession_pack(interest).key
    if pk == "tech":
        return [
            LearningResource(
                title="Stepik / freeCodeCamp — базовый трек",
                type="курс",
                description=f"Практика по теме «{name}»: код, задачи, мини-проекты.",
                url="https://stepik.org",
            ),
            LearningResource(
                title="«The Pragmatic Programmer»",
                type="книга",
                description="Про мастерство разработки и рост от джуна к мидлу.",
            ),
            LearningResource(
                title="Доклады конференций (HighLoad, HolyJS, Data Fest)",
                type="ресурс",
                description="Разбор архитектуры, продакшена и данных в индустрии.",
            ),
        ]
    if pk == "design":
        return [
            LearningResource(
                title="Interaction Design Foundation / Coursera UX",
                type="курс",
                description=f"UX/UI и исследования с практикой под «{name}».",
                url="https://www.interaction-design.org",
            ),
            LearningResource(
                title="«Don't Make Me Think» — Steve Krug",
                type="книга",
                description="Про ясность интерфейсов и юзабилити.",
            ),
            LearningResource(
                title="Кейсы на Behance / ADplist менторство",
                type="ресурс",
                description="Разбор портфолио и реальные брифы.",
            ),
        ]
    if pk in ("marketing", "sales"):
        return [
            LearningResource(
                title="Skillbox / Нетология — digital или продажи",
                type="курс",
                description=f"Модули по воронке, креативам и переговорам для «{name}».",
                url="https://skillbox.ru",
            ),
            LearningResource(
                title="«Продавай или умри» — Гитомер (или аналог по переговорам)",
                type="книга",
                description="Про дисциплину продаж и работу с клиентом.",
            ),
            LearningResource(
                title="Кейсы CMO и разборы рекламных кампаний",
                type="ресурс",
                description="YouTube-каналы маркетологов и sales-тренеры.",
            ),
        ]
    if pk == "engineering":
        return [
            LearningResource(
                title="Курсы CAD / отраслевые стандарты",
                type="курс",
                description=f"Практика чертежей и спецификаций под «{name}».",
            ),
            LearningResource(
                title="Отраслевые ГОСТ и методички работодателей",
                type="книга",
                description="Документация как основа инженерного роста.",
            ),
            LearningResource(
                title="Выставки и техно-митапы отрасли",
                type="ресурс",
                description="Нетворк с инженерами и поставщиками оборудования.",
            ),
        ]
    if pk == "science":
        return [
            LearningResource(
                title="Stepik: статистика и методы эксперимента",
                type="курс",
                description=f"База для работы в теме «{name}».",
                url="https://stepik.org",
            ),
            LearningResource(
                title="Журналы и препринты по вашей области",
                type="ресурс",
                description="Чтение статей и воспроизведение классических экспериментов.",
            ),
            LearningResource(
                title="Школы молодых учёных / конференции",
                type="ресурс",
                description="Доклады, постеры, грантовые конкурсы.",
            ),
        ]
    if pk == "office_finance":
        return [
            LearningResource(
                title="Курсы 1С / Excel для финансов / бухучёт",
                type="курс",
                description=f"Практика учёта и отчётности для «{name}».",
            ),
            LearningResource(
                title="Материалы ФНС / профстандарты",
                type="ресурс",
                description="Актуальные требования и формы.",
            ),
            LearningResource(
                title="«Финансовая грамотность для нефинансистов»",
                type="книга",
                description="Про отчёты и логику цифр для руководителей.",
            ),
        ]
    if pk == "hr":
        return [
            LearningResource(
                title="Курсы по рекрутингу и HR BP",
                type="курс",
                description=f"Полный цикл найма и адаптация под «{name}».",
            ),
            LearningResource(
                title="ТК РФ и кадровые процессы — краткие гайды",
                type="ресурс",
                description="База для безошибочных документов.",
            ),
            LearningResource(
                title="«Пять пороков команды» — Ленсиони",
                type="книга",
                description="Про динамику команд — полезно HR и лидерам.",
            ),
        ]
    if pk == "legal":
        return [
            LearningResource(
                title="Курс договорного права / корпоративка",
                type="курс",
                description=f"Практика договоров в контексте «{name}».",
            ),
            LearningResource(
                title="КонсультантПлюс / Гарант — обучающие вебинары",
                type="ресурс",
                description="Актуальная практика и шаблоны.",
            ),
            LearningResource(
                title="«Думай как юрист» — Feldman",
                type="книга",
                description="Про структуру правового рассуждения.",
            ),
        ]
    if pk == "support":
        return [
            LearningResource(
                title="Внутренняя база знаний + курс по продукту",
                type="курс",
                description=f"Углубление в продукт для линии «{name}».",
            ),
            LearningResource(
                title="Курсы сервиса и эмпатичных коммуникаций",
                type="курс",
                description="Тон, сложные клиенты, эскалации.",
            ),
            LearningResource(
                title="Сообщества поддержки (Support Driven)",
                type="ресурс",
                description="Обмен практиками CS и качества сервиса.",
            ),
        ]
    return [
        LearningResource(
            title="LinkedIn Learning / Stepik — базовый трек",
            type="курс",
            description=f"Серия модулей по теме «{name}»: фундамент + практика.",
            url="https://stepik.org",
        ),
        LearningResource(
            title="«So Good They Can't Ignore You» — Cal Newport",
            type="книга",
            description="Про навыки и карьерный капитал для молодых специалистов.",
        ),
        LearningResource(
            title="YouTube / конференции отрасли",
            type="ресурс",
            description="Регулярно смотрите доклады и разборы кейсов по выбранному направлению.",
        ),
    ]


def build_career_stages(primary_track: str | None = None) -> list[CareerStage]:
    track = (primary_track or "выбранном направлении").strip()
    return [
        CareerStage(
            title="Стажёр / вход в профессию",
            subtitle="База и безопасная среда",
            description=(
                "Вы осваиваете реальные рабочие процессы небольшими порциями: инструменты команды, "
                "стандарты качества, коммуникацию с наставником. Цель — предсказуемые задачи с обратной связью, "
                "чтобы сформировать уверенность и привычку доводить работу до «готово»."
            ),
            typical_duration="обычно 3–9 мес.",
            focus_areas=[
                "онбординг и документация",
                "микро-задачи с дедлайном",
                "наблюдение за senior / lead",
                f"лексика и контекст «{track}»",
            ],
            milestones=[
                "Понимаете, к кому и с каким вопросом идти в первый час, а не в пятый.",
                "Самостоятельно закрываете типовую задачу уровня «по шаблону» с одной итерацией правок.",
                "Умеете коротко фиксировать статус: что сделано, что блокирует, что нужно от других.",
                "Есть 1–2 артефакта для портфолио или внутреннего резюме (мини-кейс, скрин, отчёт).",
            ],
            transition_hint="Переходите к джуниору, когда стабильно тянете задачи средней сложности без ежедневного контроля по шагам.",
        ),
        CareerStage(
            title="Джуниор",
            subtitle="Самостоятельность в рамках команды",
            description=(
                "Вы берёте задачи от постановки до сдачи: уточняете требования, предлагаете варианты, "
                "учитываете ревью. Растёт скорость и ответственность за качество; вы уже влияете на сроки фичи или участка работ."
            ),
            typical_duration="часто 12–30 мес.",
            focus_areas=[
                "оценка сроков и рисков по своим задачам",
                "ревью коллег и работа с замечаниями",
                "документация для тех, кто придёт после вас",
                f"узкая специализация под {track}",
            ],
            milestones=[
                "Регулярно проходите ревью без «ломки» концепции — правки локальные.",
                "Можете объяснить нетехническому стейкхолдеру суть своей задачи простыми словами.",
                "Подхватываете баги/доработки смежных зон без потери фокуса по основному треку.",
                "Участвуете в планировании спринта/итерации с реалистичными обязательствами.",
            ],
            transition_hint="Уровень мидла ближе, когда вас тянут в разбор чужих задач и доверяют кусок продукта целиком.",
        ),
        CareerStage(
            title="Мидл",
            subtitle="Зона ответственности и влияние на результат",
            description=(
                "Вы ведёте направление внутри продукта или сервиса: декомпозиция, приоритеты, качество релиза. "
                "Менторите джуниоров точечно, участвуете в найме и онбординге. Ожидается зрелость в переговорах о сроках и техдолге."
            ),
            typical_duration="часто 24–60 мес.",
            focus_areas=[
                "дизайн решений и trade-off'ы",
                "кросс-функциональная координация",
                "метрики продукта / SLA / качество",
                "развитие людей рядом с вами",
            ],
            milestones=[
                "Один модуль или продуктовая линия «ваша» с точки зрения экспертизы.",
                "Умеете сказать «нет» или отложить без конфликта, опираясь на данные и риски.",
                "Повторяемые практики в команде (чек-листы, шаблоны) частично исходят от вас.",
                "Есть истории успеха: что изменилось в метриках или процессе после ваших инициатив.",
            ],
            transition_hint="Сеньорность — про масштаб: несколько команд, стратегия, долгосрочная архитектура или глубокая узкая экспертиза.",
        ),
        CareerStage(
            title="Сеньор / ведущий эксперт",
            subtitle="Стратегия, архитектура, культура",
            description=(
                "Вы задаёте направление развития технологий или практик, балансируете бизнес-цели и устойчивость системы. "
                "Влияете на набор компетенций в команде, этику решений и долгую дистанцию карьеры в отрасли."
            ),
            typical_duration="индивидуально, многолетний трек",
            focus_areas=[
                "видение на 1–3 года",
                "управление неопределённостью и кризисами",
                "публичное представление команды / компании",
                "наставничество лидов следующего уровня",
            ],
            milestones=[
                "Ключевые решения по продукту или платформе согласованы с вашей экспертной позицией.",
                "Вырастили или стабилизировали поток кадров под вашим направлением.",
                "Вас привлекают к спорным и дорогим инициативам до старта, а не после провала.",
                "Есть устойчивый личный бренд или узнаваемая зона ответственности на рынке.",
            ],
            transition_hint="Дальше — архитектор, директор направления, фаундер или глубокий principal: выбор зависит от аппетита к управлению и риску.",
        ),
    ]


def _user_personality_shares(ts: dict[str, int]) -> tuple[int, int, int]:
    tot = max(1, ts["analytical"] + ts["creative"] + ts["people"])
    ua = int(round(100 * ts["analytical"] / tot))
    uc = int(round(100 * ts["creative"] / tot))
    up = max(0, 100 - ua - uc)
    return ua, uc, up


def _profession_personality_target(*titles: str) -> tuple[int, int, int]:
    """Доли «логика / идеи / люди» для типичного профиля трека (по названию), сумма 100."""
    n = " ".join(t.lower() for t in titles if t).strip() or "направление"
    raw_a = raw_c = raw_p = 1.0
    for kw in (
        "данн",
        "sql",
        "python",
        "backend",
        "devops",
        "ml",
        "аналит",
        "систем",
        "контрол",
        "отчёт",
        "модел",
        "качеств",
        "тест",
        "авто",
        "процесс",
        "финанс",
        "метрик",
        "платформ",
        "api",
        "инженер",
        "учёт",
        "аудит",
        "юрис",
        "договор",
        "консультац",
        "научн",
        "лабор",
        "логистик",
        "закуп",
    ):
        if kw in n:
            raw_a += 4
    for kw in (
        "дизайн",
        "ux",
        "ui",
        "контент",
        "продукт",
        "front",
        "бренд",
        "визуал",
        "исслед",
        "гипотез",
        "сторител",
        "маркет",
        "копирайт",
        "креатив",
        "презентац",
    ):
        if kw in n:
            raw_c += 4
    for kw in (
        "клиент",
        "продаж",
        "поддерж",
        "hr",
        "команд",
        "проект",
        "партнёр",
        "обучен",
        "сопровожден",
        "успех",
        "сервис",
        "рекрут",
        "переговор",
        "pmo",
        "координ",
        "менеджер",
        "администр",
        "корпоратив",
    ):
        if kw in n:
            raw_p += 4
    s = raw_a + raw_c + raw_p
    ta = int(round(100 * raw_a / s))
    tc = int(round(100 * raw_c / s))
    tp = max(0, 100 - ta - tc)
    return ta, tc, tp


def _prep_support_score(level: str) -> int:
    """Балл опоры уровня подготовки для индикатора психологической готовности."""
    lv = (level or "").strip().lower()
    if lv == "сильный":
        return 86
    if lv == "слабый":
        return 62
    return 74


def _personality_only_totals(payload: DiagnosisPayload) -> dict[str, int] | None:
    if not payload.personality_test_answers or len(payload.personality_test_answers) != PERSONALITY_TEST_QUESTION_COUNT:
        return None
    return _score_test(payload.personality_test_answers)


def _sphere_only_totals(payload: DiagnosisPayload) -> dict[str, int] | None:
    if not payload.test_answers or len(payload.test_answers) != TEST_QUESTION_COUNT:
        return None
    return _score_test(payload.test_answers)


def build_insight_tiles(
    payload: DiagnosisPayload,
    ts: dict[str, int],
    directions: list[CareerDirection],
    mts_rows: list[MtsMatrixMatch],
    interest: Interest,
) -> list[InsightTile]:
    """Четыре метрики: психологическая готовность, акцент на тесте личности, сфера, люди/запросы."""
    sph = interest.value.replace("_", " ")
    if not directions:
        blank = InsightTile(title="—", value="—", subtitle="Нет рекомендованного трека")
        return [blank, blank, blank, blank]

    plan_a = directions[0]
    title_parts = [plan_a.name]
    if mts_rows:
        title_parts.append(mts_rows[0].title)
    ta, tc, tp = _profession_personality_target(*title_parts)
    ua, uc, up = _user_personality_shares(ts)

    def align(u: int, t: int) -> int:
        return max(0, min(100, 100 - abs(u - t)))

    fa, fc, fp = align(ua, ta), align(uc, tc), align(up, tp)
    combined_align = int(round((fa + fc + fp) / 3))

    ptot = _personality_only_totals(payload)
    if ptot:
        ua_p, uc_p, up_p = _user_personality_shares(ptot)
        fap, fcp, fpp = align(ua_p, ta), align(uc_p, tc), align(up_p, tp)
        personality_align = int(round((fap + fcp + fpp) / 3))
        person_tile_value = min(100, int(round(personality_align * 1.08)))
        fpp_p = fpp
    else:
        personality_align = combined_align
        person_tile_value = min(100, int(round(combined_align * 1.06)))
        fpp_p = fp

    prep_pts = _prep_support_score(payload.preparation_level)
    psych = int(round(0.44 * personality_align + 0.34 * combined_align + 0.22 * prep_pts))
    psych = max(41, min(97, psych))

    stot = _sphere_only_totals(payload)
    if stot:
        ua_s, uc_s, up_s = _user_personality_shares(stot)
        sphere_fit = int(round((align(ua_s, ta) + align(uc_s, tc) + align(up_s, tp)) / 3))
    else:
        sphere_fit = combined_align

    people_readiness = int(round(0.58 * fpp_p + 0.42 * fp))
    people_readiness = max(0, min(100, people_readiness))

    track_short = plan_a.name if len(plan_a.name) <= 44 else plan_a.name[:41] + "…"

    return [
        InsightTile(
            title="Психологическая готовность к роли",
            value=f"{psych}%",
            subtitle=(
                f"Насколько близки ваш стиль и подготовка к типичному профилю «{track_short}» "
                f"в сфере «{sph}» (оба теста + уровень подготовки). Не диагноз, а ориентир."
            ),
        ),
        InsightTile(
            title="Тест личности и роль",
            value=f"{person_tile_value}%",
            subtitle=(
                f"Усиленный блок по ответам только теста личности (все {PERSONALITY_TEST_QUESTION_COUNT} вопросов) "
                f"относительно ожиданий для «{track_short}». Чем выше, тем ближе ваш психопрофиль к роли."
            ),
        ),
        InsightTile(
            title="Совпадение теста сферы с треком",
            value=f"{sphere_fit}%",
            subtitle=(
                f"Как ответы по вашей сфере (тест 1) согласуются с типичным профилем направления «{track_short}»."
            ),
        ),
        InsightTile(
            title="Люди, переговоры и чужие запросы",
            value=f"{people_readiness}%",
            subtitle=(
                "Ориентир: насколько ваш профиль близок к работе с людьми и ответственностью за результат для других в этой роли."
            ),
        ),
    ]


def build_grade_plan(track: str, interest: Interest) -> list[GradePlanRow]:
    """План грейда: уровни и формулировки под семейство профессий (IT, дизайн, продажи, …)."""
    pack = resolve_profession_pack(interest)
    rows = format_grade_plan_rows(track, pack)
    return [
        GradePlanRow(code=a, stage_name=b, typical_roles=c, level_up_criteria=d) for a, b, c, d in rows
    ]


def build_skill_plan(payload: DiagnosisPayload, direction_names: list[str]) -> list[SkillPlanPhase]:
    strength = _user_skill_strength(payload)
    top_skills = sorted(strength.items(), key=lambda x: -x[1])[:3]
    labels_map = {
        SkillKey.PROGRAMMING.value: "технические навыки",
        SkillKey.ANALYTICS.value: "аналитика",
        SkillKey.DESIGN.value: "визуал и подача",
        SkillKey.COMMUNICATION.value: "коммуникации",
        SkillKey.MANAGEMENT.value: "организация",
    }
    focus_base = [labels_map.get(k, k.replace("_", " ")) for k, _ in top_skills]
    if payload.skills:
        focus_base = list(
            dict.fromkeys([s.value.replace("_", " ") for s in payload.skills] + focus_base)
        )[:5]
    d0 = direction_names[0] if direction_names else "выбранное направление"
    pk = resolve_profession_pack(payload.interests[0]).key
    artifact = "1 завершённый проект в портфолио (учебный или волонтёрский)"
    if pk == "design":
        artifact = "1 завершённая работа в портфолио (макет + краткий контекст задачи)"
    elif pk in ("sales", "marketing"):
        artifact = "1 учебный кейс с цифрами или тестовая кампания/воронка"
    elif pk in ("hr", "legal", "office_finance"):
        artifact = "1 учебный комплект документов или регламента под проверку наставника"
    elif pk == "science":
        artifact = "1 учебный отчёт или серия измерений по протоколу"
    elif pk == "engineering":
        artifact = "1 учебный комплект чертежей/спецификаций"
    elif pk == "support":
        artifact = "1 учебный день тикетов с разбором качества от наставника"
    team_event = "Командный проект или хакатон"
    if pk in ("sales", "marketing", "hr", "legal", "office_finance", "support"):
        team_event = "Командный кейс, ролевая симуляция или смена под супервизией"
    deep_focus = ["углубление в стек/инструменты", "стажировка или клиент", "софт-скиллы"]
    if pk == "design":
        deep_focus = ["дизайн-система и исследования", "стажировка в продукте", "презентация решений"]
    elif pk in ("sales", "marketing"):
        deep_focus = ["воронка и метрики", "работа с реальным/учебным клиентом", "переговоры"]
    elif pk in ("hr", "legal"):
        deep_focus = ["углубление в регламенты", "практика под супервизией", "этика и конфликты"]
    elif pk == "science":
        deep_focus = ["методы и статистика", "лаборатория или R&D стажировка", "научная коммуникация"]
    elif pk == "engineering":
        deep_focus = ["нормы и ПО", "производственная или проектная практика", "отчётность"]
    portfolio_n = "3+ проекта в портфолио"
    if pk in ("hr", "legal", "office_finance"):
        portfolio_n = "3+ учебных кейса или пакета документов в портфолио-досье"
    return [
        SkillPlanPhase(
            period="3 месяца",
            focus=focus_base[:3] or ["основы профессии", "инструмент №1 по направлению", "английский для профессии"],
            milestones=[
                f"Завершить вводный курс по «{d0}»",
                artifact,
                "Регулярная рефлексия раз в 2 недели",
            ],
        ),
        SkillPlanPhase(
            period="6 месяцев",
            focus=deep_focus,
            milestones=[
                team_event,
                "Мини-кейс с измеримым результатом",
                "Резюме и hh/LinkedIn",
            ],
        ),
        SkillPlanPhase(
            period="1 год",
            focus=["специализация", "личный бренд", "нетворкинг"],
            milestones=[
                "Уровень джуниор/мидл по рынку",
                portfolio_n,
                "Наставник или сообщество",
            ],
        ),
    ]


def mock_ai_narrative(payload: DiagnosisPayload, directions: list[CareerDirection]) -> str:
    ts = _combined_ts(payload)
    fp = _answer_fingerprint(payload)
    dom = max(ts, key=lambda k: ts[k])
    tilt = {
        "analytical": "структуру, цифры и проверку гипотез",
        "creative": "идеи, визуал и продуктовые образы",
        "people": "людей, переговоры и совместную работу",
    }[dom]
    names = ", ".join(f"{d.plan_code}: {d.name}" for d in directions)
    sp = payload.interests[0].value.replace("_", " ")
    variants = (
        f"По ответам теста сильнее тяга к {tilt}. Сценарии: {names}. План A — основной фокус квартала; B — если первый трек «не цепляет».",
        f"Тест подчёркивает {tilt}; это хорошо стыкуется с «{sp}». Направления: {names}. Держите один трек «главным», второй — для экспериментов на 2–3 недели.",
        f"Профиль: {tilt} + сфера «{sp}», подготовка «{payload.preparation_level}». Варианты: {names}. Не распыляйтесь: один навык и один мини-кейс в месяц.",
        f"Возраст {payload.age}, этап «{payload.education.value}». Тест → {tilt}. Маршруты {names}: начните с A, фиксируйте результат каждую пятницу.",
    )
    pk = resolve_profession_pack(payload.interests[0]).key
    closer = " Портфолио и стажировка убедительнее любого теста."
    if pk in ("legal", "hr", "office_finance"):
        closer = " Учебные кейсы документов и практика под супервизией убедительнее любого теста."
    elif pk in ("sales", "marketing", "support"):
        closer = " Реальные диалоги с клиентами (даже учебные) и метрики убедительнее любого теста."
    elif pk == "science":
        closer = " Воспроизводимые эксперименты и отчёты убедительнее любого теста."
    return variants[fp % len(variants)] + closer


def _mock_career_chat_reply(last_user: str) -> str:
    clip = last_user.strip().replace("\n", " ")[:120]
    return (
        "Я вижу ваш вопрос. Опираясь на тест и сохранённый разбор: выберите один фокус на месяц "
        "(навык + маленький проект), фиксируйте прогресс раз в неделю и обсудите страхи/ожидания с наставником или в чате сообщества. "
        f"По теме «{clip}» — напишите город, желаемый формат работы и что для вас важнее: деньги, обучение или баланс; тогда смогу сузить совет."
    )


async def career_chat(req: ChatRequest) -> tuple[str, Literal["llm", "mock"], str | None]:
    last_user = ""
    for m in reversed(req.messages):
        if m.role == "user":
            last_user = m.content.strip()
            break
    if not last_user:
        last_user = req.messages[-1].content.strip()
    parts: list[str] = []
    if req.context_summary:
        parts.append("Контекст разбора:\n" + req.context_summary[:1800])
    if req.directions_hint:
        parts.append("Направления:\n" + req.directions_hint[:500])
    transcript = "\n".join(f"{m.role}: {m.content[:900]}" for m in req.messages[-10:])
    user_tail = (
        "\n\nПоследнее сообщение пользователя (ответь только на него, по правилам из system):\n"
        f"«{last_user[:2000]}»"
    )
    user_prompt = "\n\n".join(
        parts
        + [f"История диалога:\n{transcript}", user_tail]
    )
    user_prompt += build_chat_user_instruction_suffix()
    mock = _mock_career_chat_reply(last_user)
    if not llm_configured():
        return (
            mock,
            "mock",
            "Ключ API не задан. Добавьте DEEPSEEK_API_KEY в .env и перезапустите сервер.",
        )
    out, api_notice = await fetch_llm_completion(
        user_prompt,
        max_tokens=900,
        temperature=0.35,
        system_prompt=CAREER_COACH_CHAT_SYSTEM,
    )
    if out:
        return out, "llm", None
    logger.warning("Чат: LLM не вернул ответ — показана заглушка (см. ошибку запроса выше в логе).")
    return mock, "mock", api_notice


async def fetch_llm_completion(
    user_prompt: str,
    *,
    max_tokens: int = 500,
    temperature: float = 0.6,
    system_prompt: str | None = None,
) -> tuple[str | None, str | None]:
    """
    Запрос к OpenAI-совместимому chat/completions.
    Возвращает (текст, подсказка_для_пользователя_при_сбое).
    """
    cfg = get_llm_settings()
    if not cfg:
        return None, None
    url, api_key, model = cfg
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    sys_default = DEFAULT_GENERIC_SYSTEM
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt or sys_default},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            r = await client.post(url, headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
            raw = data["choices"][0]["message"].get("content")
            if raw is None:
                logger.warning("LLM вернул пустой content: %s", str(data)[:400])
                return None, "Модель вернула пустой ответ. Попробуйте ещё раз."
            text = str(raw).strip()
            if not text:
                return None, "Модель вернула пустой ответ. Попробуйте ещё раз."
            return text, None
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        snippet = (e.response.text or "")[:500]
        logger.warning("LLM HTTP %s: %s", code, snippet)
        if code == 402:
            notice = (
                "На счёте DeepSeek нет средств (ошибка 402). "
                "Пополните баланс: https://platform.deepseek.com — после этого чат заработает."
            )
        elif code == 401:
            notice = "Ключ API отклонён (401). Проверьте DEEPSEEK_API_KEY в файле .env."
        elif code == 429:
            notice = "Слишком много запросов (429). Подождите минуту и попробуйте снова."
        else:
            notice = f"Сервис модели вернул ошибку {code}. Подробности — в окне, где запущен сервер."
        return None, notice
    except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError) as e:
        logger.warning("LLM запрос не удался: %s", e)
        return None, "Не удалось связаться с API модели. Проверьте интернет, VPN и окно сервера."


async def fetch_deepseek_advice(
    user_prompt: str,
    *,
    max_tokens: int = 500,
    temperature: float = 0.6,
) -> str | None:
    """Обратная совместимость: только текст ответа (подсказка об ошибке не используется)."""
    text, _ = await fetch_llm_completion(user_prompt, max_tokens=max_tokens, temperature=temperature)
    return text


def _req_covers_skill(req_lower: str, skills: list[SkillKey]) -> tuple[bool, int]:
    best_hp = 15
    covered = False
    for sk in skills:
        for kw in SKILL_KEYWORDS[sk]:
            if kw in req_lower:
                covered = True
                best_hp = max(best_hp, 88 - 5 * list(SKILL_KEYWORDS[sk]).index(kw) // max(1, len(SKILL_KEYWORDS[sk]) // 3))
    if any(w in req_lower for w in ("англий", "english", "b1", "b2")) and SkillKey.COMMUNICATION in skills:
        covered = True
        best_hp = max(best_hp, 60)
    if not covered and len(skills) == 0:
        best_hp = 25
    elif not covered:
        best_hp = 35
    return covered, min(100, best_hp)


def _vacancy_tags_for_interest(interest: Interest) -> tuple[str, ...]:
    m: dict[Interest, tuple[str, ...]] = {
        Interest.IT: ("it",),
        Interest.DATA_AI: ("it",),
        Interest.DEVOPS: ("it",),
        Interest.DESIGN: ("дизайн",),
        Interest.MARKETING: ("маркетинг",),
        Interest.SALES: ("маркетинг",),
        Interest.SUPPORT: ("маркетинг",),
        Interest.PRODUCT: ("маркетинг",),
        Interest.ENGINEERING: ("инженерия",),
        Interest.SCIENCE: ("наука", "инженерия"),
        Interest.LOGISTICS: ("инженерия",),
        Interest.BUSINESS: ("бизнес",),
        Interest.FINANCE: ("бизнес",),
        Interest.HR: ("бизнес",),
        Interest.LEGAL: ("бизнес",),
        Interest.PROCUREMENT: ("бизнес",),
        Interest.REAL_ESTATE: ("бизнес",),
        Interest.ADMIN: ("бизнес",),
    }
    return m.get(interest, ("бизнес",))


def _interest_matches_vacancy(interest: Interest, v: MockVacancy) -> bool:
    tag = v.profession_tag.lower()
    return any(x in tag for x in _vacancy_tags_for_interest(interest))


def enrich_vacancy(
    v: MockVacancy,
    skills: list[SkillKey],
    primary_interest: Interest,
) -> VacancyEnriched:
    rows: list[VacancyMatchRow] = []
    hps: list[int] = []
    for req in v.requirements:
        rl = req.lower()
        cov, hp = _req_covers_skill(rl, skills)
        rows.append(VacancyMatchRow(requirement=req, covered=cov, hp=hp))
        hps.append(hp)
    match_pct = sum(hps) // max(1, len(hps))
    if _interest_matches_vacancy(primary_interest, v):
        match_pct = min(100, match_pct + 12)
    why = f"Совпадение по требованиям ~{match_pct}%. "
    if _interest_matches_vacancy(primary_interest, v):
        why += f"Область «{primary_interest.value}» близка к тегу вакансии."
    else:
        why += "Интерес и тег вакансии различаются — смотрите разрыв по строкам ниже."
    missed = [r.requirement for r in rows if not r.covered]
    why_not = None
    if missed:
        why_not = "Слабее всего по: " + ", ".join(missed[:3])
    return VacancyEnriched(vacancy=v, match_percent=match_pct, why_match=why, why_not=why_not, rows=rows)


def filter_vacancy_list(
    items: list[MockVacancy],
    profession: str | None,
    level: str | None,
    city: str | None = None,
    work_format: str | None = None,
    salary_bracket: str | None = None,
    *,
    skip_level_filter: bool = False,
) -> list[MockVacancy]:
    """Фильтрация списка вакансий (моки или выдача hh.ru)."""
    items = list(items)
    if profession:
        p = profession.strip().lower()
        items = [v for v in items if p in v.profession_tag.lower() or p in v.title.lower()]
    if level and not skip_level_filter:
        l = level.strip().lower()
        items = [v for v in items if v.level.value.lower() == l]
    if city:
        c = city.strip().lower()
        if c in ("удалённо", "удаленно", "remote"):
            items = [v for v in items if v.work_format == WorkFormat.REMOTE or "удал" in v.city.lower()]
        else:
            items = [v for v in items if c in v.city.lower()]
    if work_format:
        wf = work_format.strip().lower()
        items = [v for v in items if v.work_format.value.lower() == wf]
    if salary_bracket:
        br = salary_bracket.strip().lower()

        def bracket_ok(v: MockVacancy) -> bool:
            sm = v.salary_min_rub
            if sm is None:
                return br == "low"
            if br == "low":
                return sm < 70_000
            if br == "medium":
                return 70_000 <= sm < 120_000
            if br == "high":
                return sm >= 120_000
            return True

        items = [v for v in items if bracket_ok(v)]
    return items


def filter_vacancies(
    profession: str | None,
    level: str | None,
    city: str | None = None,
    work_format: str | None = None,
    salary_bracket: str | None = None,
) -> list[MockVacancy]:
    return filter_vacancy_list(
        list(MOCK_VACANCIES),
        profession,
        level,
        city,
        work_format,
        salary_bracket,
        skip_level_filter=False,
    )


async def load_vacancies_for_match(req: JobMatchRequest) -> list[MockVacancy]:
    """Сначала hh.ru, при ошибке или пустом ответе — демо-вакансии."""
    from app.hh_client import fetch_hh_vacancies

    hh_list: list[MockVacancy] = []
    try:
        hh_list = await fetch_hh_vacancies(req)
    except Exception as e:
        logger.warning("hh.ru: не удалось загрузить вакансии (%s), используем демо-список", e)
    if hh_list:
        return filter_vacancy_list(
            hh_list,
            req.profession,
            req.level,
            req.city,
            req.work_format,
            req.salary_bracket,
            skip_level_filter=True,
        )
    return filter_vacancy_list(
        list(MOCK_VACANCIES),
        req.profession,
        req.level,
        req.city,
        req.work_format,
        req.salary_bracket,
        skip_level_filter=False,
    )


def _conversation_job_boost(v: MockVacancy, blob: str) -> int:
    if not blob.strip():
        return 0
    t = (v.title + " " + v.profession_tag + " " + " ".join(v.requirements)).lower()
    keys = (
        "python",
        "sql",
        "git",
        "figma",
        "ux",
        "ui",
        "дизайн",
        "маркетинг",
        "smm",
        "инженер",
        "cad",
        "лабор",
        "аналитик",
        "продаж",
        "продукт",
        "java",
        "разработ",
        "react",
        "frontend",
        "backend",
        "excel",
    )
    pts = 0
    for k in keys:
        if k in blob and k in t:
            pts += 3
    return min(15, pts)


async def match_jobs(req: JobMatchRequest) -> list[VacancyEnriched]:
    base = await load_vacancies_for_match(req)
    primary = req.interests[0]
    hint_blob = " ".join(
        x for x in (req.conversation_summary or "", req.recommended_track_hint or "") if x
    ).lower()
    enriched: list[VacancyEnriched] = []
    for v in base:
        e = enrich_vacancy(v, req.skills, primary)
        boost = _conversation_job_boost(v, hint_blob)
        if boost:
            new_pct = min(100, e.match_percent + boost)
            why = e.why_match + f" Учтены темы из чата и разбора (+{boost}%)."
            e = e.model_copy(update={"match_percent": new_pct, "why_match": why})
        enriched.append(e)
    enriched.sort(key=lambda e: e.match_percent, reverse=True)
    return enriched


async def build_analysis(payload: DiagnosisPayload) -> AnalysisResult:
    ts = _combined_ts(payload)
    primary_interest = payload.interests[0]
    prof_pack = resolve_profession_pack(primary_interest)
    style_fit = build_style_fit(payload, ts)
    raw_dirs = pick_directions(payload)
    salary_hints = {
        "A": prof_pack.salary_a,
        "B": prof_pack.salary_b,
        "C": prof_pack.salary_c,
    }
    lvl = payload.preparation_level
    directions = [
        CareerDirection(
            plan_code=code,
            name=name,
            match_score=score,
            rationale=why,
            first_steps=_first_steps_for_level(code, lvl, primary_interest),
            salary_motivation_hint=salary_hints.get(code),
        )
        for code, name, score, why in raw_dirs
    ]
    direction_names = [d.name for d in directions]
    top_track = direction_names[0]
    learning = build_learning_resources(direction_names, primary_interest)
    stages = build_career_stages(primary_track=top_track)
    skill_plan = build_skill_plan(payload, direction_names)
    gap = build_gap_analysis(payload, top_track, primary_interest)
    weekly = build_weekly_roadmap(top_track, primary_interest)

    summary_parts = [
        f"Возраст {payload.age}, образование: {payload.education.value}.",
        f"Интересы: {', '.join(i.value for i in payload.interests)}.",
        f"Уровень подготовки: {payload.preparation_level}.",
        f"Навыки: {', '.join(s.value.replace('_', ' ') for s in payload.skills) or '—'}.",
    ]
    if payload.motivation and payload.motivation.strip():
        summary_parts.append(f"Контекст: {payload.motivation.strip()}")
    if payload.profile_extra:
        extra_bits: list[str] = []
        for k, v in payload.profile_extra.items():
            if v is None or v == "" or v == []:
                continue
            if isinstance(v, list):
                extra_bits.append(f"{k}: {', '.join(str(x) for x in v)}")
            else:
                extra_bits.append(f"{k}: {v}")
        if extra_bits:
            summary_parts.append("Профиль (лист): " + "; ".join(extra_bits)[:2200])
    profile_summary = " ".join(summary_parts)
    behavioral = _behavioral_hint(payload)

    sph = primary_interest.value.replace("_", " ")
    plan_desc = ", ".join(f"{d.plan_code}={d.name} (совпадение ~{d.match_score}%)" for d in directions)
    narrative_prompt = (
        "Данные для экрана «ИИ-разбор» (веб-форма VibeWork). Сгенерируй один связный текст по правилам system.\n\n"
        "=== ПРОФИЛЬ ===\n"
        f"{profile_summary}\n\n"
        "=== СФЕРА И КОНТЕКСТ РОЛЕЙ ===\n"
        f"Главная сфера (ориентир советов): «{sph}». Справочный ключ профессионального пакета: {prof_pack.key}.\n"
        f"Уровень подготовки: {payload.preparation_level}.\n\n"
        "=== НАПРАВЛЕНИЯ A/B/C ===\n"
        f"{plan_desc}\n\n"
        "=== ЗАДАЧА ===\n"
        "Фокус на ближайший квартал в указанной сфере; один риск выгорания или перегруза; избегай штампа «учи только программирование», "
        "если сфера не сводится к разработке."
    )
    ai_text, _ai_err = await fetch_llm_completion(
        narrative_prompt,
        max_tokens=560,
        temperature=0.42,
        system_prompt=ANALYSIS_NARRATIVE_SYSTEM,
    )
    if not ai_text:
        ai_text = mock_ai_narrative(payload, directions)

    prep_branch = build_preparation_branch(payload)
    employer_hint = build_employer_feedback_hint(top_track)
    mts_rows = rank_mts_tracks(
        payload.interests[0],
        list(payload.skills),
        payload.test_answers,
        target_mts_role_id=payload.target_mts_role_id,
        personality_test_answers=payload.personality_test_answers,
    )
    insight_tiles_list = build_insight_tiles(payload, ts, directions, mts_rows, primary_interest)
    grade_plan_rows = build_grade_plan(top_track, primary_interest)

    return AnalysisResult(
        profile_summary=profile_summary,
        behavioral_hint=behavioral,
        directions=directions,
        gap_analysis=gap,
        learning_path=learning,
        career_stages=stages,
        skill_plan=skill_plan,
        weekly_roadmap=weekly,
        ai_narrative=ai_text,
        mts_matrix=mts_rows,
        style_fit=style_fit,
        insight_tiles=insight_tiles_list,
        grade_plan=grade_plan_rows,
        preparation_branch=prep_branch,
        employer_feedback=employer_hint,
        ai_pipeline=list(AI_PIPELINE_STEPS),
    )


def simulator_start(role_key: str) -> SimulatorStep:
    key = role_key if role_key in SIMULATOR_BRANCHES else "analyst"
    branch = SIMULATOR_BRANCHES[key]
    step0 = branch[0]
    choices = [
        SimulatorChoice(id=c["id"], label=c["label"], points_delta=c["delta"]) for c in step0["choices"]
    ]
    return SimulatorStep(
        step_index=0,
        title=step0["title"],
        narrative=step0["narrative"],
        choices=choices,
        career_points=50,
        is_final=False,
    )


def simulator_advance(adv: SimulatorAdvance) -> SimulatorStep:
    key = adv.state.role_key if adv.state.role_key in SIMULATOR_BRANCHES else "analyst"
    branch = SIMULATOR_BRANCHES[key]
    idx = adv.state.step_index
    step_data = branch[idx]
    delta = 0
    for c in step_data["choices"]:
        if c["id"] == adv.choice_id:
            delta = int(c["delta"])
            break
    new_pts = max(0, min(100, adv.state.career_points + delta))
    hist = list(adv.state.history)
    hist.append(adv.choice_id)

    next_idx = idx + 1
    if next_idx >= len(branch):
        return SimulatorStep(
            step_index=next_idx,
            title="Итог симуляции",
            narrative=(
                f"Ваши карьерные очки: {new_pts}/100. "
                "В реальности добавьте дедлайны, стейкхолдеров и метрики — так растут быстрее."
            ),
            choices=[],
            career_points=new_pts,
            is_final=True,
        )

    sn = branch[next_idx]
    choices = [SimulatorChoice(id=c["id"], label=c["label"], points_delta=c["delta"]) for c in sn["choices"]]
    return SimulatorStep(
        step_index=next_idx,
        title=sn["title"],
        narrative=sn["narrative"],
        choices=choices,
        career_points=new_pts,
        is_final=False,
    )
