"""Школьный learning_path — те же шаги и прогресс, что у карьеры."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.career_analysis import build_analysis_result
from wibe_work.services.role_confirmation import accept_role_confirmation, public_analysis_payload, wrap_fresh_analysis
from wibe_work.services.school_subject_resources import build_school_learning_path_payload


def _answers_15() -> list[dict]:
    return [{"question_id": i, "choice": "A"} for i in range(1, 16)]


def _school_profile() -> dict:
    return {
        "age": 16,
        "education_detail": "school_11",
        "main_sphere": "it_dev",
        "interest_spheres": '["it_dev"]',
        "favorite_subjects": '["math", "informatics"]',
        "exam_focus": "ege_11",
        "post_school_goal": "after_11_university",
        "preparation_level": "medium",
    }


def test_school_learning_path_has_subject_steps() -> None:
    profile = _school_profile()
    gap = {
        "bars": [{"label": "Математика (алгебра, логика)"}],
        "closing_skills": ["Информатика / программирование"],
    }
    lp = build_school_learning_path_payload(
        user_id=None,
        profile=profile,
        interest="it_dev",
        preparation_level="medium",
        scenarios={"best_plan_name": "Вариант A: 11 класс профиль"},
        gap=gap,
    )
    assert lp.get("path_id", "").startswith("school_")
    steps = lp.get("steps") or []
    assert len(steps) >= 3
    ids = {s["step_id"] for s in steps}
    assert "school_orient" in ids
    assert "sub_math" in ids
    assert "sub_informatics" in ids
    assert "school_sphere_probe" in ids
    assert all(s.get("title") and s.get("goal") for s in steps)
    assert lp["metrics"]["total_steps"] == len(steps)


def test_school_full_analysis_anydo_after_accept() -> None:
    profile = _school_profile()
    full = build_analysis_result(profile, {}, "it_dev", "11 класс", "medium", _answers_15())
    full = wrap_fresh_analysis(full, profile)
    full = accept_role_confirmation(full)
    pub = public_analysis_payload(full)
    assert pub["analysis_mode"] == "school"
    lp = pub.get("learning_path") or {}
    assert lp.get("path_id")
    assert len(lp.get("steps") or []) >= 3
    assert lp.get("metrics", {}).get("total_steps") == len(lp.get("steps") or [])
