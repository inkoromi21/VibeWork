#!/usr/bin/env python3
"""Проверка доступа к API hh.ru по переменным из корневого .env."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_MINIAPP_BACKEND = _REPO / "miniapp" / "backend"
sys.path.insert(0, str(_MINIAPP_BACKEND))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_REPO / ".env")

from wibe_work import config as cfg  # noqa: E402
from wibe_work.services import hh_client  # noqa: E402


def main() -> int:
    print("hh.ru diagnostic")
    print(f"  HH_USER_AGENT: {cfg.HH_USER_AGENT[:80]}{'…' if len(cfg.HH_USER_AGENT) > 80 else ''}")
    if cfg.HH_APP_ACCESS_TOKEN:
        print("  auth: HH_APP_ACCESS_TOKEN (set)")
    elif cfg.HH_CLIENT_ID and cfg.HH_CLIENT_SECRET:
        print("  auth: client_credentials (id + secret set)")
    elif cfg.HH_CLIENT_ID or cfg.HH_CLIENT_SECRET:
        print("  auth: INCOMPLETE — need both HH_CLIENT_ID and HH_CLIENT_SECRET")
        return 1
    else:
        print("  auth: none (only User-Agent; add id/secret after dev.hh.ru approval)")

    try:
        if cfg.HH_CLIENT_ID and cfg.HH_CLIENT_SECRET and not cfg.HH_APP_ACCESS_TOKEN:
            token, ttl = hh_client._fetch_client_credentials_token()
            print(f"  POST /token: OK (expires_in≈{ttl}s, token …{token[-8:]})")
    except Exception as e:
        print(f"  POST /token: FAIL — {e}")
        return 1

    try:
        areas = hh_client.suggest_areas("Моск", limit=3)
        if areas:
            print(f"  GET /suggests/areas: OK ({len(areas)} items, e.g. {areas[0]['text']!r})")
        else:
            print("  GET /suggests/areas: empty response")
    except Exception as e:
        print(f"  GET /suggests/areas: FAIL — {e}")
        return 1

    try:
        raw = hh_client.search_vacancies({"text": "python", "area": "1", "per_page": 1})
        found = raw.get("found")
        print(f"  GET /vacancies: OK (found={found})")
    except Exception as e:
        print(f"  GET /vacancies: FAIL — {e}")
        if not (cfg.HH_APP_ACCESS_TOKEN or (cfg.HH_CLIENT_ID and cfg.HH_CLIENT_SECRET)):
            print(
                "  → Заполните HH_CLIENT_ID и HH_CLIENT_SECRET в .env "
                "(кабинет https://dev.hh.ru/admin), затем перезапустите API."
            )
        return 1

    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
