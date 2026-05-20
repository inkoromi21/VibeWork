"""Профориентационный тест: 10 тех. по сфере + 5 личностных (сфера × уровень)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.questionnaire_fields import get_profile_schema
from wibe_work.services.aptitude_quiz import (
    PERSONALITY_COUNT,
    TECHNICAL_COUNT,
    get_quiz_bundle,
    get_questions_for_interest,
)
from wibe_work.services.aptitude_quiz_grading import compute_quiz_grade


def test_quiz_bundle_structure() -> None:
    profile = {"education_detail": "univ_bachelor", "course_grade": "3 курс"}
    bundle = get_quiz_bundle("it_dev", profile=profile)
    assert bundle["technical_count"] == TECHNICAL_COUNT
    assert bundle["personality_count"] == PERSONALITY_COUNT
    assert len(bundle["technical"]) == TECHNICAL_COUNT
    assert len(bundle["personality"]) == PERSONALITY_COUNT
    orient = int(bundle.get("orientation_count") or 0)
    assert len(bundle["questions"]) == orient + TECHNICAL_COUNT + PERSONALITY_COUNT
    core_ids = [q["id"] for q in bundle["technical"]] + [q["id"] for q in bundle["personality"]]
    assert core_ids == list(range(orient + 1, orient + 16))
    for q in bundle["technical"]:
        assert q.get("block") == "technical"
    for q in bundle["personality"]:
        assert q.get("block") in ("career", "personality")


def test_flat_list_matches_bundle() -> None:
    profile = {"education_detail": "school_8_11", "course_grade": "8 класс"}
    bundle = get_quiz_bundle("sales", profile=profile)
    flat = get_quiz_bundle("sales", profile=profile)["questions"]
    assert flat == bundle["questions"]
    assert len(flat) == bundle["total_count"]


def test_grade_from_education_detail() -> None:
    assert compute_quiz_grade({"education_detail": "school_8_11"}) == "school"
    assert compute_quiz_grade({"education_detail": "spo"}) == "vocational"
    assert compute_quiz_grade({"education_detail": "graduate"}) == "university"


def test_personality_text_differs_by_grade() -> None:
    school = get_quiz_bundle("other", "school")["personality"]
    uni = get_quiz_bundle("other", "university")["personality"]
    assert school[0]["text"] != uni[0]["text"]


def test_personality_q12_varies_by_sphere_track() -> None:
    tech = get_quiz_bundle("it_dev", "university")["personality"]
    creative = get_quiz_bundle("design", "university")["personality"]
    q12_tech = next(q for q in tech if q["id"] == 12)
    q12_creative = next(q for q in creative if q["id"] == 12)
    assert q12_tech["text"] != q12_creative["text"]


def test_all_interest_spheres_have_full_quiz() -> None:
    schema = get_profile_schema()
    sphere_ids = [o["id"] for o in (schema.get("interest_spheres") or [])]
    for sid in sphere_ids:
        bundle = get_quiz_bundle(sid, "vocational")
        assert len(bundle["technical"]) == TECHNICAL_COUNT, sid
        assert len(bundle["personality"]) == PERSONALITY_COUNT, sid
