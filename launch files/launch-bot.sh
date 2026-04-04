#!/usr/bin/env bash
# Запуск Telegram-бота (polling). Нужен работающий API миниаппы (порт 8000) и .env в корне репозитория.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Нужен python3 в PATH"
  exit 1
fi
if [ ! -d venv ]; then
  python3 -m venv venv
fi
./venv/bin/python -m pip install -q -r miniapp/requirements.txt
export HH_USER_AGENT="${HH_USER_AGENT:-WibeWork/1.0 (+https://api.hh.ru)}"
exec ./venv/bin/python miniapp/bot/bot.py
