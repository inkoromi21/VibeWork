"""Дымовый тест: пакет миниаппы импортируется и FastAPI-приложение создаётся."""

from __future__ import annotations

import sys
from pathlib import Path


def test_miniapp_fastapi_app_loads() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    backend = repo_root / "miniapp" / "backend"
    path = str(backend)
    if path not in sys.path:
        sys.path.insert(0, path)

    import wibe_work.main as main_mod

    assert main_mod.app is not None
    assert main_mod.app.title == "VibeWork"
