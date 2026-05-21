"""Промпты LLM зависят от уровня образования (школа / СПО / вуз)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.llm_prompts import (
    GRADE_SCHOOL,
    GRADE_VOCATIONAL,
    GRADE_UNIVERSITY,
    advice_json_system_for_grade,
    build_chat_system_prompt,
    coach_chat_system_for_grade,
    infer_education_grade_from_text,
    narrative_system_for_grade,
    select_chat_addenda,
)


def test_coach_system_differs_by_grade() -> None:
    school = coach_chat_system_for_grade(GRADE_SCHOOL).lower()
    voc = coach_chat_system_for_grade(GRADE_VOCATIONAL).lower()
    uni = coach_chat_system_for_grade(GRADE_UNIVERSITY).lower()
    assert "школьник" in school or "8–11" in school
    assert "спо" in voc or "колледж" in voc
    assert "ваканс" in uni or "стажиров" in uni
    assert school != uni


def test_narrative_system_school_and_vocational() -> None:
    school = narrative_system_for_grade("school", GRADE_SCHOOL).lower()
    voc = narrative_system_for_grade("career", GRADE_VOCATIONAL).lower()
    uni = narrative_system_for_grade("career", GRADE_UNIVERSITY).lower()
    assert "школьник" in school or "8–11" in school
    assert "спо" in voc or "колледж" in voc
    assert uni != voc
    for blob in (school, voc, uni):
        assert "только русский" in blob
        assert "420" in blob or "420 знаков" in blob


def test_polish_analysis_narrative_truncates() -> None:
    from wibe_work.services.llm_prompts import polish_analysis_narrative

    long = "А. " * 200
    out = polish_analysis_narrative(long, max_chars=100)
    assert len(out) <= 101


def test_select_addenda_school_blocks_jobs_topic() -> None:
    add = select_chat_addenda(
        "как откликаться на hh.ru",
        {},
        {"readiness": {"value_percent": 50}},
        education_grade=GRADE_SCHOOL,
    )
    blob = " ".join(add).lower()
    assert "школьник" in blob
    assert any("подработк" in a or "школьник" in a for a in add)
    assert not any("тема: вакансии" in a.lower() for a in add)


def test_build_chat_system_includes_grade_layer() -> None:
    sys_p = build_chat_system_prompt([], education_grade=GRADE_VOCATIONAL)
    assert "СПО" in sys_p or "колледж" in sys_p


def test_infer_grade_from_summary_text() -> None:
    assert infer_education_grade_from_text("Уровень для разбора: Школьный уровень") == GRADE_SCHOOL
    assert infer_education_grade_from_text("СПО / колледж — траектория") == GRADE_VOCATIONAL
    assert infer_education_grade_from_text("вуз / выпускник") == GRADE_UNIVERSITY


def test_advice_json_system_by_grade() -> None:
    s = advice_json_system_for_grade(GRADE_SCHOOL).lower()
    assert "школьник" in s
    assert "огэ" in s or "поступ" in s or "предмет" in s
