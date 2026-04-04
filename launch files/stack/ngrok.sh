#!/usr/bin/env bash
# Только для вызова из launch-stack.sh — туннель на API :8000.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"
for candidate in "$REPO_ROOT/miniapp/scripts/bin/ngrok" "$REPO_ROOT/miniapp/scripts/bin/ngrok.exe"; do
  if [ -f "$candidate" ] && [ -x "$candidate" ]; then
    exec "$candidate" http 8000
  fi
done
if command -v ngrok >/dev/null 2>&1; then
  exec ngrok http 8000
fi
echo "Нужен ngrok: https://ngrok.com/ или бинарник в miniapp/scripts/bin/ngrok"
exit 1
