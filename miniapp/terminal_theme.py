"""Цветной вывод в терминал (ANSI). Без зависимостей; NO_COLOR отключает краски."""

from __future__ import annotations

import os
import sys
_WIN_ANSI_ENABLED = False


def _use_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


def _enable_windows_ansi() -> None:
    global _WIN_ANSI_ENABLED
    if _WIN_ANSI_ENABLED or sys.platform != "win32":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        if kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING):
            _WIN_ANSI_ENABLED = True
    except Exception:
        pass


class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"


def mask_secret(value: str, head: int = 4, tail: int = 4) -> str:
    s = (value or "").strip()
    if not s:
        return "—"
    if len(s) <= head + tail + 1:
        return "•••"
    return f"{s[:head]}…{s[-tail:]}"


def launch(service: str, *, subtitle: str = "") -> None:
    """Первое сообщение: старт процесса."""
    _enable_windows_ansi()
    if _use_color():
        print(f"{C.BOLD}{C.CYAN}▶{C.RESET} {C.BOLD}{C.WHITE}Запуск {service}{C.RESET}")
        if subtitle:
            print(f"{C.DIM}  {subtitle}{C.RESET}")
    else:
        print(f"▶ Запуск {service}")
        if subtitle:
            print(f"  {subtitle}")


def ok(title: str, **details: str) -> None:
    """Успех + опциональные пары ключ — значение (одна колонка)."""
    _enable_windows_ansi()
    if _use_color():
        print(f"{C.BOLD}{C.GREEN}✓ {title}{C.RESET}")
        for key, val in details.items():
            if val is None or str(val).strip() == "":
                continue
            print(f"{C.DIM}  {key}:{C.RESET} {val}")
    else:
        print(f"✓ {title}")
        for key, val in details.items():
            if val is None or str(val).strip() == "":
                continue
            print(f"  {key}: {val}")


def fail(title: str, reason: str = "", *, hint: str = "") -> None:
    """Ошибка."""
    _enable_windows_ansi()
    if _use_color():
        print(f"{C.BOLD}{C.RED}✗ {title}{C.RESET}")
        if reason:
            print(f"{C.DIM}  Причина:{C.RESET} {reason}")
        if hint:
            print(f"{C.DIM}  Подсказка:{C.RESET} {hint}")
    else:
        print(f"✗ {title}")
        if reason:
            print(f"  Причина: {reason}")
        if hint:
            print(f"  Подсказка: {hint}")


def note(text: str) -> None:
    """Второстепенная строка (подсказка, путь)."""
    _enable_windows_ansi()
    if _use_color():
        print(f"{C.DIM}{text}{C.RESET}")
    else:
        print(text)


def warn(title: str, detail: str = "") -> None:
    _enable_windows_ansi()
    if _use_color():
        print(f"{C.BOLD}{C.YELLOW}⚠ {title}{C.RESET}")
        if detail:
            print(f"{C.DIM}  {detail}{C.RESET}")
    else:
        print(f"⚠ {title}")
        if detail:
            print(f"  {detail}")
