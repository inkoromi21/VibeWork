"""Школьная анкета: отдельные поля и правила заполненности."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.questionnaire_fields import (
    AUDIENCE_SCHOOL,
    is_profile_complete,
    questionnaire_audience,
    resolve_profile_schema,
)


def _school_profile_complete():
    return {
        "age": 16,
        "city": "Казань",
        "education_detail": "school_8_11",
        "course_grade": "10 класс",
        "interest_spheres": '["it_dev"]',
        "favorite_subjects": '["math", "informatics"]',
        "like_to_do": "роботы",
        "post_school_goal": "after_11_university",
        "exam_focus": "ege_11",
        "hours_per_week": 8,
    }


def test_questionnaire_audience_school_vs_career() -> None:
    assert questionnaire_audience("school_8_11") == AUDIENCE_SCHOOL
    assert questionnaire_audience("spo") == "career"
    assert questionnaire_audience("univ_bachelor") == "career"


def test_resolve_schema_hides_career_goals_for_school() -> None:
    from wibe_work.questionnaire_fields import get_profile_schema

    master = get_profile_schema()
    school = resolve_profile_schema(master, AUDIENCE_SCHOOL)
    ids = {s["id"] for s in school["sections"]}
    assert "school_interests" in ids
    assert "goals" not in ids
    assert "target_salary" not in {f["id"] for s in school["sections"] for f in s["fields"]}


def test_school_complete_without_salary_or_study_form() -> None:
    assert is_profile_complete(_school_profile_complete())


def test_school_incomplete_without_favorite_subjects() -> None:
    p = _school_profile_complete()
    p.pop("favorite_subjects")
    assert not is_profile_complete(p)


def test_spo_still_requires_career_fields() -> None:
    p = {
        "age": 19,
        "city": "Москва",
        "education_detail": "spo",
        "course_grade": "2 курс",
        "study_form": "fulltime",
        "interest_spheres": '["marketing"]',
        "like_to_do": "smm",
        "work_format_preference": "hybrid",
        "work_schedule": "after_classes",
        "target_salary": 35000,
        "hours_per_week": 12,
    }
    assert is_profile_complete(p)
