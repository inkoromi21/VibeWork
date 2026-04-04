@echo off
REM Единая точка входа: весь стек на Windows (четыре окна — API, ngrok, бот, сайт).
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
if not exist "venv\Scripts\python.exe" (
  echo Создайте venv в корне: python -m venv venv
  pause
  exit /b 1
)
call venv\Scripts\activate.bat
pip install -q -r miniapp\requirements.txt
call miniapp\scripts\windows\ensure-ollama.bat
if not defined HH_USER_AGENT set "HH_USER_AGENT=WibeWork/1.0 (+https://api.hh.ru)"

if not exist "website\.venv\Scripts\python.exe" (
  if not exist "website\venv\Scripts\python.exe" (
    echo Готовлю website\.venv ^(первый запуск^)...
    pushd website
    python -m venv .venv
    call .venv\Scripts\pip.exe install -q -r requirements.txt
    popd
  )
)

echo Освобождение порта 8000 ^(если остался старый API^)...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" 2>nul
timeout /t 1 /nobreak >nul

start "Wibe — API :8000" cmd /k "cd /d %CD% && call venv\Scripts\activate.bat && python miniapp\run.py"
timeout /t 2 /nobreak >nul
start "Wibe — ngrok :8000" cmd /k call "%~dp0stack\ngrok.bat"
timeout /t 2 /nobreak >nul
start "Wibe — Telegram bot" cmd /k cd /d "%CD%" ^&^& call "%~dp0stack\bot.bat"
timeout /t 1 /nobreak >nul
start "CareerCompass — website" cmd /k cd /d "%CD%" ^&^& set WIBE_NO_PAUSE=1 ^&^& call "%~dp0stack\website.bat"

echo.
echo Запущены четыре окна: API, ngrok, бот, сайт.
pause
