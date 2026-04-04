#!/usr/bin/env bash
# macOS: отдельные окна Terminal — API миниаппы (:8000), Telegram-бот, веб-сайт (:8765).
# Бот и миниаппа используют корневой venv; сайт — свой .venv в website/ (создайте заранее).
set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LAUNCH_DIR="$REPO_ROOT/launch files"
cd "$REPO_ROOT"

if [ ! -d venv ]; then
  python3 -m venv venv
fi
./venv/bin/python -m pip install -q -r miniapp/requirements.txt

bash "$REPO_ROOT/miniapp/scripts/ensure-ollama.sh" "$REPO_ROOT" || true
export HH_USER_AGENT="${HH_USER_AGENT:-WibeWork/1.0 (+https://api.hh.ru)}"

echo "🚀 Окно 1: API (порт 8000)…"
osascript -e "tell application \"Terminal\" to do script \"cd '$REPO_ROOT' && ./venv/bin/python miniapp/run.py\""

sleep 2
echo "🤖 Окно 2: Telegram-бот…"
osascript -e "tell application \"Terminal\" to do script \"cd '$REPO_ROOT' && '${LAUNCH_DIR}/launch-bot.sh'\""

sleep 1
echo "🌐 Окно 3: сайт (порт ${PORT:-8765})…"
osascript -e "tell application \"Terminal\" to do script \"cd '$REPO_ROOT' && '${LAUNCH_DIR}/launch-website.sh'\""

echo ""
echo "Готово. Проверьте три окна Terminal."
echo "  API:     http://127.0.0.1:8000/miniapp/"
echo "  Сайт:    http://127.0.0.1:${PORT:-8765}"
