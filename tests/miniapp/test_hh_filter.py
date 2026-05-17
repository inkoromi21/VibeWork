"""Поиск hh.ru: запрос из анкеты v2 и сфер."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.hh_filter import (
    _build_search_text,
    _hh_search_phrase,
    _map_employment,
    _map_experience,
    build_hh_query_params,
    hh_search_phrase_for_it_track,
)
from wibe_work.services.recommendations import run_recommendations


def test_sphere_id_maps_to_hh_phrase() -> None:
    assert "разработчик" in _hh_search_phrase("IT / разработка", [], ["it_dev"])
    assert "аналитик" in _hh_search_phrase("Аналитика и данные", ["SQL"], ["data"])


def test_main_sphere_drives_direction() -> None:
    profile = {
        "main_sphere": "finance",
        "like_to_do": "рисовать",
        "interest_spheres": '["design"]',
    }
    rec = run_recommendations(profile, [])
    assert rec["primary_direction"] == "Финансы и экономика"


def test_build_query_uses_profile_fields() -> None:
    profile = {
        "city": "Москва",
        "main_sphere": "it_dev",
        "programming_skills": "Python React",
        "work_format_preference": "remote",
        "target_salary": 120000,
        "primary_pain": "pain_no_exp",
        "preparation_level": "weak",
    }
    rec = run_recommendations(profile, [])
    params = build_hh_query_params(profile, rec, "1", [])
    assert params["experience"] == "noExperience"
    assert params.get("schedule") == "remote"
    assert "python" in str(params.get("text", "")).lower() or "разработчик" in str(
        params.get("text", "")
    ).lower()
    assert params.get("salary") == 120000


def test_search_text_from_sphere_not_slug() -> None:
    profile = {"main_sphere": "hr_edu", "like_to_do": "люди"}
    rec = run_recommendations(profile, [])
    text = _build_search_text(profile, rec, [])
    assert "hr" in text.lower() or "рекрут" in text.lower()
    assert "hr_edu" not in text


def test_map_experience_school_detail() -> None:
    assert (
        _map_experience({"education_detail": "school_11", "preparation_level": "medium"})
        == "noExperience"
    )


def test_map_employment_not_from_hours_only() -> None:
    assert _map_employment({"hours_per_week": 15, "work_schedule": "after_classes"}) is None
    assert _map_employment({"work_schedule": "weekends"}) == "part"


def test_hh_phrase_for_backend_not_generic_programmist() -> None:
    phrase = hh_search_phrase_for_it_track("backend", ["Python"])
    assert "python" in phrase.lower()
    assert "backend" in phrase.lower()
    assert phrase != "разработчик программист"


def test_it_query_no_search_field_name() -> None:
    profile = {
        "main_sphere": "it_dev",
        "city": "Кемерово",
        "primary_pain": "pain_no_exp",
    }
    rec = run_recommendations(profile, [])
    params = build_hh_query_params(profile, rec, "47", [], use_profile_salary=False)
    assert "search_field" not in params
    assert params.get("employment") is None
