#!/usr/bin/env bash
# Туннель на API :8000 (HTTPS для Telegram Web App).
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

echo -e "\033[1;96m▶ Запуск ngrok\033[0m"
echo -e "\033[2m  Прокси → http://127.0.0.1:8000 · веб-UI: http://127.0.0.1:4040\033[0m"

for candidate in "$REPO_ROOT/miniapp/scripts/bin/ngrok" "$REPO_ROOT/miniapp/scripts/bin/ngrok.exe"; do
  if [ -f "$candidate" ] && [ -x "$candidate" ]; then
    exec "$candidate" http 8000
  fi
done
if command -v ngrok >/dev/null 2>&1; then
  exec ngrok http 8000
fi

echo -e "\033[91;1m✗ ngrok не найден\033[0m" >&2
echo -e "\033[2m  https://ngrok.com/ или miniapp/scripts/bin/ngrok\033[0m" >&2
exit 1
