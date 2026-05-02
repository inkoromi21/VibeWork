#!/usr/bin/env python3
"""Запуск API миниаппы (порт 8000). Из корня репозитория: python miniapp/run.py."""
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# Делает импортируемым пакет website/app как модуль "app.*" (для website_api_routes).
_REPO_ROOT = Path(__file__).resolve().parent.parent
_WEBSITE = _REPO_ROOT / "website"
if _WEBSITE.is_dir() and str(_WEBSITE) not in sys.path:
    sys.path.insert(0, str(_WEBSITE))

import uvicorn
from wibe_work.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
