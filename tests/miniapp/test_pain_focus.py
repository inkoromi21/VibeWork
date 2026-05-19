"""Фокус по ситуации: персонализация под анкету и разбор."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.career_analysis import _pain_focus


def test_pain_low_confidence_uses_profile_and_gap() -> None:
    profile = {
        "primary_pain": "pain_low_confidence",
        "city": "Кемерово",
        "like_to_do": "программирование на Python, помогаю одногруппникам с кодом",
        "main_sphere": "it_dev",
        "interest_spheres": '["it_dev"]',
        "work_format_preference": "remote",
        "preparation_level": "weak",
    }
    gap = {"overall_hp": 55, "closing_skills": ["Организация", "Коммуникации"]}
    scenarios = {"best_plan_name": "План A: Backend", "best_avg_percent": 58}
    axes = [
        {"label": "Самопознание", "value_percent": 62},
        {"label": "Люди", "value_percent": 48},
    ]
    out = _pain_focus(
        profile,
        gap=gap,
        scenarios=scenarios,
        axes=axes,
        readiness_percent=51,
        top_track="backend",
    )
    assert out is not None
    assert "ничего не умею" in out["label"].lower()
    assert out["summary"]
    assert "Python" in out["summary"] or "программирование" in out["summary"]
    assert "51" in out["summary"]
    assert out["tips"]
    assert not any("/career/" in t for t in out["tips"])
