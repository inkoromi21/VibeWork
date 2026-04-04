@echo off
cd /d "%~dp0\..\..\.."
if not exist venv\Scripts\activate.bat (
  echo Создайте venv: python -m venv venv
  exit /b 1
)
call venv\Scripts\activate.bat
pip install -q -r miniapp\requirements.txt
python miniapp\bot\bot.py
