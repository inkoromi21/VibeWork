"""Маршрутизация профориентационных модулей по образованию и классу."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.assessment_bundle import get_assessment_bundle
from wibe_work.services.assessment_routing import (
    TRACK_SCHOOL_GRADE9,
    TRACK_SCHOOL_SENIOR,
    TRACK_UNIVERSITY,
    parse_course_grade,
    resolve_assessment_track,
    track_modules,
)


def test_parse_course_grade_school() -> None:
    assert parse_course_grade("10 класс")["school_class"] == 10
    assert parse_course_grade("11 кл")["school_class"] == 11
    assert parse_course_grade("2 курс")["course_year"] == 2


def test_track_school_grade9() -> None:
    p = {"education_detail": "school_8_11", "course_grade": "9 класс", "age": 15}
    assert resolve_assessment_track(p) == TRACK_SCHOOL_GRADE9
    assert "klimov" in track_modules(TRACK_SCHOOL_GRADE9)


def test_track_school_senior() -> None:
    p = {"education_detail": "school_8_11", "course_grade": "11 класс"}
    assert resolve_assessment_track(p) == TRACK_SCHOOL_SENIOR
    assert "holland" in track_modules(TRACK_SCHOOL_SENIOR)


def test_track_university() -> None:
    p = {"education_detail": "univ_bachelor", "course_grade": "2 курс"}
    assert resolve_assessment_track(p) == TRACK_UNIVERSITY


def test_bundle_counts() -> None:
    school = get_assessment_bundle(
        {"education_detail": "school_8_11", "course_grade": "10 класс"},
        "it_dev",
    )
    orient_n = school["orientation_count"]
    career_n = school["personality_count"]
    assert school["technical_count"] == 0
    assert school["test_grade"] == "school"
    assert school["total_count"] == orient_n + career_n
    assert len(school["questions"]) == school["total_count"]
    assert len(school["weights_matrix"]) == school["total_count"]
    assert school["technical"] == []
    mods = school.get("modules") or []
    assert not any(m.get("id") == "sphere" for m in mods)

    uni = get_assessment_bundle({"education_detail": "univ_bachelor", "course_grade": "1 курс"}, "it_dev")
    assert uni["track_id"] == TRACK_UNIVERSITY
    assert uni["orientation_count"] == 0
    assert uni["technical_count"] == 10
    assert uni["career_count"] == 5
    assert uni["total_count"] == 15
    assert len(uni["questions"]) == uni["total_count"]
    assert uni["assessment_focus"] == "job_search"
