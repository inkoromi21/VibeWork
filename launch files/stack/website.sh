#!/usr/bin/env bash

# Веб VibeWork на :8765 (или $PORT).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

WEB_ROOT="$REPO_ROOT/website"

cd "$WEB_ROOT"



if [ -x ".venv/bin/python" ]; then

  PY=".venv/bin/python"

elif [ -x "venv/bin/python" ]; then

  PY="venv/bin/python"

else

  echo -e "\033[93;1m▶ Первый запуск: создаю website/.venv…\033[0m"

  python3 -m venv .venv

  PY=".venv/bin/python"

fi



"$PY" -m pip install -q -r requirements.txt

export PORT="${PORT:-8765}"

exec "$PY" main.py

