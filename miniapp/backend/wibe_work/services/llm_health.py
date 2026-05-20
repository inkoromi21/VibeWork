"""Единый ответ GET /api/health/llm (миниаппа и website API в одном процессе)."""

from __future__ import annotations

import os

from wibe_work.services.llm_client import (
    _is_local_llm_url,
    fetch_llm_completion,
    get_llm_settings,
)


def build_llm_health_payload() -> dict:
    raw_url = (os.getenv("CHAT_API_URL", "").strip())
    cfg = get_llm_settings()
    use_ollama = (os.getenv("USE_OLLAMA", "").strip().lower() in ("1", "true", "yes", "on")) or (
        bool(raw_url) and _is_local_llm_url(raw_url)
    )
    out: dict = {
        "llm_configured": cfg is not None,
        "ok": False,
        "use_ollama": use_ollama,
        "chat_api_url_env": raw_url or None,
    }
    if not cfg:
        out["hint"] = (
            "Задайте CHAT_API_KEY и CHAT_API_URL (Ollama Cloud: https://ollama.com/v1/chat/completions, "
            "Groq: api.groq.com). Без 127.0.0.1 при облаке. Перезапустите API."
        )
        return out
    url, _, model = cfg
    out["model"] = model
    out["resolved_url"] = url.split("?")[0]
    local = _is_local_llm_url(url)
    out["endpoint_local"] = local
    use_ollama_env = os.getenv("USE_OLLAMA", "").strip().lower() in ("0", "false", "no", "off")
    if local and use_ollama_env and raw_url and _is_local_llm_url(raw_url):
        out["config_warning"] = (
            "CHAT_API_URL указывает на Ollama (localhost) — локальная модель. "
            "Для Ollama Cloud: https://ollama.com/v1/chat/completions и USE_OLLAMA=0."
        )
    if local:
        out["hint"] = "Локальный LLM: запустите Ollama (ollama serve) и модель из CHAT_MODEL."
    elif "ollama.com" in url.lower():
        out["hint"] = "Ollama Cloud: ключ с ollama.com/settings/keys, модель с суффиксом -cloud."
    # gpt-oss и reasoning-модели: короткий лимит даёт пустой content.
    text, notice = fetch_llm_completion(
        "Скажи одно слово: ок",
        max_tokens=64,
        temperature=0,
        system_prompt="Ответь одним словом на русском.",
    )
    out["ok"] = bool(text)
    if notice:
        out["notice"] = notice
    elif not text:
        out["notice"] = "Модель не ответила; см. лог API."
    return out
