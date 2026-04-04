#!/usr/bin/env bash
# Запуск веб-сайта CareerCompass (порт по умолчанию 8765).
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WEB_ROOT="$REPO_ROOT/website"
cd "$WEB_ROOT"
if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
elif [ -x "venv/bin/python" ]; then
  PY="venv/bin/python"
else
  echo "Создайте окружение: cd website && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi
"$PY" -m pip install -q -r requirements.txt
export PORT="${PORT:-8765}"
exec "$PY" main.py
