#!/usr/bin/env bash
# Единая точка входа: весь стек на macOS (четыре окна Terminal — API, ngrok, бот, сайт).
# Бот и миниаппа — корневой venv; сайт — website/.venv (создаётся при первом запуске).
set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STACK_DIR="$REPO_ROOT/launch files/stack"
cd "$REPO_ROOT"

if [ ! -d venv ]; then
  python3 -m venv venv
fi
./venv/bin/python -m pip install -q -r miniapp/requirements.txt

WEB_ROOT="$REPO_ROOT/website"
if [ -d "$WEB_ROOT" ] && [ ! -x "$WEB_ROOT/.venv/bin/python" ] && [ ! -x "$WEB_ROOT/venv/bin/python" ]; then
  echo "Готовлю website/.venv (первый запуск)…"
  python3 -m venv "$WEB_ROOT/.venv"
  "$WEB_ROOT/.venv/bin/pip" install -q -r "$WEB_ROOT/requirements.txt"
fi

bash "$REPO_ROOT/miniapp/scripts/ensure-ollama.sh" "$REPO_ROOT" || true
export HH_USER_AGENT="${HH_USER_AGENT:-WibeWork/1.0 (+https://api.hh.ru)}"

# Снять старый uvicorn / другой процесс на :8000 (иначе «address already in use»).
if command -v lsof >/dev/null 2>&1; then
  pids=$(lsof -ti tcp:8000 -sTCP:LISTEN 2>/dev/null || true)
  if [ -n "$pids" ]; then
    echo "Порт 8000 занят — завершаю процесс(ы): $pids"
    kill $pids 2>/dev/null || true
    sleep 0.5
    pids=$(lsof -ti tcp:8000 -sTCP:LISTEN 2>/dev/null || true)
    if [ -n "$pids" ]; then
      kill -9 $pids 2>/dev/null || true
    fi
  fi
fi

# Один блок AppleScript: несколько do script — отдельные окна (API → ngrok → бот → сайт).
echo "🚀 Открываю четыре окна Terminal (API :8000, ngrok→8000, бот, сайт :${PORT:-8765})…"
if ! osascript <<EOF
tell application "Terminal"
    activate
    do script "cd '$REPO_ROOT' && ./venv/bin/python miniapp/run.py"
    delay 1
    do script "cd '$REPO_ROOT' && bash '$STACK_DIR/ngrok.sh'"
    delay 1
    do script "cd '$REPO_ROOT' && bash '$STACK_DIR/bot.sh'"
    delay 1
    do script "cd '$REPO_ROOT' && bash '$STACK_DIR/website.sh'"
end tell
EOF
then
  echo ""
  echo "Не удалось открыть окна через Терминал.app."
  echo "Частые причины на macOS:"
  echo "  • Запуск из Cursor/другого терминала: Системные настройки → Конфиденциальность и безопасность → Автоматизация — разрешите этому приложению управлять «Терминалом»."
  echo "  • В Терминале: Настройки → Обычные → снимите «Во вкладках предпочтительнее», если нужны именно отдельные окна, а не вкладки в одном окне."
  exit 1
fi

echo ""
echo "Готово. Проверьте четыре окна Terminal."
echo "  API:     http://127.0.0.1:8000/miniapp/"
echo "  ngrok:   веб-интерфейс туннелей http://127.0.0.1:4040 (бот берёт HTTPS-URL отсюда)"
echo "  Сайт:    http://127.0.0.1:${PORT:-8765}"
