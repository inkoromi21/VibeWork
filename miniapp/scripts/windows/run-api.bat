@echo off
call "%~dp0ensure-ollama.bat"
cd /d "%~dp0\..\..\.."
if not exist venv\Scripts\activate.bat (
  echo Создайте venv: python -m venv venv
  exit /b 1
)
call venv\Scripts\activate.bat
pip install -q -r miniapp\requirements.txt
if not defined HH_USER_AGENT set "HH_USER_AGENT=WibeWork/1.0 (+https://api.hh.ru)"
python miniapp\run.py
