"""Этапы роста с привязкой к советам и обучению."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.learning.growth_stages import build_growth_stages


def test_growth_stages_links_advice_and_path() -> None:
    advice = {
        "by_plan": {
            "A": {
                "title": "План A: Backend",
                "steps": [
                    {"text": "Начните с Python курса", "materials": []},
                    {"text": "Резюме под backend", "materials": []},
                ],
            }
        }
    }
    learning_path = {
        "steps": [
            {"title": "Основы Python", "resources": [{"title": "Stepik", "url": "https://stepik.org/1"}]},
            {"title": "Git", "resources": [{"title": "Git branching", "url": "https://learngitbranching.js.org/"}]},
            {"title": "Пет-проект", "resources": []},
        ]
    }
    scenarios = {
        "best_plan_id": "A",
        "plans": [{"id": "A", "name": "План A: Backend", "score_percent": 80}],
    }
    stages = build_growth_stages(
        interest="it_dev",
        eff_interest="it_dev",
        preparation_level="weak",
        readiness_percent=42,
        profile={"interest_sphere": "it_dev"},
        gap={"closing_skills": ["python", "git"]},
        scenarios=scenarios,
        individual_advice=advice,
        learning_path=learning_path,
    )
    assert len(stages) == 3
    assert stages[0]["materials"]
    assert stages[0]["plan"]
    assert stages[0]["checklist"]
    assert stages[1]["continues_from"]
    assert "42%" in stages[0]["intro"]
    assert "трио" not in " ".join(stages[0].get("focus_tags") or []).lower()
    assert "голланд" not in stages[2]["body"].lower()
