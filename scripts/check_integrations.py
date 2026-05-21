#!/usr/bin/env python3
"""Проверка ключевых интеграций (без вывода секретов). Запуск из корня репозитория."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "miniapp" / "backend"))

# Как run.py: .env из корня репозитория
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from wibe_work import config as cfg
from wibe_work.services.learning import get_integration_status
from wibe_work.services.learning.adapters import github_search_repos
from wibe_work.services.learning.vk_video import vk_video_search
from wibe_work.services.hh_client import _resolve_bearer, suggest_area_id
from wibe_work.services.llm_client import fetch_llm_completion, get_llm_settings, llm_configured


def _ok(label: str, ok: bool, detail: str = "") -> None:
    mark = "OK" if ok else "FAIL"
    extra = f" — {detail}" if detail else ""
    print(f"  [{mark}] {label}{extra}")


def main() -> int:
    print("VibeWork — проверка интеграций\n")
    print("Переменные (.env):")
    _ok("VK_ACCESS_TOKEN", bool(cfg.VK_ACCESS_TOKEN))
    _ok("GITHUB_TOKEN", bool(cfg.GITHUB_TOKEN))
    _ok(
        "hh.ru auth",
        bool(cfg.HH_APP_ACCESS_TOKEN or (cfg.HH_CLIENT_ID and cfg.HH_CLIENT_SECRET)),
        "HH_APP_ACCESS_TOKEN или client_id+secret",
    )
    _ok("HH_USER_AGENT", bool(cfg.HH_USER_AGENT and "@" in cfg.HH_USER_AGENT or "localhost" not in cfg.HH_USER_AGENT))

    llm_cfg = get_llm_settings()
    _ok("LLM configured", llm_configured())
    if llm_cfg:
        url, _, model = llm_cfg
        local = "127.0.0.1" in url or "localhost" in url
        _ok("LLM endpoint", True, f"model={model}, local={local}")
        text, notice = fetch_llm_completion("ok", max_tokens=8, temperature=0)
        _ok("LLM chat probe", bool(text), notice or (text[:40] if text else "пустой ответ"))
    else:
        _ok("LLM endpoint", False, "CHAT_API_KEY + CHAT_API_URL в .env")

    print("\nLearning status:")
    st = get_integration_status()
    for name in ("vk_video", "github", "exercism", "codewars", "onet", "esco"):
        block = st.get(name, {})
        if isinstance(block, dict):
            conf = block.get("configured", block.get("preferred"))
            _ok(name, bool(conf), str(block.get("needs") or "")[:60])
        else:
            _ok(name, bool(block))

    print("\nПробные запросы:")
    if cfg.GITHUB_TOKEN:
        repos = github_search_repos("python starter", limit=1)
        _ok("GitHub search", len(repos) > 0, repos[0].get("url", "")[:50] if repos else "пусто")
    else:
        _ok("GitHub search", False, "нет токена")

    if cfg.VK_ACCESS_TOKEN:
        vids = vk_video_search("python курс", limit=1)
        _ok("VK video.search", len(vids) > 0, vids[0].get("url", "")[:50] if vids else "пусто/ошибка API")
    else:
        _ok("VK video.search", False, "нет токена")

    try:
        token = _resolve_bearer()
        _ok("hh.ru bearer", bool(token), "есть" if token else "нет — проверьте HH_* в .env")
        if token:
            area = suggest_area_id("Кемерово")
            _ok("hh.ru suggests", area is not None, f"area_id={area}" if area else "пусто")
    except Exception as e:
        _ok("hh.ru API", False, str(e)[:80])

    print("\nГотово. После правок .env перезапустите API.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
