"""LLM: OpenAI-совместимый chat/completions (DeepSeek, OpenAI, Ollama, …) и заглушки."""

from __future__ import annotations

import json
import logging
import os
from typing import List, Literal, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 45.0
# Первый прогон локальной модели может занять минуту — для Ollama по умолчанию дольше.
OLLAMA_DEFAULT_TIMEOUT = 120.0


def ollama_mode_enabled() -> bool:
    """Режим локальной Ollama: ключ облака не нужен."""
    v = os.getenv("USE_OLLAMA", "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    return os.getenv("LLM_BACKEND", "").strip().lower() == "ollama"


def _ollama_chat_url() -> str:
    raw = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").strip().rstrip("/")
    if "/v1/chat/completions" in raw:
        return raw if raw.startswith("http") else f"http://{raw}"
    if not raw.startswith("http"):
        raw = f"http://{raw}"
    return f"{raw}/v1/chat/completions"


def _ollama_model() -> str:
    return (
        os.getenv("OLLAMA_MODEL", "").strip()
        or os.getenv("CHAT_MODEL", "").strip()
        or "llama3.2"
    )


def get_llm_settings() -> Optional[Tuple[str, str, str]]:
    """
    (url, api_key, model). Любой провайдер с POST .../v1/chat/completions.

    Ollama (рекомендуется для разработки без облака):
      USE_OLLAMA=1
      OLLAMA_HOST=http://127.0.0.1:11434   # опционально
      OLLAMA_MODEL=llama3.2                 # имя модели из `ollama list`

    Либо без USE_OLLAMA: CHAT_API_URL=http://127.0.0.1:11434/v1/chat/completions — ключ не обязателен.
    """
    if ollama_mode_enabled():
        return (_ollama_chat_url(), os.getenv("OLLAMA_API_KEY", "").strip(), _ollama_model())

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
        return float(os.getenv("LLM_LOCAL_TIMEOUT", str(OLLAMA_DEFAULT_TIMEOUT)))
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
    sys_default = (
        "Ты внешний карьерный консультант для молодёжи 14–30, не работодатель. "
        "Не используй «в нашей компании», «мы нанимаем». "
        "Весь ответ строго на русском: ни одного предложения на китайском, английском или другом языке "
        "(кроме имён брендов/технологий при необходимости). Не дублируй тот же смысл на двух языках. "
        "3–7 предложений, конкретика. Без HTML."
    )
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
        r = requests.post(url, headers=headers, data=json.dumps(body), timeout=timeout)
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
                f"Ollama: модель «{model}» не найдена (404). В терминале: ollama pull {model} "
                "и проверьте OLLAMA_MODEL в .env."
            )
        elif code == 402:
            notice = "На счёте провайдера нет средств (402). Пополните баланс или смените ключ."
        elif code == 401:
            notice = "Ключ API отклонён (401). Для Ollama задайте USE_OLLAMA=1 — ключ не нужен."
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
                "Нет ответа от Ollama. Запущено ли приложение Ollama, порт 11434? Команда проверки: curl http://127.0.0.1:11434/api/tags",
            )
        return None, "Не удалось связаться с API модели. Проверьте интернет и настройки URL."


_CAREER_CHAT_SYSTEM = """Ты карьерный консультант для молодёжи 14–30 в России. Пишешь одну связную реплику пользователю.

КРИТИЧНО — язык (нарушение недопустимо):
- Весь текст ответа только на русском. Ни одного предложения, слогана или «перефразирования для ясности» на китайском, английском, японском и т.п.
- Запрещено дублировать один и тот же смысл на двух языках (например, сначала по-русски, потом та же мысль по-китайски или по-английски).
- Запрещены вставки переводчика, двуязычные блоки и любой метатекст не на русском (включая «перефразирую на другом языке для ясности»).
- Исключение: отдельные имена брендов, API, инструментов (Docker, Kubernetes, SQL) — коротко, без целых фраз на английском.

Роль и тон:
- Ты не из компании пользователя и не работодатель. Не пиши «в нашей компании», «у нас нанимаем».
- Не переводи фразы пользователю «для обучения»; не объясняй, как сказать по-другому — только прямой совет и вопросы консультанта.
- Отвечай на последнее сообщение пользователя; не выдумывай лишний small talk.

Содержание:
- Опирайся на «Контекст разбора», «Направления» (A, B, C) и «Анкета (уже заполнено)», если они переданы.
- Не переспрашивай город, формат работы и приоритет (обучение/деньги/баланс), если они уже есть в анкете.
- По короткому «Привет»: если в анкете этих полей ещё нет — мягко попроси город, формат работы и приоритет; если уже есть — не дублируй.
- По целям: один фокус на месяц (навык + маленький проект), при необходимости напомни про блок «Прогресс за неделю» в анкете.

Формат: 6–12 предложений, связный текст. Без HTML, без маркированных списков из одних эмодзи."""


def _mock_career_chat_reply(_last_user: str) -> str:
    return (
        "Опираясь на сохранённый разбор: выберите один фокус на месяц (навык + маленький проект) "
        "и обновляйте в анкете блок «Прогресс за неделю». По теме «Привет»: если в анкете ещё нет — "
        "уточните город, формат работы и что важнее: обучение, деньги или баланс. "
        "Для ответов ИИ настройте LLM в .env и перезапустите API (см. подсказку ниже)."
    )


def career_coach_chat_reply(
    messages: List[dict],
    context_summary: str,
    directions_hint: str,
    profile_snippet: str = "",
) -> Tuple[str, Literal["llm", "mock"], Optional[str]]:
    last_user = ""
    for m in reversed(messages):
        if (m.get("role") or "") == "user":
            last_user = str(m.get("content", "")).strip()
            break
    if not last_user and messages:
        last_user = str(messages[-1].get("content", "")).strip()

    parts: List[str] = []
    if context_summary.strip():
        parts.append("Контекст разбора:\n" + context_summary[:1800])
    if directions_hint.strip():
        parts.append("Направления:\n" + directions_hint[:500])
    if (profile_snippet or "").strip():
        parts.append("Анкета (уже заполнено):\n" + profile_snippet.strip()[:900])
    transcript = "\n".join(
        f"{m.get('role', 'user')}: {str(m.get('content', ''))[:900]}" for m in messages[-10:]
    )
    user_tail = (
        "\n\nПоследнее сообщение пользователя (ответь только на него):\n"
        f"«{last_user[:2000]}»"
    )
    user_prompt = "\n\n".join(parts + [f"История диалога:\n{transcript}", user_tail])
    mock = _mock_career_chat_reply(last_user or "ваш вопрос")

    if not llm_configured():
        hint = (
            "Для локальной Ollama: USE_OLLAMA=1, OLLAMA_MODEL=<модель>, запущенный Ollama и ollama pull. "
            "Для облака: CHAT_API_KEY или DEEPSEEK_API_KEY в .env. Перезапустите API после правок."
        )
        return (mock, "mock", hint)

    out, api_notice = fetch_llm_completion(
        user_prompt,
        max_tokens=900,
        temperature=0.25,
        system_prompt=_CAREER_CHAT_SYSTEM,
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
