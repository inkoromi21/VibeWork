"""Краткий вывод: человеческий текст без «План A»."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.career_analysis import _mock_ai_narrative


def test_mock_narrative_plain_language() -> None:
    profile = {
        "city": "Кемерово",
        "like_to_do": "Python и помощь одногруппникам",
        "interest_spheres": '["it_dev"]',
        "preparation_level": "weak",
    }
    scenarios = {
        "plans": [
            {"id": "A", "name": "План A: Метрики и контроль качества", "score_percent": 55},
            {"id": "B", "name": "План B: Backend-разработка (API, сервер, базы данных)", "score_percent": 72},
            {"id": "C", "name": "План C: DevOps и CI/CD", "score_percent": 48},
        ]
    }
    axes = [
        {"key": "structure_mastery", "label": "Структура и экспертиза", "value_percent": 68},
        {"key": "people_service", "label": "Люди и служение", "value_percent": 45},
    ]
    text = _mock_ai_narrative(
        profile,
        "it_dev",
        "weak",
        scenarios,
        axes,
        0,
        readiness_percent=51,
        gap={"closing_skills": ["Организация"]},
    )
    assert "План A:" not in text
    assert "План B:" not in text
    assert "Backend" in text or "бэкенд" in text.lower()
    assert "51" in text
    assert "Python" in text or "Кемерово" in text
