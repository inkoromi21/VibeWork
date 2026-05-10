#!/usr/bin/env bash
# Запуск API на ВМ: зависимости, освобождение :8000, uvicorn.
# Код репозитория скрипт НЕ тянет — сделайте git pull отдельно (иначе при pull с PAT в URL
# и повторном git pull внутри скрипта Git снова запрашивает логин для origin).
#
# Использование (из каталога репозитория, например /opt/vibework):
#   git pull origin main && bash deploy/vps-run-api.sh
# или после настройки credential.helper / SSH на origin:
#   cd /opt/vibework && bash deploy/vps-run-api.sh
#   (и перед этим при необходимости: git pull origin main)
#
# chmod +x deploy/vps-run-api.sh   # по желанию, чтобы вызывать ./deploy/vps-run-api.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

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
