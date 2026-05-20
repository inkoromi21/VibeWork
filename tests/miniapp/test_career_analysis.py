"""Разбор после теста: структура, gap, анкета."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.career_analysis import (
    build_analysis_result,
    infer_it_track_from_answers,
    public_analysis_payload,
)


def _answers_15() -> list[dict]:
    return [{"question_id": i, "choice": "A"} for i in range(1, 16)]


def test_analysis_has_gap_and_pain() -> None:
    profile = {
        "age": 19,
        "city": "Москва",
        "education_level": "студент вуза (бакалавр)",
        "primary_pain": "pain_no_exp",
        "like_to_do": "программирование python",
        "main_sphere": "it_dev",
        "preparation_level": "weak",
    }
    full = build_analysis_result(
        profile,
        {"city": "Москва", "age": 19},
        "it_dev",
        "вуз",
        "weak",
        _answers_15(),
    )
    pub = public_analysis_payload(full)
    assert "gap_analysis" in pub
    assert len(pub["gap_analysis"]["bars"]) == 5
    assert pub["pain_focus"] and pub["pain_focus"]["label"]
    assert len(pub["weekly_roadmap"]) >= 2
    assert "программирование" in full["profile_summary"].lower() or "python" in full["profile_summary"].lower()
    assert len(pub["style_radar"]["axes"]) == 4


def test_it_backend_track_from_technical_answers() -> None:
    tech_a = [{"question_id": i, "choice": "A"} for i in range(1, 11)]
    pers = [{"question_id": i, "choice": "B"} for i in range(11, 16)]
    assert infer_it_track_from_answers(tech_a) == "backend"
    profile = {
        "age": 20,
        "city": "Кемерово",
        "education_detail": "univ_bachelor",
        "main_sphere": "it_dev",
        "programming_skills": "Python Django",
        "preparation_level": "medium",
    }
    full = build_analysis_result(
        profile, {}, "it_dev", "вуз", "medium", tech_a + pers
    )
    scenarios = full.get("scenarios") or {}
    inf = scenarios.get("inferred_profession") or {}
    assert inf.get("track_id") == "backend"
    assert "Backend" in str(inf.get("label") or "")
    best = str(scenarios.get("best_plan_name") or "").lower()
    assert "backend" in best or "бэкенд" in best
    pub = public_analysis_payload(full)
    assert pub.get("inferred_profession", {}).get("label")
    mts = pub.get("mts_matrix", {}).get("rows") or []
    assert len(mts) >= 3
    names = " ".join(str(r.get("role_name") or "") for r in mts).lower()
    assert "backend" in names or "бэкенд" in names
    assert "закуп" not in names


def test_public_payload_omits_internal_keys() -> None:
    full = build_analysis_result({}, {}, "other", "—", "medium", _answers_15())
    pub = public_analysis_payload(full)
    assert "profile_summary" not in pub
    assert "directions_hint" not in pub
    assert "learning_path_detail" in pub
    assert "growth_stages_rich" in pub
