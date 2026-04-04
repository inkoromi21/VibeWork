#!/usr/bin/env bash
# Локальная проверка как в CI (два изолированных venv в /tmp).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python3}"

run_miniapp() {
  local d
  d="$(mktemp -d)"
  trap 'rm -rf "$d"' RETURN
  "$PY" -m venv "$d/v"
  local vpy="$d/v/bin/python"
  [[ -x "$vpy" ]] || vpy="$d/v/bin/python3"
  "$vpy" -m pip install -q -U pip
  "$vpy" -m pip install -q -r miniapp/requirements.txt "pytest>=8,<9"
  "$vpy" -m compileall -q miniapp/backend/wibe_work
  "$vpy" -m pytest tests/miniapp -q --tb=short
}

run_website() {
  local d
  d="$(mktemp -d)"
  trap 'rm -rf "$d"' RETURN
  "$PY" -m venv "$d/v"
  local vpy="$d/v/bin/python"
  [[ -x "$vpy" ]] || vpy="$d/v/bin/python3"
  "$vpy" -m pip install -q -U pip
  "$vpy" -m pip install -q -r website/requirements.txt "pytest>=8,<9"
  "$vpy" -m compileall -q website/app
  "$vpy" -m pytest tests/website -q --tb=short
}

echo "== miniapp =="
run_miniapp
echo "== website =="
run_website
echo "OK"
