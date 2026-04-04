@echo off
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

start "Wibe — API :8000" cmd /k "cd /d %CD% && call venv\Scripts\activate.bat && python miniapp\run.py"
timeout /t 2 /nobreak >nul
start "Wibe — Telegram bot" cmd /k "cd /d %CD% && call venv\Scripts\activate.bat && python miniapp\bot\bot.py"
timeout /t 1 /nobreak >nul
start "CareerCompass — website" cmd /k "cd /d %CD%\website && if exist .venv\Scripts\activate.bat (call .venv\Scripts\activate.bat) else if exist venv\Scripts\activate.bat (call venv\Scripts\activate.bat) else (echo Создайте website\.venv && pause && exit /b 1) && pip install -q -r requirements.txt && set PORT=8765 && python main.py"

echo.
echo Запущены три окна: API, бот, сайт.
pause
