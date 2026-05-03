#!/usr/bin/env python3

"""Точка входа API (порт 8000). Из корня: python miniapp/run.py."""

import sys

from pathlib import Path



_MINIAPP = Path(__file__).resolve().parent

_BACKEND = _MINIAPP / "backend"

sys.path.insert(0, str(_MINIAPP))

sys.path.insert(0, str(_BACKEND))



_REPO_ROOT = _MINIAPP.parent

_WEBSITE = _REPO_ROOT / "website"

if _WEBSITE.is_dir() and str(_WEBSITE) not in sys.path:

    sys.path.insert(0, str(_WEBSITE))



from terminal_theme import fail, launch, note  # noqa: E402



import uvicorn  # noqa: E402

from wibe_work.main import app  # noqa: E402



if __name__ == "__main__":

    launch(

        "API VibeWork",

        subtitle="uvicorn · 0.0.0.0:8000 · miniapp / career / сайт",

    )

    note("Остановка: Ctrl+C · ниже лог uvicorn")

    print()

    try:

        uvicorn.run(app, host="0.0.0.0", port=8000)

    except OSError as e:

        fail(

            "Ошибка запуска API",

            str(e),

            hint="Порт 8000 занят — закройте процесс или измените порт в miniapp/run.py",

        )

        sys.exit(1)


