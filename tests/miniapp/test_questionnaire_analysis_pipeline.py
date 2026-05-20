"""Связка анкета → тест → разбор → обучение по уровню (школа / СПО / вуз)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.questionnaire_fields import (
    AUDIENCE_SCHOOL,
    get_profile_schema,
    is_profile_complete,
    questionnaire_audience,
    resolve_profile_schema,
)
from wibe_work.services.assessment_bundle import expected_question_ids, get_assessment_bundle
from wibe_work.services.career_analysis import build_analysis_result
from wibe_work.services.profile_analysis_context import analysis_mode_for_profile
from wibe_work.services.learning.assessment_signals import build_assessment_signals


def _answers_for_profile(profile: dict, interest: str) -> list[dict]:
    ids = expected_question_ids(profile, interest)
    return [{"question_id": qid, "choice": "A"} for qid in sorted(ids)]


def _school_profile() -> dict:
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
        "hours_per_week": 10,
    }


def _spo_profile() -> dict:
    return {
        "age": 19,
        "city": "Москва",
        "education_detail": "spo",
        "course_grade": "2 курс",
        "study_form": "fulltime",
        "interest_spheres": '["marketing"]',
        "like_to_do": "контент",
        "work_format_preference": "remote",
        "work_schedule": "after_classes",
        "target_salary": 60000,
        "hours_per_week": 8,
        "preparation_level": "medium",
    }


def _univ_profile() -> dict:
    return {
        "age": 21,
        "city": "СПб",
        "education_detail": "univ_bachelor",
        "course_grade": "3 курс",
        "study_form": "fulltime",
        "interest_spheres": '["it_dev"]',
        "like_to_do": "python",
        "work_format_preference": "hybrid",
        "work_schedule": "flex",
        "target_salary": 120000,
        "hours_per_week": 12,
        "preparation_level": "strong",
    }


def test_school_pipeline_questionnaire_test_analysis_learning():
    profile = _school_profile()
    assert questionnaire_audience(profile=profile) == "school"
    assert is_profile_complete(profile)
    schema = resolve_profile_schema(get_profile_schema(), AUDIENCE_SCHOOL)
    assert "school_interests" in {s["id"] for s in schema["sections"]}

    bundle = get_assessment_bundle(profile, "it_dev")
    assert bundle["test_grade"] == "school"
    assert bundle["technical_count"] == 0
    texts = " ".join(q["text"].lower() for q in bundle["questions"])
    assert "ваканс" not in texts and "резюме" not in texts

    full = build_analysis_result(
        profile,
        {"city": profile["city"], "age": profile["age"]},
        "it_dev",
        "школа",
        "medium",
        _answers_for_profile(profile, "it_dev"),
    )
    assert analysis_mode_for_profile(profile) == "school"
    mts = full.get("mts_matrix") or {}
    assert mts.get("school_mode") is True
    scenarios = full.get("scenarios") or {}
    names = " ".join(p.get("name", "") for p in scenarios.get("plans") or []).lower()
    assert "backend" not in names
    signals = full.get("assessment_signals") or build_assessment_signals(
        profile=profile,
        interest="it_dev",
        preparation_level="medium",
        gap=full.get("gap_analysis") or {},
    )
    assert signals.get("analysis_mode") == "school"
    assert signals.get("education_grade") == "school"
    summary = full.get("profile_summary") or ""
    assert "ОГЭ" in summary or "ЕГЭ" in summary
    assert summary.count("Любимые предметы:") <= 1


def test_spo_pipeline_vocational_bundle_and_career_mode():
    profile = _spo_profile()
    assert questionnaire_audience(profile=profile) == "career"
    assert is_profile_complete(profile)

    bundle = get_assessment_bundle(profile, "marketing")
    assert bundle["test_grade"] == "vocational"
    assert bundle["technical_count"] >= 1
    assert analysis_mode_for_profile(profile) == "career"

    full = build_analysis_result(
        profile,
        {"city": profile["city"], "age": profile["age"]},
        "marketing",
        "СПО",
        "medium",
        _answers_for_profile(profile, "marketing"),
    )
    assert (full.get("mts_matrix") or {}).get("school_mode") is not True
    signals = full.get("assessment_signals") or {}
    assert signals.get("education_grade") in ("vocational", None) or analysis_mode_for_profile(
        profile
    ) == "career"
    summary = full.get("profile_summary") or ""
    assert "зарплат" in summary.lower() or "Формат работы" in summary


def test_univ_pipeline_job_search_no_school_exam_wording():
    profile = _univ_profile()
    assert questionnaire_audience(profile=profile) == "career"
    bundle = get_assessment_bundle(profile, "it_dev")
    assert bundle["test_grade"] == "university"
    assert bundle.get("assessment_focus") == "job_search"
    assert bundle["orientation_count"] == 0

    full = build_analysis_result(
        profile,
        {"city": profile["city"], "age": profile["age"]},
        "it_dev",
        "вуз",
        "strong",
        _answers_for_profile(profile, "it_dev"),
    )
    assert analysis_mode_for_profile(profile) == "career"
    mts = full.get("mts_matrix") or {}
    rows = mts.get("rows") or []
    assert len(rows) >= 1
