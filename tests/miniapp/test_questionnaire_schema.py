"""Схема анкеты v2: поля совпадают с ProfileData."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.api_schemas import ProfileData
from wibe_work.questionnaire_fields import get_profile_schema


def _collect_field_ids(schema: dict) -> set[str]:
    out: set[str] = set()
    for sec in schema.get("sections") or []:
        for f in sec.get("fields") or []:
            if f.get("type") != "hidden":
                out.add(f["id"])
    return out


def test_profile_schema_version_and_completion() -> None:
    schema = get_profile_schema()
    assert schema.get("version") == 2
    assert schema.get("wizard") is True
    comp = schema.get("completion") or {}
    assert "age" in comp.get("required", [])
    assert comp.get("any_of")


def test_schema_field_ids_in_profile_data() -> None:
    allowed = set(ProfileData.model_fields.keys())
    for fid in _collect_field_ids(get_profile_schema()):
        assert fid in allowed, f"unknown field {fid!r} for ProfileData"


def test_interest_spheres_multiselect() -> None:
    schema = get_profile_schema()
    found = False
    for sec in schema["sections"]:
        for f in sec.get("fields") or []:
            if f["id"] == "interest_spheres":
                assert f["type"] == "multiselect"
                assert f.get("max_select") == 5
                found = True
    assert found
