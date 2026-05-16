"""Вызов chat/completions (OpenAI-совместимый API: Groq, DeepSeek, OpenAI и т.д.)."""

from __future__ import annotations

import json
import logging
import os
import threading
from functools import lru_cache
from typing import List, Literal, Optional, Tuple

import requests

from wibe_work.services.llm_prompts import (
    DEFAULT_GENERIC_SYSTEM,
    build_chat_system_prompt,
    build_chat_user_prompt,
    select_chat_addenda,
)

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


@lru_cache(maxsize=1)
def get_llm_settings() -> Optional[Tuple[str, str, str]]:
    """
    (url, api_key, model). Провайдер с POST .../v1/chat/completions.

    Облако: CHAT_API_KEY (или DEEPSEEK_*/OPENAI_*), CHAT_API_URL, CHAT_MODEL.
    Локальный URL без ключа: если в CHAT_API_URL указан 127.0.0.1 / localhost — ключ не обязателен.
    """
    chat_key = os.getenv("CHAT_API_KEY", "").strip()
    ds_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    oa_key = os.getenv("OPENAI_API_KEY", "").strip()
    key = chat_key or ds_key or oa_key

    url = (
        os.getenv("CHAT_API_URL", "").strip()
        or os.getenv("DEEPSEEK_API_URL", "").strip()
    )
    if not url:
        base = os.getenv("DEEPSEEK_BASE_URL", "").strip().rstrip("/")
        if base and "api.openai.com" not in base:
            url = f"{base}/v1/chat/completions"
        elif oa_key and not ds_key:
            url = "https://api.openai.com/v1/chat/completions"
        else:
            url = "https://api.deepseek.com/v1/chat/completions"

    local = "127.0.0.1" in url or "localhost" in url

    model = (
        os.getenv("CHAT_MODEL", "").strip()
        or os.getenv("DEEPSEEK_MODEL", "").strip()
        or os.getenv("OPENAI_MODEL", "").strip()
    )
    if not model:
        if "api.openai.com" in url:
            model = "gpt-4o-mini"
        elif local:
            model = "llama3.2"
        else:
            model = "deepseek-chat"

    if local:
        key = chat_key

    if not key and not local:
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


def _mock_career_chat_reply(_last_user: str) -> str:
    return (
        "Опираясь на сохранённый разбор: уточните в анкете город, желаемый формат работы и что сейчас важнее — "
        "обучение, стабильный доход или баланс. Для ответов ИИ настройте LLM в .env и перезапустите API "
        "(см. подсказку ниже)."
    )


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

    addenda = select_chat_addenda(last_user, profile, analysis_snap)
    system_prompt = build_chat_system_prompt(addenda)
    user_prompt = build_chat_user_prompt(
        messages,
        profile_snippet=profile_snippet,
        analysis_snap=analysis_snap,
        directions_hint=directions_hint,
        legacy_context_summary=context_summary,
    )
    mock = _mock_career_chat_reply(last_user or "ваш вопрос")

    if not llm_configured():
        hint = (
            "Задайте CHAT_API_KEY и CHAT_API_URL (или DEEPSEEK_* / OPENAI_*) в .env. Перезапустите API после правок."
        )
        return (mock, "mock", hint)

    out, api_notice = fetch_llm_completion(
        user_prompt,
        max_tokens=900,
        temperature=0.25,
        system_prompt=system_prompt,
    )
    if out:
        return out, "llm", None
    logger.warning("Чат: LLM не вернул ответ — заглушка.")
    return mock, "mock", api_notice


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
