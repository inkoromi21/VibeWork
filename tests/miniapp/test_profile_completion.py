"""Проверка заполненности анкеты (completion rules v2)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.questionnaire_fields import is_profile_complete, profile_field_filled


def test_complete_v2_profile():
    p = {
        "age": 18,
        "city": "Казань",
        "education_detail": "univ_bachelor",
        "course_grade": "2 курс",
        "study_form": "fulltime",
        "interest_spheres": '["it_dev"]',
        "like_to_do": "код",
        "work_format_preference": "remote",
        "work_schedule": "flex",
        "target_salary": 40000,
        "hours_per_week": 15,
    }
    assert is_profile_complete(p)


def test_legacy_course_or_grade_counts_school():
    p = {
        "age": 17,
        "city": "Москва",
        "education_detail": "school_8_11",
        "course_or_grade": 10,
        "main_sphere": "it_dev",
        "interest_spheres": '["it_dev"]',
        "favorite_subjects": '["math"]',
        "like_to_do": "игры",
        "post_school_goal": "undecided",
        "exam_focus": "profile_only",
        "hours_per_week": 8,
    }
    assert profile_field_filled(p, "course_grade")
    assert is_profile_complete(p)


def test_incomplete_missing_goals():
    p = {
        "age": 20,
        "city": "СПб",
        "education_detail": "spo",
        "course_grade": "1",
        "study_form": "fulltime",
        "interest_spheres": "marketing",
        "like_to_do": "smm",
        "work_format_preference": "hybrid",
        "work_schedule": "after_classes",
    }
    assert not is_profile_complete(p)
