#!/usr/bin/env bash
# Только для вызова из launch-stack.sh — Telegram-бот (polling).
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

c_red='\033[91;1m'
c_dim='\033[2m'
c_rst='\033[0m'

if ! command -v python3 >/dev/null 2>&1; then
  echo -e "${c_red}✗ Нужен python3 в PATH${c_rst}"
  exit 1
fi
if [ ! -d venv ]; then
  python3 -m venv venv
fi
./venv/bin/python -m pip install -q -r miniapp/requirements.txt
export HH_USER_AGENT="${HH_USER_AGENT:-VibeWork/1.0 (+https://api.hh.ru)}"

if [ ! -f "$REPO_ROOT/.env" ]; then
  echo -e "${c_red}✗ Нет .env в корне ($REPO_ROOT)${c_rst}"
  echo -e "${c_dim}  создайте .env в корне репо — TELEGRAM_BOT_TOKEN от @BotFather (docs/ENV.md)${c_rst}"
  exit 1
fi
if ! grep -qE '^[[:space:]]*TELEGRAM_BOT_TOKEN=[^[:space:]]' "$REPO_ROOT/.env"; then
  echo -e "${c_red}✗ В .env не задан TELEGRAM_BOT_TOKEN${c_rst}"
  exit 1
fi

./venv/bin/python miniapp/bot/bot.py || {
  ec=$?
  echo -e "${c_red}✗ Ошибка запуска бота (код $ec)${c_rst}"
  exit "$ec"
}
