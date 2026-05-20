"""Фильтр опыта вакансий (годы → коды hh.ru)."""

from __future__ import annotations

import sys
from pathlib import Path

_WEBSITE = Path(__file__).resolve().parents[2] / "website"
sys.path.insert(0, str(_WEBSITE))

from app.hh_client import _experience_params, normalize_job_experience  # noqa: E402


def test_normalize_hh_codes() -> None:
    assert normalize_job_experience("between1And3") == "between1And3"
    assert normalize_job_experience("moreThan6") == "moreThan6"
    assert normalize_job_experience("") is None
    assert normalize_job_experience("any") is None


def test_legacy_grade_maps_to_hh() -> None:
    assert normalize_job_experience("джуниор") == "between1And3"
    assert normalize_job_experience("стажер") == "noExperience"


def test_experience_params_single_code() -> None:
    assert _experience_params("between3And6") == [("experience", "between3And6")]
