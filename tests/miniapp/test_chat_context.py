"""Контекст для ИИ-чата."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.chat_context import (
    build_comprehensive_chat_context,
    build_context_aware_fallback,
)


def test_comprehensive_context_includes_learning_and_advice() -> None:
    snap = {
        "readiness": {"value_percent": 50},
        "learning_path": {
            "title": "Путь",
            "metrics": {"coverage_percent": 10, "current_step_index": 0, "total_steps": 2},
            "steps": [
                {
                    "title": "Шаг 1",
                    "goal": "Цель",
                    "status": "in_progress",
                    "resources": [{"title": "Курс", "url": "https://example.com", "provider": "stepik"}],
                }
            ],
        },
        "individual_advice": {
            "by_plan": {
                "A": {
                    "priority_skills": ["python"],
                    "steps": [{"text": "Начните с курса", "materials": []}],
                }
            },
        },
        "scenarios": {"best_plan_id": "A", "plans": [{"id": "A", "name": "План A: Backend"}]},
    }
    ctx = build_comprehensive_chat_context(
        analysis_snap=snap, profile_snippet="Город: Кемерово"
    )
    assert "Кемерово" in ctx
    assert "Путь обучения" in ctx
    assert "Индивидуальные советы" in ctx
    assert "example.com" in ctx


def test_fallback_uses_narrative() -> None:
    text = build_context_aware_fallback(
        "привет",
        analysis_snap={"readiness": {"value_percent": 40}, "ai_narrative": "Фокус на backend."},
        profile_snippet="",
    )
    assert "backend" in text.lower() or "40" in text
