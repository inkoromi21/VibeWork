#!/usr/bin/env bash
# Поднять Ollama, если в .env включён локальный LLM и порт 11434 ещё мёртв.
set -euo pipefail

REPO_ROOT="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
ENV_FILE="$REPO_ROOT/.env"

c_grn='\033[92;1m'
c_cya='\033[96;1m'
c_ylw='\033[93;1m'
c_dim='\033[2m'
c_rst='\033[0m'

need=false
if [[ -f "$ENV_FILE" ]]; then
  if grep -qiE '^[[:space:]]*USE_OLLAMA[[:space:]]*=[[:space:]]*(1|true|yes|on)' "$ENV_FILE"; then
    need=true
  fi
  if grep -qE '^[[:space:]]*CHAT_API_URL=.*(127\.0\.0\.1|localhost):11434' "$ENV_FILE" 2>/dev/null; then
    need=true
  fi
fi

if [[ "$need" != true ]]; then
  exit 0
fi

if curl -sf "http://127.0.0.1:11434/api/tags" >/dev/null 2>&1; then
  echo -e "${c_grn}✓ Ollama уже слушает http://127.0.0.1:11434${c_rst}"
  exit 0
fi

echo -e "${c_cya}▶ Запуск Ollama${c_rst}"
echo -e "${c_dim}  В .env включён локальный LLM — нужен сервис на :11434${c_rst}"

if [[ -d "/Applications/Ollama.app" ]]; then
  open -a Ollama
elif command -v ollama >/dev/null 2>&1; then
  nohup ollama serve >>"${TMPDIR:-/tmp}/ollama-wibe-work.log" 2>&1 &
  echo $! >"${TMPDIR:-/tmp}/ollama-wibe-work.pid"
  echo -e "${c_dim}  ollama serve в фоне · лог: ${TMPDIR:-/tmp}/ollama-wibe-work.log${c_rst}"
else
  echo -e "${c_ylw}⚠ Ollama не найдена${c_rst}"
  echo -e "${c_dim}  https://ollama.com/${c_rst}"
  exit 0
fi

for _ in $(seq 1 30); do
  sleep 1
  if curl -sf "http://127.0.0.1:11434/api/tags" >/dev/null 2>&1; then
    echo -e "${c_grn}✓ Ollama отвечает на :11434${c_rst}"
    exit 0
  fi
done

echo -e "${c_ylw}⚠ За 30 с Ollama не поднялась — запустите приложение вручную${c_rst}"
