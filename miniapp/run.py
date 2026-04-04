#!/usr/bin/env python3
"""Запуск API миниаппы (порт 8000). Из корня репозитория: python miniapp/run.py."""
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import uvicorn
from wibe_work.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
