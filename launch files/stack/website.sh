#!/usr/bin/env bash
# Только для вызова из launch-stack.sh — сайт CareerCompass (:8765).
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WEB_ROOT="$REPO_ROOT/website"
cd "$WEB_ROOT"

if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
elif [ -x "venv/bin/python" ]; then
  PY="venv/bin/python"
else
  echo "Создаю website/.venv и ставлю зависимости…"
  python3 -m venv .venv
  PY=".venv/bin/python"
fi

"$PY" -m pip install -q -r requirements.txt
export PORT="${PORT:-8765}"
exec "$PY" main.py
