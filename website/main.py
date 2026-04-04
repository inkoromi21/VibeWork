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

# 8000 на Windows часто даёт WinError 10013 (порт занят / зарезервирован)
PORT = int(os.environ.get("PORT", "8765"))

if __name__ == "__main__":
    print(f"Папка проекта: {_ROOT}")
    print(f"Сервер: http://127.0.0.1:{PORT}")
    print("Остановка: Ctrl+C в этом окне\n")
    uvicorn.run("app.main:app", host="127.0.0.1", port=PORT, reload=True)
