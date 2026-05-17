"""Пояснение к индексу готовности."""

from __future__ import annotations

import sys
from pathlib import Path

_repo = Path(__file__).resolve().parents[2]
_backend = _repo / "miniapp" / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))


def test_build_readiness_insight_has_why_and_lists() -> None:
    from wibe_work.services.career_analysis import _build_readiness_insight

    axes = [
        {"label": "Самопознание", "value_percent": 62},
        {"label": "Люди", "value_percent": 48},
        {"label": "Структура", "value_percent": 55},
        {"label": "Баланс", "value_percent": 44},
    ]
    gap = {
        "overall_hp": 55,
        "closing_skills": ["Организация", "Коммуникации"],
    }
    out = _build_readiness_insight(51, "medium", axes, gap, {"best_avg_percent": 58})
    assert "51%" in out["why"]
    assert out["pros"]
    assert out["cons"]
    assert any("Организация" in c or "Люди" in c for c in out["cons"])
