#!/usr/bin/env bash
# На VPS: нормализация .env, обновление pip-зависимостей, перезапуск API (и nginx).
# Git pull сюда не входит — выполняйте перед этим скриптом (или vps-full-update.ps1 с ПК).
# Без запроса логина при git pull: на VPS настройте PAT — deploy/VPS-GIT-PAT.md
#
#   cd /opt/vibework && sudo bash deploy/vps-update.sh
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ -f .env ]]; then
  sed -i 's/\r$//' .env || true
fi

if [[ -d venv ]]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
  pip install -r miniapp/requirements.txt -q
else
  echo "deploy/vps-update.sh: нет venv/ — установите venv и зависимости вручную." >&2
fi

sudo systemctl restart vibework-api
systemctl is-active vibework-api

sudo systemctl reload nginx 2>/dev/null || true

echo "vps-update.sh: готово."
