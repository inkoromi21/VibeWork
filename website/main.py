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
_MINIAPP_BACKEND = _MINIAPP_TERM / "backend"
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

_FULL_STACK = os.environ.get("VIBEWORK_FULL_STACK", "").strip().lower() in ("1", "true", "yes")


def _configure_paths_for_unified() -> None:
    """Тот же порядок sys.path, что в miniapp/run.py — приложение wibe_work.main."""
    if _MINIAPP_BACKEND.is_dir():
        sys.path.insert(0, str(_MINIAPP_BACKEND))
    if _MINIAPP_TERM.is_dir():
        sys.path.insert(0, str(_MINIAPP_TERM))
    _ws = _REPO_ROOT / "website"
    if _ws.is_dir():
        sys.path.insert(0, str(_ws))


if __name__ == "__main__":
    if _FULL_STACK:
        _configure_paths_for_unified()
        from wibe_work.main import app as _unified_app  # noqa: E402

        launch(
            "VibeWork (полный стек)",
            subtitle=(
                f"как miniapp/run.py · / и /miniapp/ · http://127.0.0.1:{PORT} · "
                "переменная VIBEWORK_FULL_STACK=1"
            ),
        )
        note("Остановка: Ctrl+C · для бота укажите PUBLIC_BASE_URL на этот хост и порт")
        print()
        try:
            # reload в дочернем процессе не подхватывает правки sys.path — без reload
            uvicorn.run(_unified_app, host="127.0.0.1", port=PORT, reload=False)
        except OSError as e:
            fail(
                "Ошибка запуска",
                str(e),
                hint=f"Порт {PORT} занят — другой порт: set PORT=8770",
            )
            sys.exit(1)
    else:
        launch(
            "веб-сайта VibeWork",
            subtitle=(
                f"reload=ON · http://127.0.0.1:{PORT} · только website/app "
                f"(без /miniapp/). Полный стек: set VIBEWORK_FULL_STACK=1 или python miniapp/run.py"
            ),
        )
        note("Остановка: Ctrl+C · ниже лог uvicorn")
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
