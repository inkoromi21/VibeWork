@echo off

REM Единая точка входа: Windows — три окна (API :8000, Telegram-бот, сайт :8765).

chcp 65001 >nul

setlocal

cd /d "%~dp0.."

if not exist "venv\Scripts\python.exe" (

  powershell -NoProfile -Command "Write-Host '✗ Создайте venv в корне: python -m venv venv' -ForegroundColor Red"

  pause

  exit /b 1

)

call venv\Scripts\activate.bat

pip install -q -r miniapp\requirements.txt

if not defined HH_USER_AGENT set "HH_USER_AGENT=VibeWork/1.0 (+https://api.hh.ru)"



if not exist "website\.venv\Scripts\python.exe" (

  if not exist "website\venv\Scripts\python.exe" (

    powershell -NoProfile -Command "Write-Host '▶ Первый запуск: создаю website\.venv…' -ForegroundColor Yellow"

    pushd website

    python -m venv .venv

    call .venv\Scripts\pip.exe install -q -r requirements.txt

    popd

  )

)



powershell -NoProfile -Command "Write-Host '▶ Освобождаю порт 8000 (если занят старым API)…' -ForegroundColor Cyan"

powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" 2>nul

timeout /t 1 /nobreak >nul



start "VibeWork — API :8000" cmd /k "cd /d %CD% && call venv\Scripts\activate.bat && python miniapp\run.py"

timeout /t 2 /nobreak >nul

start "VibeWork — Telegram-бот" cmd /k cd /d "%CD%" ^&^& call "%~dp0stack\bot.bat"

timeout /t 1 /nobreak >nul

start "VibeWork — сайт :8765" cmd /k cd /d "%CD%" ^&^& set WIBE_NO_PAUSE=1 ^&^& call "%~dp0stack\website.bat"



powershell -NoProfile -Command "& { Write-Host ''; Write-Host '✓ Окна запущены' -ForegroundColor Green; Write-Host '  API http://127.0.0.1:8000/ (миниапп /miniapp/), сайт http://127.0.0.1:8765' -ForegroundColor DarkGray; Write-Host '  Для Web App в Telegram задайте в .env HTTPS: TELEGRAM_PUBLIC_BASE_URL (прод-домен или свой туннель)' -ForegroundColor DarkGray }"

pause

