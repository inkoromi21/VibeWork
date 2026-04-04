@echo off
chcp 65001 >nul
cd /d "%~dp0..\.."
if exist "miniapp\scripts\bin\ngrok.exe" (
  "miniapp\scripts\bin\ngrok.exe" http 8000
  exit /b 0
)
where ngrok >nul 2>&1
if %ERRORLEVEL% equ 0 (
  ngrok http 8000
  exit /b 0
)
echo Установите ngrok: https://ngrok.com/
echo или скопируйте ngrok.exe в miniapp\scripts\bin\
pause
exit /b 1
