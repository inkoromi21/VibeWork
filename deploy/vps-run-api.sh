#!/usr/bin/env bash
# Запуск API на ВМ: обновление кода, зависимости, освобождение :8000, uvicorn.
# Использование (из каталога репозитория, например /opt/vibework):
#   bash deploy/vps-run-api.sh
# или:
#   cd /opt/vibework && bash deploy/vps-run-api.sh
#
# chmod +x deploy/vps-run-api.sh   # по желанию, чтобы вызывать ./deploy/vps-run-api.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

git pull origin main
# shellcheck disable=SC1091
source venv/bin/activate
pip install -r miniapp/requirements.txt -q

PORT=8000

# Снять старый процесс на порту (прошлый uvicorn / ручной запуск), иначе Errno 98.
# Совпадает с miniapp/run.py (uvicorn на :8000).
if command -v fuser >/dev/null 2>&1; then
  fuser -k "${PORT}/tcp" 2>/dev/null || true
else
  PIDS=$(lsof -ti:"${PORT}" -sTCP:LISTEN 2>/dev/null || true)
  if [ -n "${PIDS:-}" ]; then
    # shellcheck disable=SC2086
    kill ${PIDS} 2>/dev/null || true
  fi
fi
sleep 0.5

exec python miniapp/run.py
