"""Фильтр релевантности учебных материалов."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.learning.material_relevance import (
    build_learning_search_query,
    filter_materials_heuristic,
    heuristic_material_score,
    is_entertainment_or_sport,
)
from wibe_work.services.learning.video_scoring import course_score


def test_football_video_rejected() -> None:
    card = {
        "title": "Разбор матча Реал — Барселона",
        "description": "Голы и моменты",
        "provider": "vk",
    }
    assert is_entertainment_or_sport(card)
    assert heuristic_material_score(card, track="backend") == 0
    assert course_score(card["title"], "python backend курс", description=card["description"]) < 0


def test_backend_accepts_python_course() -> None:
    card = {
        "title": "Python для начинающих — полный курс",
        "description": "Уроки программирования",
        "provider": "vk",
    }
    assert heuristic_material_score(card, track="backend") >= 8
    assert filter_materials_heuristic([card], track="backend")


def test_backend_rejects_figma() -> None:
    card = {
        "title": "Figma UI UX дизайн с нуля",
        "description": "Макеты и прототипы",
        "provider": "stepik",
    }
    assert heuristic_material_score(card, track="backend") == 0


def test_vague_query_replaced_by_track() -> None:
    q = build_learning_search_query("карьера обучение", track="backend")
    assert "python" in q.lower() or "backend" in q.lower()


def test_off_topic_education_feed_rejected() -> None:
    card = {
        "title": "Полный курс кулинарии для начинающих",
        "description": "Уроки готовки",
        "provider": "vk",
    }
    assert heuristic_material_score(card, track="backend") == 0


def test_course_score_skips_irrelevant_title() -> None:
    assert (
        course_score(
            "Футбол. Обзор тура",
            "python курс",
            description="Матч",
            track="backend",
        )
        < 6
    )
