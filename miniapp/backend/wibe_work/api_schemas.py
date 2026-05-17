"""Pydantic-схемы тел запросов/ответов HTTP API миниаппы."""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List


class ProfileData(BaseModel):
    nickname: Optional[str] = Field(None, max_length=80)
    age: Optional[int] = None
    city: Optional[str] = None
    main_sphere: Optional[str] = None
    education_detail: Optional[str] = None
    preparation_level: Optional[str] = None
    motivation_ai: Optional[str] = None
    work_format_pref: Optional[str] = None
    education_level: Optional[str] = None
    course_or_grade: Optional[int] = None
    interests: Optional[str] = None
    like_to_do: Optional[str] = None
    dislike_to_do: Optional[str] = None
    work_format_preference: Optional[str] = None
    relocation_ready: Optional[str] = None
    work_schedule: Optional[str] = None
    software_skills: Optional[str] = None
    target_salary: Optional[int] = None
    study_form: Optional[str] = None
    interest_spheres: Optional[str] = None
    languages: Optional[str] = None
    programming_skills: Optional[str] = None
    social_media_skills: Optional[str] = None
    extra_education: Optional[str] = None
    soft_communication: Optional[int] = Field(None, ge=1, le=5)
    soft_teamwork: Optional[int] = Field(None, ge=1, le=5)
    soft_organization: Optional[int] = Field(None, ge=1, le=5)
    soft_stress: Optional[int] = Field(None, ge=1, le=5)
    soft_creativity: Optional[int] = Field(None, ge=1, le=5)
    soft_analytical: Optional[int] = Field(None, ge=1, le=5)
    experience_official: Optional[str] = None
    experience_side: Optional[str] = None
    experience_volunteer: Optional[str] = None
    experience_projects: Optional[str] = None
    achievements: Optional[str] = None
    internship_ready: Optional[str] = None
    hours_per_week: Optional[int] = None
    has_resume_portfolio: Optional[str] = None
    acquisition_source: Optional[str] = None
    career_priority: Optional[str] = None
    monthly_focus_skill: Optional[str] = None
    monthly_focus_project: Optional[str] = None
    weekly_progress_note: Optional[str] = None
    primary_pain: Optional[str] = None
    course_grade: Optional[str] = None

    @field_validator("nickname", mode="before")
    @classmethod
    def strip_nickname(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            return s if s else None
        return v


class AnswerItem(BaseModel):
    question_id: int
    text: Optional[str] = None
    choice_id: Optional[int] = None
    choice_ids: Optional[List[int]] = None


class PollAnswerRequest(BaseModel):
    user_id: str
    poll_id: int
    answers: List[AnswerItem]


class CompetencyItem(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    level: int = Field(3, ge=1, le=5)


class CompetencyBulkRequest(BaseModel):
    items: List[CompetencyItem]


class JobSearchParams(BaseModel):
    max_listing_age_days: int = Field(120, ge=1, le=365)


class EmailRegisterBody(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class EmailLoginBody(BaseModel):
    """email: обычный адрес или логин админа без @ (ADMIN_LOGIN из .env)."""

    email: str = Field(..., min_length=1, max_length=320)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def email_or_admin_login(cls, v: str) -> str:
        s = (v or "").strip()
        if not s:
            raise ValueError("Укажите email или логин")
        if "@" not in s:
            return s
        local, _, domain = s.partition("@")
        if not local or not domain or "." not in domain:
            raise ValueError("Некорректный email")
        return s.lower()


class EmailPasswordChangeBody(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class EmailForgotPasswordBody(BaseModel):
    email: EmailStr


class EmailResetPasswordBody(BaseModel):
    token: str = Field(..., min_length=10, max_length=256)
    new_password: str = Field(..., min_length=8, max_length=128)
