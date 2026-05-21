"""VK Video search for learning paths."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.learning.adapters import run_dynamic_adapter
from wibe_work.services.learning.vk_video import video_search_for_learning, vk_video_search


@patch("wibe_work.services.learning.vk_video.VK_ACCESS_TOKEN", "test-token")
@patch("wibe_work.services.learning.vk_video._vk_call")
def test_vk_video_search_parses_items(mock_vk) -> None:
    mock_vk.return_value = {
        "items": [
            {
                "owner_id": -1,
                "id": 42,
                "title": "Python для начинающих — полный курс",
                "description": "Уроки программирования",
            }
        ]
    }
    cards = vk_video_search("python курс", limit=3, track="backend")
    assert len(cards) == 1
    assert cards[0]["provider"] == "vk"
    assert "vk.com/video" in cards[0]["url"]


@patch("wibe_work.services.learning.vk_video.VK_ACCESS_TOKEN", "")
def test_video_adapter_empty_without_token() -> None:
    out = run_dynamic_adapter({"adapter": "video", "query": "python", "limit": 2})
    assert out == []


@patch("wibe_work.services.learning.vk_video.VK_ACCESS_TOKEN", "test-token")
@patch("wibe_work.services.learning.vk_video.vk_search_for_learning")
@patch("wibe_work.services.llm_client.llm_configured", return_value=False)
@patch(
    "wibe_work.services.learning.material_relevance.filter_materials_for_context",
    side_effect=lambda cards, **_: cards,
)
def test_video_search_for_learning_uses_vk(_filter, _llm, mock_vk) -> None:
    mock_vk.return_value = [
        {
            "title": "Python курс",
            "url": "https://vk.com/video-1_42",
            "provider": "vk",
        }
    ]
    out = video_search_for_learning("python", track="backend", limit=2)
    assert out and out[0]["provider"] == "vk"
