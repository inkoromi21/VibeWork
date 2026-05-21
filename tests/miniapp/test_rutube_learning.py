"""Rutube video search for learning paths."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.learning.rutube import (
    _course_score,
    rutube_search_for_learning,
    video_search_preferred,
)


def test_course_score_prefers_course_title() -> None:
    assert _course_score(
        "Полный курс Python с нуля",
        "python backend курс",
        track="backend",
    ) > _course_score(
        "Интервью про Python",
        "python backend курс",
        track="backend",
    )


@patch("wibe_work.services.learning.rutube._get_json")
def test_rutube_search_parses_video_url(mock_get) -> None:
    mock_get.return_value = {
        "results": [
            {
                "id": "abc123" * 2 + "ab",
                "title": "Курс Python backend с нуля",
                "description": "Уроки",
                "video_url": "https://rutube.ru/video/" + "abc123" * 2 + "ab/",
            }
        ]
    }
    cards = rutube_search_for_learning(
        "python backend",
        limit=2,
        prefer_course=False,
        track="backend",
    )
    assert len(cards) == 1
    assert cards[0]["provider"] == "rutube"
    assert "rutube.ru/video/" in cards[0]["url"]
    assert cards[0]["kind"] in ("курс", "видео")


@patch("wibe_work.services.learning.rutube.rutube_search_for_learning")
def test_video_search_prefers_rutube_first(mock_ru) -> None:
    mock_ru.return_value = [{"title": "R", "url": "https://rutube.ru/video/x/", "provider": "rutube"}]
    out = video_search_preferred("python", limit=1, track="backend")
    assert out and out[0]["provider"] == "rutube"
