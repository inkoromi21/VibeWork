"""Точка входа: запуск сервера из корня проекта (python main.py)."""

import os
import sys
from pathlib import Path

import uvicorn

# Всегда корень website/ (иначе не находятся app/ и frontend/)
_ROOT = Path(__file__).resolve().parent
os.chdir(_ROOT)
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_REPO_ROOT = _ROOT.parent
_MINIAPP_TERM = _REPO_ROOT / "miniapp"
if _MINIAPP_TERM.is_dir():
    sys.path.insert(0, str(_MINIAPP_TERM))

try:
    from terminal_theme import fail, launch, note
except ImportError:

    def launch(service: str, *, subtitle: str = "") -> None:
        print(f"▶ Запуск {service}")
        if subtitle:
            print(f"  {subtitle}")

    def note(text: str) -> None:
        print(text)

    def fail(title: str, reason: str = "", *, hint: str = "") -> None:
        print(f"✗ {title}")
        if reason:
            print(f"  Причина: {reason}")
        if hint:
            print(f"  Подсказка: {hint}")


# 8000 на Windows часто даёт WinError 10013 (порт занят / зарезервирован)
PORT = int(os.environ.get("PORT", "8765"))

if __name__ == "__main__":
    launch(
        "веб-сайта VibeWork",
        subtitle=f"reload=ON · http://127.0.0.1:{PORT} · папка {_ROOT.name}/",
    )
    note(f"Остановка: Ctrl+C · ниже лог uvicorn")
    print()
    try:
        uvicorn.run("app.main:app", host="127.0.0.1", port=PORT, reload=True)
    except OSError as e:
        fail(
            "Ошибка запуска веб-сервера",
            str(e),
            hint=f"Порт {PORT} занят — другой порт: PORT=8770 (Linux/macOS) или set PORT=8770 (Windows)",
        )
        sys.exit(1)
