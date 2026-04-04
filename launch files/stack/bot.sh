#!/usr/bin/env bash
# Только для вызова из launch-stack.sh — Telegram-бот (polling).
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
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

if [ ! -f "$REPO_ROOT/.env" ]; then
  echo ""
  echo "Нет файла .env в корне репозитория ($REPO_ROOT)."
  echo "Создайте:  cp miniapp/.env.example .env"
  echo "Откройте .env и укажите TELEGRAM_BOT_TOKEN (токен от @BotFather в Telegram)."
  echo ""
  exit 1
fi
if ! grep -qE '^[[:space:]]*TELEGRAM_BOT_TOKEN=[^[:space:]]' "$REPO_ROOT/.env"; then
  echo ""
  echo "В $REPO_ROOT/.env не задан TELEGRAM_BOT_TOKEN (строка не должна быть пустой после =)."
  echo ""
  exit 1
fi

exec ./venv/bin/python miniapp/bot/bot.py
