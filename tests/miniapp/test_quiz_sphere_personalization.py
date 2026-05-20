"""Техблок теста: вопросы по сфере, без IT-лексики для немедицинских сфер."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))
if str(_REPO / "website") not in sys.path:
    sys.path.insert(0, str(_REPO / "website"))

from wibe_work.services.aptitude_quiz_content_bridge import (
    fetch_technical_from_website,
    normalize_sphere_id,
)
from wibe_work.services.assessment_bundle import get_assessment_bundle


def _tech_blob(interest: str) -> str:
    profile = {"education_detail": "univ_bachelor", "course_grade": "2 курс"}
    bundle = get_assessment_bundle(profile, interest)
    parts = [str(q.get("text") or "") for q in bundle["technical"]]
    for q in bundle["technical"]:
        for o in q.get("options") or []:
            parts.append(str(o.get("label") or ""))
    return " ".join(parts).lower()


def test_normalize_legacy_medicine_web_key() -> None:
    assert normalize_sphere_id("поддержка_и_сервис") == "medicine"
    assert normalize_sphere_id("medicine") == "medicine"


def test_medicine_questions_not_it_pet_project() -> None:
    blob = _tech_blob("medicine")
    assert "пет" not in blob and "pet" not in blob
    assert any(k in blob for k in ("пациент", "медиц", "практик", "стаж"))


def test_medicine_via_legacy_web_interest_param() -> None:
    blob = _tech_blob("поддержка_и_сервис")
    assert "пет" not in blob and "pet" not in blob
    assert "пациент" in blob or "медиц" in blob


def test_fetch_technical_medicine_from_website_bank() -> None:
    qs = fetch_technical_from_website("medicine")
    assert qs and len(qs) >= 10
    blob = " ".join(
        str(q.get("text") or "")
        + " "
        + " ".join(str(o.get("label") or "") for o in q.get("options") or [])
        for q in qs
    ).lower()
    assert "пет" not in blob
    assert "пациент" in blob or "стажиров" in blob
