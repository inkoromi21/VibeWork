"""Pydantic-схемы запросов и ответов HTTP API VibeWork (веб)."""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class Interest(str, Enum):
    """Направления в профиле (расширенный список). Значения = то, что уходит в API."""

    IT = "IT"
    DATA_AI = "данные_и_AI"
    DEVOPS = "DevOps_и_SRE"
    DESIGN = "дизайн"
    MARKETING = "маркетинг"
    SALES = "продажи"
    ENGINEERING = "инженерия"
    SCIENCE = "наука"
    BUSINESS = "бизнес"
    FINANCE = "финансы_и_контроль"
    HR = "HR_и_рекрутинг"
    LEGAL = "юриспруденция"
    PROCUREMENT = "закупки"
    LOGISTICS = "логистика"
    REAL_ESTATE = "недвижимость_и_эксплуатация"
    ADMIN = "офис_и_администрирование"
    PRODUCT = "продукт_и_PMO"
    SUPPORT = "поддержка_и_сервис"


class Education(str, Enum):
    SCHOOL = "школа"
    COLLEGE = "колледж"
    UNIVERSITY = "вуз"


class EducationLevel(str, Enum):
    INTERN = "стажер"
    JUNIOR = "джуниор"
    MIDDLE = "мидл"
    SENIOR = "сеньор"


class WorkFormat(str, Enum):
    REMOTE = "удалённо"
    OFFICE = "офис"
    HYBRID = "гибрид"


class SkillKey(str, Enum):
    PROGRAMMING = "программирование"
    ANALYTICS = "аналитика"
    COMMUNICATION = "коммуникации"
    DESIGN = "дизайн"
    MANAGEMENT = "организация_и_управление"


TEST_QUESTION_COUNT = 10
_TEST_IDS = list(range(1, TEST_QUESTION_COUNT + 1))

PERSONALITY_TEST_QUESTION_COUNT = 8  # legacy default; фактическое число — 4–22 по треку
PERSONALITY_TEST_MIN = 4
PERSONALITY_TEST_MAX = 22


class QuestionTiming(BaseModel):
    question_id: int = Field(ge=1, le=TEST_QUESTION_COUNT)
    ms: int = Field(ge=0, le=600_000)


class PersonalityQuestionTiming(BaseModel):
    question_id: int = Field(ge=1, le=PERSONALITY_TEST_MAX)
    ms: int = Field(ge=0, le=600_000)


class TestAnswer(BaseModel):
    question_id: int = Field(ge=1, le=TEST_QUESTION_COUNT)
    choice: Literal["A", "B", "C", "D"]


class PersonalityTestAnswer(BaseModel):
    question_id: int = Field(ge=1, le=PERSONALITY_TEST_MAX)
    choice: Literal["A", "B", "C", "D"]


class DiagnosisPayload(BaseModel):
    age: int = Field(ge=14, le=30, description="Как в профиле / Google Sheet")
    interests: list[Interest] = Field(min_length=1, max_length=6)
    education: Education
    test_answers: list[TestAnswer] = Field(
        min_length=TEST_QUESTION_COUNT,
        max_length=TEST_QUESTION_COUNT,
    )
    personality_test_answers: list[PersonalityTestAnswer] = Field(
        min_length=PERSONALITY_TEST_MIN,
        max_length=PERSONALITY_TEST_MAX,
        description="Профориентация: интересы, мотивы, тип среды (число вопросов зависит от класса/курса)",
    )
    skills: list[SkillKey] = Field(default_factory=list)
    question_timings: list[QuestionTiming] = Field(default_factory=list)
    personality_question_timings: list[PersonalityQuestionTiming] = Field(default_factory=list)
    motivation: str | None = Field(None, max_length=2500)
    profile_extra: dict | None = Field(
        None,
        description="Расширенные данные профиля (город, сферы, шкалы и т.д.) — структура как в /api/profile/schema",
    )
    preparation_level: Literal["слабый", "средний", "сильный"] = "средний"
    target_mts_role_id: str | None = Field(
        None,
        description="Служебное поле; в UI скрыто — матрица МТС используется только на сервере",
    )

    @field_validator("test_answers")
    @classmethod
    def unique_questions(cls, v: list[TestAnswer]) -> list[TestAnswer]:
        ids = [a.question_id for a in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Каждый вопрос теста должен отвечаться один раз")
        sorted_ids = sorted(ids)
        if sorted_ids != _TEST_IDS:
            raise ValueError(f"Нужны ответы на вопросы 1–{TEST_QUESTION_COUNT}")
        return v

    @field_validator("personality_test_answers")
    @classmethod
    def unique_personality_questions(cls, v: list[PersonalityTestAnswer]) -> list[PersonalityTestAnswer]:
        ids = [a.question_id for a in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Каждый вопрос блока профориентации должен отвечаться один раз")
        expected = list(range(1, len(ids) + 1))
        if sorted(ids) != expected:
            raise ValueError(
                f"Нужны ответы на все вопросы блока 2 подряд (1–{len(ids)}), без пропусков"
            )
        return v


class CareerStage(BaseModel):
    title: str
    subtitle: str = ""
    description: str
    typical_duration: str
    focus_areas: list[str] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)
    transition_hint: str = ""


class LearningResource(BaseModel):
    title: str
    type: str
    description: str
    url: str | None = None


class CareerDirection(BaseModel):
    plan_code: Literal["A", "B", "C"]
    name: str
    match_score: int = Field(ge=0, le=100)
    rationale: str
    first_steps: list[str]
    salary_motivation_hint: str | None = None


class SkillPlanPhase(BaseModel):
    period: str
    focus: list[str]
    milestones: list[str]


class GapSkillBar(BaseModel):
    label: str
    user_percent: int = Field(ge=0, le=100)
    target_percent: int = Field(ge=0, le=100)
    gap_percent: int = Field(ge=0, le=100)


class GapAnalysis(BaseModel):
    headline: str
    overall_hp: int = Field(ge=0, le=100)
    bars: list[GapSkillBar]
    closing_skills: list[str]


class WeekPlanItem(BaseModel):
    week_range: str
    topics: list[str]


class MockVacancy(BaseModel):
    id: str
    title: str
    company: str
    requirements: list[str]
    profession_tag: str
    level: EducationLevel
    salary_hint: str | None = None
    city: str
    work_format: WorkFormat
    salary_min_rub: int | None = None
    source_url: str | None = Field(None, description="Ссылка на вакансию (hh.ru и т.п.)")


class VacancyMatchRow(BaseModel):
    requirement: str
    covered: bool
    hp: int = Field(ge=0, le=100)


class VacancyEnriched(BaseModel):
    vacancy: MockVacancy
    match_percent: int = Field(ge=0, le=100)
    why_match: str
    why_not: str | None = None
    rows: list[VacancyMatchRow]


class JobMatchRequest(BaseModel):
    skills: list[SkillKey] = Field(default_factory=list)
    interests: list[Interest] = Field(min_length=1)
    profession: str | None = None
    level: str | None = None
    city: str | None = None
    work_format: str | None = None
    salary_bracket: str | None = Field(
        None,
        description="low | medium | high — фильтр по демо-зарплатам",
    )
    conversation_summary: str | None = Field(
        None,
        max_length=2500,
        description="Фрагменты чата с ИИ + разбор — для мягкого буста вакансий",
    )
    recommended_track_hint: str | None = Field(
        None,
        max_length=400,
        description="Например название плана A или топ-роль из матрицы",
    )


class MtsMatrixMatch(BaseModel):
    """Роль из матрицы МТС с оценкой соответствия профилю и тесту."""

    id: str
    title: str
    profession_tag: str
    relevance: int = Field(ge=0, le=100)
    reason: str
    requirements: list[str]
    duties: list[str]


class MtsPreviewPayload(BaseModel):
    """Превью матрицы (внутренние/отладочные вызовы): тест либо пустой, либо полный набор ответов."""

    interests: list[Interest] = Field(min_length=1, max_length=6)
    skills: list[SkillKey] = Field(default_factory=list)
    test_answers: list[TestAnswer] = Field(default_factory=list)
    personality_test_answers: list[PersonalityTestAnswer] = Field(default_factory=list)
    target_mts_role_id: str | None = None

    @field_validator("test_answers")
    @classmethod
    def all_or_empty(cls, v: list[TestAnswer]) -> list[TestAnswer]:
        if not v:
            return v
        if len(v) != TEST_QUESTION_COUNT:
            raise ValueError(
                f"Укажите все {TEST_QUESTION_COUNT} ответов теста или не передавайте test_answers"
            )
        ids = [a.question_id for a in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Дубли в ответах теста")
        if sorted(ids) != _TEST_IDS:
            raise ValueError(f"Нужны ответы на вопросы 1–{TEST_QUESTION_COUNT}")
        return v

    @field_validator("personality_test_answers")
    @classmethod
    def personality_all_or_empty(cls, v: list[PersonalityTestAnswer]) -> list[PersonalityTestAnswer]:
        if not v:
            return v
        if len(v) < PERSONALITY_TEST_MIN or len(v) > PERSONALITY_TEST_MAX:
            raise ValueError(
                f"Укажите от {PERSONALITY_TEST_MIN} до {PERSONALITY_TEST_MAX} ответов блока профориентации "
                "или не передавайте поле"
            )
        ids = [a.question_id for a in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Дубли в ответах блока профориентации")
        if sorted(ids) != list(range(1, len(ids) + 1)):
            raise ValueError(f"Нужны ответы на вопросы 1–{len(ids)} блока профориентации подряд")
        return v


class ChatMessageIn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    messages: list[ChatMessageIn] = Field(min_length=1, max_length=48)
    context_summary: str | None = Field(None, max_length=2000)
    directions_hint: str | None = Field(None, max_length=600)


class ChatResponse(BaseModel):
    """source=llm — ответ модели; mock — заглушка (нет ключа или сбой запроса к API)."""

    reply: str
    source: Literal["llm", "mock"]
    notice: str | None = None  # если mock — коротко, почему (баланс, ключ, сеть)


class PreparationBranch(BaseModel):
    """Ветка по уровню подготовки (как на блок-схеме: слабый / средний / сильный)."""

    level: Literal["слабый", "средний", "сильный"]
    headline: str
    next_route: str
    checklist: list[str]


class EmployerFeedbackHint(BaseModel):
    """Симуляция фокуса работодателя до собеседования."""

    headline: str
    body: str
    suggestion: str


class AiPipelineStep(BaseModel):
    """Шаг контура ИИ (визуальная дорожка в отчёте)."""

    idx: int = Field(ge=1, le=9)
    label: str
    target_id: str


class StyleFitBar(BaseModel):
    """Проценты близости к типам задач (без показа матрицы ролей МТС)."""

    label: str
    percent: int = Field(ge=0, le=100)
    hint: str | None = None


class InsightTile(BaseModel):
    """Четыре компактные метрики в блоке рядом со сценариями."""

    title: str
    value: str
    subtitle: str = ""


class GradePlanRow(BaseModel):
    """Строка плана грейда (уровень → роли → как перейти дальше)."""

    code: str
    stage_name: str
    typical_roles: str
    level_up_criteria: str


class AnalysisResult(BaseModel):
    profile_summary: str
    behavioral_hint: str | None = None
    directions: list[CareerDirection]
    gap_analysis: GapAnalysis
    learning_path: list[LearningResource]
    learning_path_detail: dict | None = Field(
        None,
        description="Путь обучения: шаги, ресурсы из каталога, прогресс",
    )
    individual_advice: dict | None = Field(
        None,
        description="Советы по планам A/B/C с привязкой к материалам",
    )
    growth_stages_rich: list[dict] | None = Field(
        None,
        description="Этапы роста с материалами и чеклистами",
    )
    career_stages: list[CareerStage]
    skill_plan: list[SkillPlanPhase]
    weekly_roadmap: list[WeekPlanItem]
    ai_narrative: str
    mts_matrix: list[MtsMatrixMatch] = Field(
        default_factory=list,
        description="Роли матрицы с relevance; в UI — только полосы %, без reason/requirements",
    )
    style_fit: list[StyleFitBar]
    insight_tiles: list[InsightTile] = Field(
        default_factory=list,
        description="4 быстрых индикатора рядом со сценариями A/B/C",
    )
    grade_plan: list[GradePlanRow] = Field(
        default_factory=list,
        description="План грейда по этапам роста",
    )
    preparation_branch: PreparationBranch
    employer_feedback: EmployerFeedbackHint
    ai_pipeline: list[AiPipelineStep]


class SimulatorChoice(BaseModel):
    id: str
    label: str
    points_delta: int = Field(ge=-20, le=30)


class SimulatorStep(BaseModel):
    step_index: int
    title: str
    narrative: str
    choices: list[SimulatorChoice]
    career_points: int = Field(ge=0, le=100)
    is_final: bool = False
    sim_role: str | None = Field(None, description="Нормализованный ключ сценария")
    day_path: list[dict[str, Any]] = Field(default_factory=list)


class SimulatorState(BaseModel):
    role_key: str
    step_index: int
    career_points: int = Field(ge=0, le=100)
    history: list[str] = Field(default_factory=list)
    day_path: list[dict[str, Any]] = Field(default_factory=list)


class SimulatorAdvance(BaseModel):
    state: SimulatorState
    choice_id: str

