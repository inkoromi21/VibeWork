#!/usr/bin/env python3
"""Удалить всех пользователей и аннулировать старые JWT (JWT_INVALID_BEFORE в .env)."""

from __future__ import annotations

import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "miniapp" / "backend"))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

MINIAPP_USER_TABLES = [
    "learning_progress",
    "ai_chat_sessions",
    "password_reset_tokens",
    "vibework_sessions",
    "vibework_snapshots",
    "user_hh_state",
    "user_competencies",
    "answers",
    "email_users",
    "telegram_users",
    "user_profiles",
    "simulator_progress",
]

WEBSITE_LEGACY = ROOT / "website" / "data" / "vibework.db"


def _wipe_sqlite(path: Path, tables: list[str]) -> None:
    if not path.is_file():
        print(f"  skip (нет файла): {path}")
        return
    conn = sqlite3.connect(path)
    existing = {
        r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    for table in tables:
        if table not in existing:
            continue
        n = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
        conn.execute(f"DELETE FROM [{table}]")
        print(f"  {path.name} · {table}: {n}")
    conn.commit()
    conn.close()


def _set_jwt_invalid_before(env_path: Path) -> str:
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    line = f"JWT_INVALID_BEFORE={stamp}"
    if not env_path.is_file():
        env_path.write_text(line + "\n", encoding="utf-8")
        return stamp
    text = env_path.read_text(encoding="utf-8")
    if re.search(r"^JWT_INVALID_BEFORE=", text, flags=re.MULTILINE):
        text = re.sub(
            r"^JWT_INVALID_BEFORE=.*$",
            line,
            text,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        if text and not text.endswith("\n"):
            text += "\n"
        text += line + "\n"
    env_path.write_text(text, encoding="utf-8")
    return stamp


def main() -> None:
    from wibe_work.sqlite_db import _db_path, init_db

    init_db()
    miniapp_db = _db_path()
    print("Miniapp DB:", miniapp_db)
    _wipe_sqlite(miniapp_db, MINIAPP_USER_TABLES)

    print("Website legacy DB:", WEBSITE_LEGACY)
    _wipe_sqlite(WEBSITE_LEGACY, ["sessions", "user_snapshots", "users"])

    stamp = _set_jwt_invalid_before(ROOT / ".env")
    print(f"\nГотово. В .env задано JWT_INVALID_BEFORE={stamp}")
    print("Перезапустите API. В браузере: выйти или очистить localStorage для сайта.")


if __name__ == "__main__":
    main()
