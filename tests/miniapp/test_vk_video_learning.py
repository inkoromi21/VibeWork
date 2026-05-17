"""VK Video API for learning paths."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.learning.vk_video import (
    vk_search_for_learning,
    vk_video_search,
)


@patch("wibe_work.services.learning.vk_video.VK_ACCESS_TOKEN", "test_token")
@patch("wibe_work.services.learning.vk_video._vk_call")
def test_vk_video_search_parses_items(mock_call) -> None:
    mock_call.return_value = {
        "count": 1,
        "items": [
            {
                "owner_id": -100,
                "id": 456,
                "title": "Полный курс Python с нуля",
                "description": "Уроки",
            }
        ],
    }
    cards = vk_video_search("python", limit=2)
    assert len(cards) == 1
    assert cards[0]["provider"] == "vk"
    assert cards[0]["url"] == "https://vk.com/video-100_456"
    mock_call.assert_called_once()
    assert mock_call.call_args[0][0] == "video.search"


@patch("wibe_work.services.learning.vk_video.VK_ACCESS_TOKEN", "")
def test_vk_video_search_without_token() -> None:
    assert vk_video_search("python") == []


@patch("wibe_work.services.learning.vk_video.VK_ACCESS_TOKEN", "test_token")
@patch("wibe_work.services.learning.vk_video.vk_video_search")
def test_vk_search_for_learning(mock_search) -> None:
    mock_search.return_value = [
        {"title": "Курс", "url": "https://vk.com/video-1_2", "provider": "vk"}
    ]
    out = vk_search_for_learning("python курс", limit=1)
    assert len(out) == 1
    assert out[0]["provider"] == "vk"
