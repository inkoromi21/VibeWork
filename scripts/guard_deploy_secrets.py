#!/usr/bin/env python3
"""Блокирует коммит, если в deploy/ попали похожие на секреты строки (кроме .template/.example)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "deploy"

# Паттерны реальных ключей (не плейсхолдеры PASTE_* / пустые значения)
_PATTERNS = [
    (re.compile(r"ghp_[A-Za-z0-9]{20,}"), "GitHub PAT (ghp_)"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "GitHub fine-grained PAT"),
    (re.compile(r"re_[A-Za-z0-9_]{20,}"), "Resend API key"),
    (re.compile(r"APPL[A-Z0-9]{30,}"), "hh.ru application token"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "OpenAI-style API key"),
]

_SAFE_SUFFIX = {".template", ".example", ".md", ".sh", ".ps1", ".conf"}


def _check_file(path: Path) -> list[str]:
    if path.suffix in _SAFE_SUFFIX or path.name.endswith(".template"):
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    issues: list[str] = []
    for i, line in enumerate(text.splitlines(), 1):
        if "PASTE_" in line:
            continue
        for rx, label in _PATTERNS:
            if rx.search(line):
                issues.append(f"{path.relative_to(ROOT)}:{i} — похоже на {label}")
    return issues


def main() -> int:
    paths = [Path(p) for p in sys.argv[1:] if p.strip()]
    if not paths:
        return 0
    all_issues: list[str] = []
    for p in paths:
        if not p.is_file():
            continue
        if DEPLOY not in p.parents and p.parent != DEPLOY:
            continue
        all_issues.extend(_check_file(p))
    if all_issues:
        print("Коммит отклонён: похожие на секреты значения в deploy/\n", file=sys.stderr)
        for msg in all_issues:
            print(f"  {msg}", file=sys.stderr)
        print(
            "\nСекреты только в корневом .env (см. docs/ENV.md). Не коммитьте deploy/*.env.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
