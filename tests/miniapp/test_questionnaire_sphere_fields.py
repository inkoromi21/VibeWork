"""Анкета: поля по сферам интересов (без IT-вопросов медику)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.questionnaire_fields import (
    AUDIENCE_CAREER,
    get_profile_schema,
    resolve_profile_schema,
)


def _field_ids(schema: dict) -> set[str]:
    out: set[str] = set()
    for sec in schema.get("sections") or []:
        for f in sec.get("fields") or []:
            out.add(f["id"])
    return out


def _field_by_id(schema: dict, fid: str) -> dict | None:
    for sec in schema.get("sections") or []:
        for f in sec.get("fields") or []:
            if f.get("id") == fid:
                return f
    return None


def test_medicine_hides_programming_skills() -> None:
    master = get_profile_schema()
    resolved = resolve_profile_schema(
        master,
        AUDIENCE_CAREER,
        {"interest_spheres": '["medicine"]', "education_detail": "univ_bachelor"},
    )
    ids = _field_ids(resolved)
    assert "programming_skills" not in ids
    assert "languages" in ids
    proj = _field_by_id(resolved, "experience_projects")
    assert proj and "практик" in (proj.get("label") or "").lower()


def test_it_dev_shows_programming() -> None:
    master = get_profile_schema()
    resolved = resolve_profile_schema(
        master,
        AUDIENCE_CAREER,
        {"interest_spheres": '["it_dev"]', "education_detail": "univ_bachelor"},
    )
    assert "programming_skills" in _field_ids(resolved)


def test_medicine_and_it_shows_both_skill_blocks() -> None:
    master = get_profile_schema()
    resolved = resolve_profile_schema(
        master,
        AUDIENCE_CAREER,
        {
            "interest_spheres": '["medicine", "it_dev"]',
            "education_detail": "univ_bachelor",
        },
    )
    ids = _field_ids(resolved)
    assert "programming_skills" in ids
    proj = _field_by_id(resolved, "experience_projects")
    assert proj and (
        "стаж" in (proj.get("placeholder") or "").lower()
        or "клинич" in (proj.get("placeholder") or "").lower()
    )
