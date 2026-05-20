"""Профориентация: формулировки по уровню образования и сфере."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.assessment_bundle import get_assessment_bundle
from wibe_work.services.assessment_routing import uses_job_search_assessment


def _orientation_texts(bundle: dict) -> str:
    parts = []
    for q in bundle.get("orientation") or []:
        parts.append(str(q.get("text") or ""))
        for o in q.get("options") or []:
            parts.append(str(o.get("label") or ""))
    return "\n".join(parts).lower()


def _career_texts(bundle: dict) -> str:
    parts = []
    for q in bundle.get("career") or bundle.get("personality") or []:
        parts.append(str(q.get("text") or ""))
        for o in q.get("options") or []:
            parts.append(str(o.get("label") or ""))
    return "\n".join(parts).lower()


def test_university_uses_job_search_not_proforientation() -> None:
    profile = {"education_detail": "univ_bachelor", "course_grade": "2 курс"}
    assert uses_job_search_assessment(profile)
    bundle = get_assessment_bundle(profile, "medicine")
    assert bundle["assessment_focus"] == "job_search"
    assert bundle["orientation_count"] == 0
    assert len(bundle["orientation"]) == 0
    assert bundle["technical_count"] == 10
    assert bundle["career_count"] == 5
    assert bundle["total_count"] == 15


def test_university_career_block_about_role_not_field() -> None:
    bundle = get_assessment_bundle(
        {"education_detail": "univ_bachelor", "course_grade": "3 курс"},
        "medicine",
    )
    text = _career_texts(bundle)
    assert "должност" in text or "ваканс" in text or "позици" in text
    assert "кем стать" not in text
    assert "одноклассник" not in text


def test_university_no_orientation_modules() -> None:
    bundle = get_assessment_bundle(
        {"education_detail": "univ_master", "course_grade": "1 курс"},
        "it_dev",
    )
    assert _orientation_texts(bundle) == ""
    mods = {m.get("id") for m in bundle.get("modules") or []}
    assert "holland" not in mods
    assert "jovaisa" not in mods
    assert "sphere" in mods
    assert "career" in mods


def test_school_track_keeps_proforientation() -> None:
    profile = {"education_detail": "school_8_11", "course_grade": "10 класс"}
    assert not uses_job_search_assessment(profile)
    bundle = get_assessment_bundle(profile, "it_dev")
    assert bundle["assessment_focus"] == "proforientation"
    assert bundle["orientation_count"] > 0
    text = _orientation_texts(bundle)
    assert "класс" in text or "одноклассник" in text or "школьн" in text
