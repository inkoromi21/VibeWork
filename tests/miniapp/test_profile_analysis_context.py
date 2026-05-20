"""Разбор и обучение учитывают поля школьной и карьерной анкеты."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.learning.assessment_signals import (
    build_assessment_signals,
    resource_allowed,
)
from wibe_work.services.career_analysis_school import build_school_gap_analysis, pick_school_path_plans
from wibe_work.services.learning.catalog import resources_by_id
from wibe_work.services.profile_analysis_context import (
    analysis_mode_for_profile,
    build_profile_summary_for_analysis,
    favorite_subjects_labels,
)


def _school_full():
    return {
        "education_detail": "school_8_11",
        "course_grade": "11 класс",
        "interest_spheres": '["it_dev"]',
        "favorite_subjects": '["math", "informatics"]',
        "post_school_goal": "after_11_university",
        "exam_focus": "ege_11",
        "like_to_do": "роботы",
        "hours_per_week": 12,
    }


def test_profile_summary_includes_school_fields():
    summary = build_profile_summary_for_analysis(_school_full(), "it_dev", "medium")
    assert "Любимые предметы" in summary
    assert "Математика" in summary
    assert "План после школы" in summary or "вуз" in summary
    assert "ЕГЭ" in summary
    assert "школьник" in summary.lower() or "Школьный" in summary


def test_profile_summary_no_duplicate_school_lines():
    summary = build_profile_summary_for_analysis(_school_full(), "it_dev", "medium")
    assert summary.count("Любимые предметы:") == 1
    assert summary.count("План после школы:") == 1


def test_profile_summary_includes_career_fields_for_spo():
    profile = {
        "education_detail": "spo",
        "course_grade": "2 курс",
        "study_form": "fulltime",
        "work_format_preference": "remote",
        "target_salary": 50000,
        "interest_spheres": '["marketing"]',
    }
    summary = build_profile_summary_for_analysis(profile, "marketing", "weak")
    assert "Формат работы" in summary
    assert "зарплат" in summary.lower()
    assert "СПО" in summary or "колледж" in summary


def test_school_paths_boost_post_school_goal():
    axes = [{"key": "structure_mastery", "label": "Структура", "value_percent": 60}]
    scenarios = pick_school_path_plans(_school_full(), "it_dev", axes, 7)
    names = " ".join(p["name"] for p in scenarios["plans"]).lower()
    assert "вуз" in names or "11" in names


def test_school_gap_includes_favorite_subjects():
    gap = build_school_gap_analysis(
        _school_full(),
        "it_dev",
        "Колледж IT",
        [{"key": "structure_mastery", "label": "Структура", "value_percent": 70}],
        3,
    )
    labels = " ".join(b["label"] for b in gap["bars"]).lower()
    assert "матем" in labels or "информ" in labels


def test_school_signals_block_career_resume_resources():
    signals = build_assessment_signals(
        profile=_school_full(),
        interest="it_dev",
        preparation_level="medium",
        gap={"closing_skills": ["Математика"]},
    )
    assert signals["analysis_mode"] == "school"
    blocked = 0
    allowed = 0
    for r in resources_by_id().values():
        if resource_allowed(r, signals):
            allowed += 1
        else:
            blocked += 1
    assert allowed >= 1
    assert blocked >= 1
    assert analysis_mode_for_profile(_school_full()) == "school"
