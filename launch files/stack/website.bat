@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0..\..\website"

if exist ".venv\Scripts\python.exe" (
  call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\python.exe" (
  call venv\Scripts\activate.bat
) else (
  powershell -NoProfile -Command "Write-Host '▶ Первый запуск: создаю website\.venv…' -ForegroundColor Yellow"
  python -m venv .venv
  call .venv\Scripts\pip.exe install -q -r requirements.txt
  call .venv\Scripts\activate.bat
)

pip install -q -r requirements.txt
if not defined PORT set "PORT=8765"
python main.py

if not defined WIBE_NO_PAUSE pause
