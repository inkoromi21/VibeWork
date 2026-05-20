"""Вызов chat/completions (OpenAI-совместимый API: Groq, DeepSeek, OpenAI и т.д.)."""

from __future__ import annotations

import json
import logging
import os
import threading
from typing import List, Literal, Optional, Tuple

import requests

from wibe_work.services.chat_context import (
    build_comprehensive_chat_context,
    build_context_aware_fallback,
)
from wibe_work.services.llm_prompts import (
    DEFAULT_GENERIC_SYSTEM,
    build_chat_system_prompt,
    build_chat_user_prompt,
    select_chat_addenda,
)
from wibe_work.services.profile_analysis_context import education_grade as profile_education_grade

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 45.0
# Локальный совместимый сервер (127.0.0.1) — первый ответ может быть долгим.
LOCAL_LLM_DEFAULT_TIMEOUT = 120.0

_tls_http = threading.local()


def _http_session() -> requests.Session:
    s = getattr(_tls_http, "session", None)
    if s is None:
        s = requests.Session()
        _tls_http.session = s
    return s


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return default


def _looks_like_ollama_model(name: str) -> bool:
    low = (name or "").lower()
    return any(
        x in low
        for x in (
            "gpt-oss",
            "llama",
            "mistral",
            "qwen",
            "deepseek-r1",
            ":",
            "ollama",
        )
    )


def _cloud_url_for_provider(provider: str, key: str) -> str:
    p = (provider or "").strip().lower()
    if p == "groq":
        return "https://api.groq.com/openai/v1/chat/completions"
    if p in ("openai", "gpt"):
        return "https://api.openai.com/v1/chat/completions"
    if p in ("zai", "z.ai", "glm"):
        return "https://api.z.ai/api/paas/v4/chat/completions"
    if key.startswith("gsk_"):
        return "https://api.groq.com/openai/v1/chat/completions"
    if key.startswith("sk-or-"):
        return "https://api.openai.com/v1/chat/completions"
    if "." in key and not key.startswith("sk-"):
        return "https://api.z.ai/api/paas/v4/chat/completions"
    return "https://api.deepseek.com/v1/chat/completions"


def _default_model_for_url(url: str) -> str:
    u = url.lower()
    if "groq.com" in u:
        return "llama-3.1-8b-instant"
    if "api.openai.com" in u:
        return "gpt-4o-mini"
    if "z.ai" in u or "bigmodel.cn" in u:
        return "glm-4-flash"
    if _is_local_llm_url(url):
        return "llama3.2"
    return "deepseek-chat"


def _resolve_chat_url(key: str, explicit_url: str, *, use_local: bool) -> str:
    url = (explicit_url or "").strip()
    if use_local:
        return url or "http://127.0.0.1:11434/v1/chat/completions"
    if url and not _is_local_llm_url(url):
        return url
    provider = os.getenv("CHAT_PROVIDER", "").strip()
    return _cloud_url_for_provider(provider, key)


def _resolve_chat_model(url: str, explicit_model: str) -> str:
    model = (
        (explicit_model or "").strip()
        or os.getenv("DEEPSEEK_MODEL", "").strip()
        or os.getenv("OPENAI_MODEL", "").strip()
    )
    if _is_local_llm_url(url):
        return model or _default_model_for_url(url)
    if not model or _looks_like_ollama_model(model):
        return _default_model_for_url(url)
    return model


def _use_local_llm(explicit_url: str) -> bool:
    """Локальный Ollama: USE_OLLAMA=1 или CHAT_API_URL на 127.0.0.1/localhost."""
    if _is_local_llm_url(explicit_url):
        return True
    return _env_flag("USE_OLLAMA", default=False)


def get_llm_settings() -> Optional[Tuple[str, str, str]]:
    """
    (url, api_key, model). Провайдер с POST .../v1/chat/completions.

    Локально (бесплатно): CHAT_API_URL=http://127.0.0.1:11434/... и/или USE_OLLAMA=1.
    CHAT_API_KEY для Ollama не нужен. Облако: USE_OLLAMA=0 и облачный URL + ключ (Groq и т.д.).
    """
    chat_key = os.getenv("CHAT_API_KEY", "").strip()
    ds_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    oa_key = os.getenv("OPENAI_API_KEY", "").strip()
    key = chat_key or ds_key or oa_key

    explicit_url = (
        os.getenv("CHAT_API_URL", "").strip()
        or os.getenv("DEEPSEEK_API_URL", "").strip()
    )
    use_local = _use_local_llm(explicit_url)
    url = _resolve_chat_url(key, explicit_url, use_local=use_local)
    local = _is_local_llm_url(url)

    explicit_model = os.getenv("CHAT_MODEL", "").strip()
    model = _resolve_chat_model(url, explicit_model)

    if local:
        # Ollama не требует Bearer; ключ в .env не отправляем в облако по ошибке.
        return (url, "", model)

    if not key:
        return None
    return (url, key, model)


def llm_configured() -> bool:
    return get_llm_settings() is not None


def _is_local_llm_url(url: str) -> bool:
    u = url.lower()
    return "127.0.0.1" in u or "localhost" in u


def _http_timeout_seconds(url: str) -> float:
    if _is_local_llm_url(url):
        return float(os.getenv("LLM_LOCAL_TIMEOUT", str(LOCAL_LLM_DEFAULT_TIMEOUT)))
    return float(os.getenv("LLM_REQUEST_TIMEOUT", str(REQUEST_TIMEOUT)))


def fetch_llm_completion(
    user_prompt: str,
    *,
    max_tokens: int = 500,
    temperature: float = 0.6,
    system_prompt: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Синхронный запрос. Возвращает (текст, подсказка пользователю при сбое)."""
    cfg = get_llm_settings()
    if not cfg:
        return None, None
    url, api_key, model = cfg
    timeout = _http_timeout_seconds(url)
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    sys_default = DEFAULT_GENERIC_SYSTEM
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt or sys_default},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    try:
        r = _http_session().post(url, headers=headers, json=body, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        raw = data["choices"][0]["message"].get("content")
        if raw is None:
            logger.warning("LLM пустой content: %s", str(data)[:400])
            return None, "Модель вернула пустой ответ. Попробуйте ещё раз."
        text = str(raw).strip()
        if not text:
            return None, "Модель вернула пустой ответ. Попробуйте ещё раз."
        return text, None
    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else 0
        logger.warning("LLM HTTP %s: %s", code, (e.response.text or "")[:500] if e.response else "")
        if code == 404 and _is_local_llm_url(url):
            notice = (
                f"Локальная модель «{model}» не найдена (404). Проверьте CHAT_MODEL и что сервер LLM запущен."
            )
        elif code == 402:
            notice = "На счёте провайдера нет средств (402). Пополните баланс или смените ключ."
        elif code == 401:
            notice = "Ключ API отклонён (401). Проверьте CHAT_API_KEY в .env."
        elif code == 403:
            notice = (
                "Доступ запрещён (403). Для Groq нужен ключ gsk_… с console.groq.com; "
                "если ключ DeepSeek (sk-…) — укажите CHAT_API_URL=https://api.deepseek.com/v1/chat/completions "
                "и CHAT_MODEL=deepseek-chat."
            )
        elif code == 429:
            notice = "Слишком много запросов (429). Подождите и повторите."
        else:
            notice = f"Сервис модели вернул ошибку {code}. Смотрите лог сервера."
        return None, notice
    except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError, TypeError) as e:
        logger.warning("LLM запрос не удался: %s", e)
        if _is_local_llm_url(url):
            return (
                None,
                "Нет ответа от локального LLM. Проверьте CHAT_API_URL и что сервер слушает этот адрес.",
            )
        return None, "Не удалось связаться с API модели. Проверьте интернет и настройки URL."


def career_coach_chat_reply(
    messages: List[dict],
    context_summary: str = "",
    directions_hint: str = "",
    profile_snippet: str = "",
    *,
    profile: Optional[dict] = None,
    analysis_snap: Optional[dict] = None,
) -> Tuple[str, Literal["llm", "mock"], Optional[str]]:
    last_user = ""
    for m in reversed(messages):
        if (m.get("role") or "") == "user":
            last_user = str(m.get("content", "")).strip()
            break
    if not last_user and messages:
        last_user = str(messages[-1].get("content", "")).strip()

    context_pack = build_comprehensive_chat_context(
        analysis_snap=analysis_snap,
        profile_snippet=profile_snippet,
        directions_hint=directions_hint or context_summary,
    )
    grade = profile_education_grade(profile or {})
    addenda = select_chat_addenda(
        last_user, profile, analysis_snap, education_grade=grade
    )
    system_prompt = build_chat_system_prompt(
        addenda, context_pack=context_pack, education_grade=grade
    )
    user_prompt = build_chat_user_prompt(
        messages,
        profile_snippet="",  # анкета уже в context_pack (system)
        analysis_snap=analysis_snap,
        directions_hint="",
        legacy_context_summary=context_summary if not analysis_snap else "",
    )
    fallback = build_context_aware_fallback(
        last_user or "ваш вопрос",
        analysis_snap=analysis_snap,
        profile_snippet=profile_snippet,
    )

    if not llm_configured():
        hint = (
            "ИИ не настроен: задайте CHAT_API_KEY и CHAT_API_URL в корневом .env "
            "(Groq: api.groq.com, ключ gsk_…). Перезапустите API."
        )
        return (fallback + " " + hint, "mock", hint)

    out, api_notice = fetch_llm_completion(
        user_prompt,
        max_tokens=1100,
        temperature=0.35,
        system_prompt=system_prompt,
    )
    if out:
        return out, "llm", None
    logger.warning("Чат: LLM не вернул ответ — контекстная заглушка. %s", api_notice)
    notice = api_notice or "Модель не ответила; проверьте CHAT_API_KEY и лимиты провайдера."
    return fallback, "mock", notice


def chat_completion(
    messages: List[dict],
    context_summary: str,
    directions_hint: str,
    profile_snippet: str = "",
) -> str:
    """Обратная совместимость: только текст ответа."""
    text, _, _ = career_coach_chat_reply(
        messages, context_summary, directions_hint, profile_snippet
    )
    return text
