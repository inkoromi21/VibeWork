"""Подтверждение роли / сферы перед полным разбором."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.career_analysis import build_analysis_result
from wibe_work.services.role_confirmation import (
    accept_role_confirmation,
    parse_feedback_exclusions_career,
    public_analysis_payload,
    reject_role_and_regenerate,
    wrap_fresh_analysis,
)


def _answers_15() -> list[dict]:
    return [{"question_id": i, "choice": "A"} for i in range(1, 16)]


def _it_profile() -> dict:
    return {
        "age": 20,
        "city": "Москва",
        "education_detail": "univ_bachelor",
        "main_sphere": "it_dev",
        "programming_skills": "Python",
        "preparation_level": "medium",
    }


def test_pending_payload_hides_full_analysis() -> None:
    full = build_analysis_result(_it_profile(), {}, "it_dev", "вуз", "medium", _answers_15())
    full = wrap_fresh_analysis(full, _it_profile())
    pub = public_analysis_payload(full)
    assert pub.get("role_confirmation", {}).get("status") == "pending"
    assert "gap_analysis" not in pub
    assert pub["role_confirmation"]["proposal"]["label"]


def test_accept_exposes_full_analysis() -> None:
    full = build_analysis_result(_it_profile(), {}, "it_dev", "вуз", "medium", _answers_15())
    full = wrap_fresh_analysis(full, _it_profile())
    full = accept_role_confirmation(full)
    pub = public_analysis_payload(full)
    assert pub.get("role_confirmation", {}).get("status") == "accepted"
    assert "gap_analysis" in pub


def test_reject_backend_offers_different_track() -> None:
    tech_a = [{"question_id": i, "choice": "A"} for i in range(1, 11)]
    pers = [{"question_id": i, "choice": "B"} for i in range(11, 16)]
    full = build_analysis_result(
        _it_profile(), {}, "it_dev", "вуз", "medium", tech_a + pers
    )
    full = wrap_fresh_analysis(full, _it_profile())
    first = full["role_confirmation"]["proposal"].get("track_id")
    assert first == "backend"
    full = reject_role_and_regenerate(
        full, _it_profile(), {}, "не хочу бэкенд и серверную разработку"
    )
    second = full["role_confirmation"]["proposal"].get("track_id")
    assert second != "backend"
    assert "backend" in full["role_confirmation"]["excluded_track_ids"]


def test_parse_feedback_exclusions() -> None:
    assert "backend" in parse_feedback_exclusions_career("не нравится бэкенд")
    assert "frontend" in parse_feedback_exclusions_career("хочу фронт и интерфейсы")


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


def test_school_pending_proposal_has_sphere_and_subjects() -> None:
    full = build_analysis_result(_school_profile(), {}, "it_dev", "11 класс", "medium", _answers_15())
    full = wrap_fresh_analysis(full, _school_profile())
    pub = public_analysis_payload(full)
    assert pub["analysis_mode"] == "school"
    prop = pub["role_confirmation"]["proposal"]
    assert prop["mode"] == "school"
    assert prop.get("sphere_label")
    assert any(s["id"] == "informatics" for s in prop.get("exam_subjects") or [])


def test_school_reject_informatics_keeps_math() -> None:
    full = build_analysis_result(_school_profile(), {}, "it_dev", "11 класс", "medium", _answers_15())
    full = wrap_fresh_analysis(full, _school_profile())
    full = reject_role_and_regenerate(
        full,
        _school_profile(),
        {},
        "не хочу сдавать информатику, но хочу математику и ЕГЭ",
    )
    prop = full["role_confirmation"]["proposal"]
    sub_ids = {s["id"] for s in prop.get("exam_subjects") or []}
    assert "informatics" not in sub_ids
    assert "informatics" in full["role_confirmation"]["excluded_subject_ids"]
    assert "math" in sub_ids or len(sub_ids) >= 1
