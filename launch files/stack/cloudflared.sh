#!/usr/bin/env bash
# Quick tunnel: локальный :8000 → https://*.trycloudflare.com
# Прокси сброшены (см. cloudflared#376). Опционально: export VIBEWORK_CLOUDFLARED_REGION=us
set -e
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"
export HTTP_PROXY= HTTPS_PROXY= ALL_PROXY= http_proxy= https_proxy= all_proxy=
echo -e "\033[1;96m▶ Cloudflare Tunnel (quick)\033[0m"
echo -e "\033[2m  :8000 -> https в логе · http2 · IPv4\033[0m"
if ! command -v cloudflared >/dev/null 2>&1; then
  echo -e "\033[91;1m✗ cloudflared не в PATH\033[0m" >&2
  echo -e "\033[2m  Установка: https://github.com/cloudflare/cloudflared/releases (darwin) или brew install cloudflared\033[0m" >&2
  exit 1
fi
cloudflared --version
if [ -n "${VIBEWORK_CLOUDFLARED_REGION:-}" ]; then
  exec cloudflared --region "$VIBEWORK_CLOUDFLARED_REGION" tunnel --url http://127.0.0.1:8000 --protocol http2 --edge-ip-version 4
fi
exec cloudflared tunnel --url http://127.0.0.1:8000 --protocol http2 --edge-ip-version 4
