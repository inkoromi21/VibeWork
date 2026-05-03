#!/usr/bin/env python3
"""Обновить или добавить одну строку KEY=value в .env (UTF-8)."""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse


def _reject_bad_telegram_public_url(key: str, value: str) -> None:
    if key != "TELEGRAM_PUBLIC_BASE_URL":
        return
    host = (urlparse(value).hostname or "").lower()
    blocked = {"api.trycloudflare.com", "www.trycloudflare.com"}
    if host in blocked or not host:
        print(
            f"upsert_env: refuse {key}={value!r} (not a tunnel hostname)",
            file=sys.stderr,
        )
        sys.exit(1)


def main() -> None:
    if len(sys.argv) != 4:
        print("Usage: upsert_env.py <path/.env> KEY VALUE", file=sys.stderr)
        sys.exit(2)
    path = Path(sys.argv[1])
    key = sys.argv[2]
    value = sys.argv[3]
    _reject_bad_telegram_public_url(key, value)
    lines: list[str] = []
    if path.is_file():
        lines = path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    found = False
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k == key:
                out.append(f"{key}={value}")
                found = True
                continue
        out.append(line)
    if not found:
        if out and out[-1].strip():
            out.append("")
        out.append(f"{key}={value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
