"""Курсы и материалы строго привязаны к сфере, треку и разбору теста."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.learning.assessment_signals import (
    build_assessment_signals,
    infer_track_from_plan_name,
    resource_allowed,
    resolve_learning_track,
)
from wibe_work.services.learning.catalog import pick_path, pick_catalog_resources_for_signals
from wibe_work.services.learning.engine import build_learning_for_analysis
from wibe_work.services.learning.personalized_advice import build_individual_advice


def test_marketing_plan_yields_marketing_track() -> None:
    scenarios = {
        "best_plan_name": "План A: Digital-маркетинг и CRM",
        "plans": [{"id": "A", "name": "План A: Digital-маркетинг и CRM", "score_percent": 78}],
    }
    track, src = resolve_learning_track(
        sphere="marketing",
        scenarios=scenarios,
        answers=None,
        axes=[],
    )
    assert track == "marketing"
    assert src == "best_scenario_plan"


def test_it_backend_from_technical_answers() -> None:
    answers = [{"question_id": i, "choice": "A"} for i in range(1, 11)]
    scenarios = {"inferred_profession": {"track_id": "backend", "label": "Backend"}}
    track, src = resolve_learning_track(
        sphere="it_dev",
        scenarios=scenarios,
        answers=answers,
        axes=[],
    )
    assert track == "backend"
    assert src == "inferred_profession"


def test_hubspot_not_in_it_backend_catalog() -> None:
    signals = build_assessment_signals(
        profile={"main_sphere": "it_dev", "preparation_level": "medium"},
        interest="it_dev",
        preparation_level="medium",
        scenarios={"inferred_profession": {"track_id": "backend"}},
        gap={"closing_skills": ["python", "git"]},
        axes=[{"key": "structure_mastery", "value_percent": 80}],
        answers=[{"question_id": i, "choice": "A"} for i in range(1, 11)],
    )
    cards = pick_catalog_resources_for_signals(signals, limit=12)
    titles = " ".join(c.get("title", "") for c in cards).lower()
    assert "hubspot" not in titles
    assert any("python" in titles or "backend" in titles or "roadmap" in titles for _ in [0])


def test_marketing_path_not_general_with_hubspot_only() -> None:
    signals = build_assessment_signals(
        profile={"main_sphere": "marketing"},
        interest="marketing",
        preparation_level="weak",
        scenarios={
            "best_plan_name": "План A: SMM и контент",
            "plans": [{"id": "A", "name": "План A: SMM и контент", "score_percent": 70}],
        },
        gap={"closing_skills": ["marketing"]},
        axes=[],
    )
    path = pick_path("marketing", signals.get("track"), "weak", signals=signals)
    assert path is not None
    assert path.get("id") == "marketing_junior"


def test_learning_pack_respects_sphere() -> None:
    scenarios = {
        "inferred_profession": {"track_id": "backend"},
        "plans": [
            {"id": "A", "name": "План A: Backend-разработка", "score_percent": 85},
        ],
        "best_plan_name": "План A: Backend-разработка",
    }
    pack = build_learning_for_analysis(
        user_id=None,
        profile={"main_sphere": "it_dev", "preparation_level": "medium"},
        interest="it_dev",
        preparation_level="medium",
        scenarios=scenarios,
        gap={"closing_skills": ["python"]},
        axes=[{"key": "structure_mastery", "value_percent": 75}],
        answers=[{"question_id": i, "choice": "A"} for i in range(1, 11)],
    )
    lp = pack.get("learning_path") or {}
    assert lp.get("path_id") == "it_dev_backend_junior"
    assert lp.get("track") == "backend"
    cards = pack.get("learning") or []
    blob = " ".join(
        (c.get("title") or "") + (c.get("description") or "") for c in cards
    ).lower()
    assert "hubspot" not in blob


def test_advice_materials_match_plan_track() -> None:
    scenarios = {
        "plans": [
            {"id": "A", "name": "План A: DevOps и релизы", "score_percent": 70},
        ],
        "best_plan_name": "План A: DevOps и релизы",
    }
    out = build_individual_advice(
        scenarios=scenarios,
        preparation_level="medium",
        profile={"main_sphere": "it_dev", "education_level": "student"},
        gap={"closing_skills": ["docker", "linux"]},
        interest="it_dev",
        learning_path=None,
        user_id=None,
    )
    block = out["by_plan"]["A"]
    assert block.get("track") == "devops"
    mats = []
    for st in block.get("steps") or []:
        mats.extend(st.get("materials") or [])
    if mats:
        blob = " ".join((m.get("title") or "") for m in mats).lower()
        assert "hubspot" not in blob


def test_infer_track_from_plan_devops() -> None:
    assert infer_track_from_plan_name("DevOps и CI/CD") == "devops"
