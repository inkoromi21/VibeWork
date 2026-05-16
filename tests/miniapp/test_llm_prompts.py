"""Промпты карьерного чата: ситуации и сборка контекста."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.llm_prompts import (
    build_analysis_context_for_chat,
    build_chat_system_prompt,
    build_chat_user_prompt,
    select_chat_addenda,
)


def test_addenda_no_analysis_and_pain() -> None:
    add = select_chat_addenda(
        "как найти работу без опыта",
        {"primary_pain": "pain_no_exp"},
        None,
    )
    assert any("разбора ещё нет" in a for a in add)
    assert any("нет опыта" in a.lower() for a in add)


def test_addenda_jobs_topic() -> None:
    add = select_chat_addenda(
        "как откликаться на hh.ru",
        {},
        {"readiness": {"value_percent": 70}},
    )
    assert any("ваканс" in a.lower() or "hh" in a.lower() for a in add)


def test_build_user_prompt_includes_blocks() -> None:
    snap = {
        "profile_summary": "Возраст: 20; сфера: it_dev",
        "readiness": {"value_percent": 65},
        "ai_narrative": "Фокус на разработку.",
        "scenarios": {"plans": [{"id": "A", "name": "План A: Python", "score_percent": 80}]},
    }
    ctx = build_analysis_context_for_chat(snap)
    assert "готовности" in ctx
    assert "Python" in ctx
    prompt = build_chat_user_prompt(
        [{"role": "user", "content": "С чего начать?"}],
        profile_snippet="Город: Москва",
        analysis_snap=snap,
    )
    assert "Анкета" in prompt
    assert "Разбор и тест" in prompt
    assert "С чего начать" in prompt


def test_system_prompt_joins_addenda() -> None:
    sys_p = build_chat_system_prompt(["ДОПОЛНИТЕЛЬНО (тест)"])
    assert "карьерный консультант" in sys_p.lower()
    assert "ДОПОЛНИТЕЛЬНО (тест)" in sys_p
