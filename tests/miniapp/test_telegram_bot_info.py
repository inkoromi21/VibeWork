"""Тесты resolve username бота для Login Widget."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services import telegram_bot_info as tbi


@pytest.fixture(autouse=True)
def reset_telegram_bot_cache():
    tbi._cached = None
    tbi._resolved = False
    yield
    tbi._cached = None
    tbi._resolved = False


def test_explicit_username_from_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_USERNAME", "@MyBot")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    assert tbi.get_telegram_bot_username() == "MyBot"


def test_getme_when_only_token(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_USERNAME", raising=False)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:ABC")
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"result": {"username": "vibeworks_bot"}}
    with patch("wibe_work.services.telegram_bot_info.requests.get", return_value=mock_resp) as get:
        assert tbi.get_telegram_bot_username() == "vibeworks_bot"
        get.assert_called_once()
        assert tbi.get_telegram_bot_username() == "vibeworks_bot"
        assert get.call_count == 1


def test_none_without_token_or_username(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_USERNAME", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    assert tbi.get_telegram_bot_username() is None
