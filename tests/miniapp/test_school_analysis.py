"""Разбор для школьников: маршруты обучения, не карьерные треки."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.assessment_bundle import get_assessment_bundle
from wibe_work.services.profile_analysis_context import analysis_mode_for_profile
from wibe_work.services.career_analysis_school import (
    build_school_gap_analysis,
    pick_school_path_plans,
    school_education_hints,
)
from wibe_work.services.school_subject_resources import build_school_curated_learning_cards


def _school_profile():
    return {
        "age": 15,
        "city": "Казань",
        "education_detail": "school_8_11",
        "course_grade": "9 класс",
        "interest_spheres": '["it_dev"]',
        "like_to_do": "программирование",
        "main_sphere": "it_dev",
    }


def test_school_mode_and_paths_not_job_titles():
    profile = _school_profile()
    assert analysis_mode_for_profile(profile) == "school"
    bundle = get_assessment_bundle(profile, "it_dev")
    assert bundle["technical_count"] == 0

    axes = [
        {"key": "structure_mastery", "label": "Структура", "value_percent": 70},
        {"key": "people_service", "label": "Люди", "value_percent": 55},
    ]
    scenarios = pick_school_path_plans(profile, "it_dev", axes, 42)
    plans = scenarios["plans"]
    names = " ".join(p["name"] for p in plans).lower()
    assert "план a:" not in names
    assert "backend" not in names
    assert any(x in names for x in ("колледж", "11 класс", "спо", "вуз", "9 класс"))

    top = scenarios["best_plan_name"]
    gap = build_school_gap_analysis(profile, "it_dev", top, axes, 42)
    assert gap["bars"]
    assert any("матем" in b["label"].lower() or "информ" in b["label"].lower() for b in gap["bars"])

    mts = school_education_hints(profile, "it_dev", scenarios)
    assert mts.get("school_mode") is True
    assert mts["rows"]


def test_school_curated_links_fipi_and_subjects():
    profile = _school_profile()
    gap = {
        "bars": [{"label": "Математика (алгебра, логика)"}],
        "closing_skills": ["Информатика / программирование"],
    }
    cards = build_school_curated_learning_cards(profile, "it_dev", gap)
    assert cards[0]["url"].startswith("https://fipi.ru")
    urls = " ".join(c["url"] for c in cards)
    assert "ege.sdamgia.ru" in urls
    assert "kpolyakov.spb.ru" in urls or "informatics.msk.ru" in urls
    assert "math100.ru" in urls or "ege.sdamgia.ru/math" in urls
