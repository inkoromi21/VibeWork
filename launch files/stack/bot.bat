@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0..\.."
if not exist "venv\Scripts\python.exe" (
  echo Создайте venv в корне репозитория: python -m venv venv
  pause
  exit /b 1
)
call venv\Scripts\activate.bat
pip install -q -r miniapp\requirements.txt
if not defined HH_USER_AGENT set "HH_USER_AGENT=WibeWork/1.0 (+https://api.hh.ru)"

if not exist ".env" (
  echo.
  echo Нет файла .env в корне репозитория.
  echo Создайте:  copy miniapp\.env.example .env
  echo Укажите в .env TELEGRAM_BOT_TOKEN.
  echo.
  pause
  exit /b 1
)
findstr /r /c:"^TELEGRAM_BOT_TOKEN=." .env >nul 2>&1
if errorlevel 1 (
  echo.
  echo В .env нет непустого TELEGRAM_BOT_TOKEN.
  echo.
  pause
  exit /b 1
)

python miniapp\bot\bot.py
pause
