#!/usr/bin/env bash
# Поднять Ollama, если в .env включён локальный LLM и порт 11434 ещё мёртв.
set -euo pipefail

REPO_ROOT="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
ENV_FILE="$REPO_ROOT/.env"

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
  echo "✅ Ollama уже слушает http://127.0.0.1:11434"
  exit 0
fi

echo "🦙 В .env включён локальный LLM — запускаю Ollama…"

if [[ -d "/Applications/Ollama.app" ]]; then
  open -a Ollama
elif command -v ollama >/dev/null 2>&1; then
  nohup ollama serve >>"${TMPDIR:-/tmp}/ollama-wibe-work.log" 2>&1 &
  echo $! >"${TMPDIR:-/tmp}/ollama-wibe-work.pid"
  echo "   (ollama serve в фоне, лог: ${TMPDIR:-/tmp}/ollama-wibe-work.log)"
else
  echo "⚠️  Ollama не найдена. Установите: https://ollama.com"
  exit 0
fi

for _ in $(seq 1 30); do
  sleep 1
  if curl -sf "http://127.0.0.1:11434/api/tags" >/dev/null 2>&1; then
    echo "✅ Ollama отвечает на :11434"
    exit 0
  fi
done

echo "⚠️  За 30 с Ollama не поднялась — откройте приложение Ollama вручную и дождитесь иконки в меню."
