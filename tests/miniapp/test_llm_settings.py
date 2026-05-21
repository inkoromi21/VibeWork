"""Настройки LLM: облако vs локальный URL."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "miniapp" / "backend"))

from wibe_work.services.llm_client import _extract_assistant_text, get_llm_settings
from wibe_work.services.llm_health import build_llm_health_payload


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


def test_ollama_cloud_keeps_gpt_oss_model(monkeypatch) -> None:
    monkeypatch.setenv("USE_OLLAMA", "0")
    monkeypatch.setenv("CHAT_API_URL", "https://ollama.com/v1/chat/completions")
    monkeypatch.setenv("CHAT_API_KEY", "abc.fake.ollama")
    monkeypatch.setenv("CHAT_MODEL", "gpt-oss:120b-cloud")
    cfg = get_llm_settings()
    assert cfg is not None
    assert cfg[2] == "gpt-oss:120b-cloud"
    assert "ollama.com" in cfg[0]


def test_extract_assistant_text_reasoning_fallback() -> None:
    assert _extract_assistant_text({"content": "", "reasoning": "ок"}) == "ок"
    assert _extract_assistant_text({"content": "да"}) == "да"


def test_llm_health_payload_has_ok_field(monkeypatch) -> None:
    monkeypatch.setenv("USE_OLLAMA", "0")
    monkeypatch.setenv("CHAT_API_URL", "")
    monkeypatch.delenv("CHAT_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    out = build_llm_health_payload()
    assert "ok" in out
    assert out["ok"] is False


def test_zai_key_resolves_zai_url(monkeypatch) -> None:
    monkeypatch.setenv("USE_OLLAMA", "0")
    monkeypatch.setenv("CHAT_API_URL", "")
    monkeypatch.setenv("DEEPSEEK_API_URL", "")
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("CHAT_PROVIDER", raising=False)
    monkeypatch.setenv("CHAT_API_KEY", "abc.defghijklmnop")
    monkeypatch.setenv("CHAT_MODEL", "")
    cfg = get_llm_settings()
    assert cfg is not None
    assert "z.ai" in cfg[0]
