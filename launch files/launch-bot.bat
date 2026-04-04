@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
if not exist "venv\Scripts\python.exe" (
  echo Создайте venv в корне репозитория: python -m venv venv
  pause
  exit /b 1
)
call venv\Scripts\activate.bat
pip install -q -r miniapp\requirements.txt
if not defined HH_USER_AGENT set "HH_USER_AGENT=WibeWork/1.0 (+https://api.hh.ru)"
python miniapp\bot\bot.py
pause
