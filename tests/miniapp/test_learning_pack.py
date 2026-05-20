"""Паритет полей обучения с сайтом."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.learning_pack import build_learning_extras, normalize_preparation_level
from wibe_work.services.quiz_web_bundle import quiz_bundle_for_web


def test_normalize_preparation_ru() -> None:
    assert normalize_preparation_level("средний") == "medium"
    assert normalize_preparation_level("strong") == "strong"


def test_quiz_web_bundle_matches_track() -> None:
    profile = {"education_detail": "school_8_11", "course_grade": "9 класс", "main_sphere": "it_dev"}
    pack = quiz_bundle_for_web(profile, "IT")
    assert pack.get("track_id") == "school_grade9"
    # Школа 9 класс: без технического блока по сфере, только профориентация + карьера
    assert len(pack.get("questions") or []) == 0
    assert len(pack.get("personality_questions") or []) >= 4
    assert pack.get("modules")


def test_learning_extras_keys() -> None:
    gap = {"overall_hp": 55, "bars": [], "headline": "x", "closing_skills": []}
    scenarios = {"plans": [], "best_plan_name": "IT"}
    out = build_learning_extras(
        profile={"age": 20, "main_sphere": "it_dev"},
        interest="it_dev",
        preparation_level="medium",
        scenarios=scenarios,
        gap=gap,
        eff_interest="it_dev",
    )
    assert "learning_path_detail" in out
    assert "growth_stages_rich" in out
    assert out["learning_path_detail"] == out["learning_path"]
