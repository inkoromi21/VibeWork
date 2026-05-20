"""Настройки LLM: облако vs локальный URL."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.llm_client import get_llm_settings


def test_localhost_url_uses_ollama_even_if_use_ollama_zero(monkeypatch) -> None:
    monkeypatch.setenv("USE_OLLAMA", "0")
    monkeypatch.setenv("CHAT_API_URL", "http://127.0.0.1:11434/v1/chat/completions")
    monkeypatch.setenv("CHAT_API_KEY", "1d6b5ead.fake.zai.key")
    monkeypatch.setenv("CHAT_MODEL", "gpt-oss:20b")
    cfg = get_llm_settings()
    assert cfg is not None
    url, key, model = cfg
    assert "127.0.0.1" in url
    assert key == ""
    assert model == "gpt-oss:20b"


def test_cloud_mode_without_localhost(monkeypatch) -> None:
    monkeypatch.setenv("USE_OLLAMA", "0")
    monkeypatch.setenv("CHAT_API_URL", "")
    monkeypatch.setenv("CHAT_API_KEY", "gsk_test_key_example")
    monkeypatch.setenv("CHAT_MODEL", "")
    monkeypatch.delenv("CHAT_PROVIDER", raising=False)
    cfg = get_llm_settings()
    assert cfg is not None
    url, key, model = cfg
    assert "groq.com" in url
    assert key == "gsk_test_key_example"
    assert model == "llama-3.1-8b-instant"


def test_zai_key_resolves_zai_url(monkeypatch) -> None:
    monkeypatch.setenv("USE_OLLAMA", "0")
    monkeypatch.setenv("CHAT_API_URL", "")
    monkeypatch.setenv("CHAT_API_KEY", "abc.defghijklmnop")
    monkeypatch.setenv("CHAT_MODEL", "")
    cfg = get_llm_settings()
    assert cfg is not None
    assert "z.ai" in cfg[0]
