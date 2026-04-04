@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0..\website"
if exist ".venv\Scripts\python.exe" (
  call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\python.exe" (
  call venv\Scripts\activate.bat
) else (
  echo Создайте .venv в папке website
  pause
  exit /b 1
)
pip install -q -r requirements.txt
if not defined PORT set "PORT=8765"
python main.py
pause
