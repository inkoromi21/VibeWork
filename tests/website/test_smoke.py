"""Дымовый тест: приложение сайта импортируется (нужны зависимости website/)."""

from __future__ import annotations

import sys
from pathlib import Path


def test_website_fastapi_app_loads() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    website_root = repo_root / "website"
    path = str(website_root)
    if path not in sys.path:
        sys.path.insert(0, path)

    from app.main import app

    assert app is not None
    assert app.title == "VibeWork"
