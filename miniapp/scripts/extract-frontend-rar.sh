#!/bin/bash
# Распаковать frontend.rar в папку проекта (нужен unar: brew install unar)
set -e
TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$TOOLS_DIR/../.." && pwd)"
RAR="${1:-$HOME/Downloads/frontend.rar}"
OUT="$REPO_ROOT/miniapp/frontend/import-rar"
if ! command -v unar >/dev/null 2>&1; then
  echo "Установите: brew install unar"
  exit 1
fi
mkdir -p "$OUT"
unar -f -o "$OUT" "$RAR"
echo "Готово: $OUT"
