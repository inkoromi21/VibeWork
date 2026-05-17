"""Персональные советы с материалами."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.learning.personalized_advice import (
    _infer_track_from_plan,
    _rule_based_plan_advice,
    build_individual_advice,
)


def test_infer_track_devops() -> None:
    assert _infer_track_from_plan("DevOps и релизы") == "devops"


def test_rule_based_advice_has_materials_for_weak_prep() -> None:
    plan = {"id": "A", "name": "План A: Backend-разработка", "score_percent": 80}
    block = _rule_based_plan_advice(
        plan,
        preparation="weak",
        profile={"interest_sphere": "it_dev"},
        gap={"closing_skills": ["python", "git"]},
        sphere="it_dev",
        materials=[
            {
                "title": "Stepik Python",
                "url": "https://stepik.org/course/67",
                "kind": "курс",
                "provider": "stepik",
            }
        ],
        pain_id=None,
        priority=["python", "git"],
    )
    assert block["intro"]
    assert block["sections"]
    assert block["steps"]
    texts = " ".join(s.get("text", "") for s in block["steps"])
    assert "Шейна" not in texts and "Голланд" not in texts
    first = block["steps"][0]
    assert first.get("text")
    assert isinstance(first.get("materials"), list)


def test_build_individual_advice_structure() -> None:
    scenarios = {
        "plans": [
            {"id": "A", "name": "План A: DevOps и релизы", "score_percent": 70},
            {"id": "B", "name": "План B: Backend", "score_percent": 65},
        ]
    }
    out = build_individual_advice(
        scenarios=scenarios,
        preparation_level="medium",
        profile={"interest_sphere": "it_dev", "education_level": "student"},
        gap={"closing_skills": ["docker", "linux"]},
        interest="it_dev",
        learning_path=None,
        profile_summary="Сфера IT, студент.",
        user_id=None,
    )
    assert "by_plan" in out
    assert "A" in out["by_plan"]
    block_a = out["by_plan"]["A"]
    assert block_a.get("intro")
    assert block_a.get("sections")
    steps = block_a["steps"]
    assert steps and steps[0].get("text")
