#!/usr/bin/env bash
# VPS: .env CRLF, pip, restart API + nginx; print steps and recent logs (like foreground uvicorn).
#
#   cd /opt/vibework && sudo bash deploy/vps-update.sh
#
set -euo pipefail

SERVICE_NAME="${VIBEWORK_SYSTEMD_SERVICE:-vibework-api}"

echo "=== vps-update $(date -Is) ==="

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
echo "[1/5] REPO_ROOT=$REPO_ROOT"

if [[ -f .env ]]; then
  echo "[2/5] strip CRLF in .env"
  sed -i 's/\r$//' .env || true
else
  echo "[2/5] no .env (skip)"
fi

if [[ -d venv ]]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
  echo "[3/5] pip install -r miniapp/requirements.txt"
  pip install -r miniapp/requirements.txt
else
  echo "[3/5] WARN: no venv/ — skip pip" >&2
fi

echo "[4/5] systemctl restart $SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"
systemctl is-active "$SERVICE_NAME" || true

echo "[4/5] nginx reload (if installed)"
sudo systemctl reload nginx 2>/dev/null || true

sleep 1
echo "[5/5] GET http://127.0.0.1:8000/api/health/email"
curl -sS --max-time 5 "http://127.0.0.1:8000/api/health/email" || echo "(curl failed)"

echo ""
echo "=== last 50 lines: journalctl -u $SERVICE_NAME ==="
if command -v journalctl >/dev/null 2>&1; then
  journalctl -u "$SERVICE_NAME" -n 50 --no-pager -o short-iso 2>/dev/null || true
else
  echo "(no journalctl)"
fi

echo "=== follow live logs: journalctl -u $SERVICE_NAME -f ==="
echo "=== vps-update done $(date -Is) ==="
