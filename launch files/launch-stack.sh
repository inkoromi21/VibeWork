#!/usr/bin/env bash
# Единая точка входа: весь стек на macOS (четыре окна Terminal — API, Cloudflare Tunnel, бот, сайт).
set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STACK_DIR="$REPO_ROOT/launch files/stack"
cd "$REPO_ROOT"

c_grn='\033[92;1m'
c_cya='\033[96;1m'
c_dim='\033[2m'
c_red='\033[91;1m'
c_rst='\033[0m'

if [ ! -d venv ]; then
  python3 -m venv venv
fi
./venv/bin/python -m pip install -q -r miniapp/requirements.txt

WEB_ROOT="$REPO_ROOT/website"
if [ -d "$WEB_ROOT" ] && [ ! -x "$WEB_ROOT/.venv/bin/python" ] && [ ! -x "$WEB_ROOT/venv/bin/python" ]; then
  echo -e "${c_cya}▶ Первый запуск: создаю website/.venv…${c_rst}"
  python3 -m venv "$WEB_ROOT/.venv"
  "$WEB_ROOT/.venv/bin/pip" install -q -r "$WEB_ROOT/requirements.txt"
fi

bash "$REPO_ROOT/miniapp/scripts/ensure-ollama.sh" "$REPO_ROOT" || true
export HH_USER_AGENT="${HH_USER_AGENT:-VibeWork/1.0 (+https://api.hh.ru)}"

if command -v lsof >/dev/null 2>&1; then
  pids=$(lsof -ti tcp:8000 -sTCP:LISTEN 2>/dev/null || true)
  if [ -n "$pids" ]; then
    echo -e "${c_cya}▶ Порт 8000 занят — завершаю PID: $pids${c_rst}"
    kill $pids 2>/dev/null || true
    sleep 0.5
    pids=$(lsof -ti tcp:8000 -sTCP:LISTEN 2>/dev/null || true)
    if [ -n "$pids" ]; then
      kill -9 $pids 2>/dev/null || true
    fi
  fi
fi

echo -e "${c_cya}▶ Открываю четыре окна Terminal…${c_rst}"
echo -e "${c_dim}  API :8000 · cloudflared →8000 · Telegram-бот · сайт :${PORT:-8765}${c_rst}"

if ! osascript <<EOF
tell application "Terminal"
    activate
    do script "cd '$REPO_ROOT' && ./venv/bin/python miniapp/run.py"
    delay 1
    do script "cd '$REPO_ROOT' && bash '$STACK_DIR/cloudflared.sh'"
    delay 1
    do script "cd '$REPO_ROOT' && bash '$STACK_DIR/bot.sh'"
    delay 1
    do script "cd '$REPO_ROOT' && bash '$STACK_DIR/website.sh'"
end tell
EOF
then
  echo -e "${c_red}✗ Не удалось открыть окна через Терминал.app${c_rst}" >&2
  echo -e "${c_dim}  macOS: Системные настройки → Автоматизация — разрешите управление «Терминалом».${c_rst}" >&2
  exit 1
fi

echo ""
echo -e "${c_grn}✓ Готово${c_rst}"
echo -e "${c_dim}  API    http://127.0.0.1:8000/miniapp/${c_rst}"
echo -e "${c_dim}  Туннель: URL из окна cloudflared (*.trycloudflare.com) → .env PUBLIC_BASE_URL${c_rst}"
echo -e "${c_dim}  Сайт   http://127.0.0.1:${PORT:-8765}${c_rst}"
