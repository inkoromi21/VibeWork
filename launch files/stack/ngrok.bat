@echo off
chcp 65001 >nul
cd /d "%~dp0..\.."
REM Ищем ngrok в типовых местах:
REM - tools\ngrok\ngrok.exe (скачан вручную)
REM - miniapp\scripts\bin\ngrok.exe (legacy)
REM - ngrok в PATH (если установлен)
if exist "tools\ngrok\ngrok.exe" (
  "tools\ngrok\ngrok.exe" http 8000
  exit /b 0
)
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
echo или положите ngrok.exe в tools\ngrok\ngrok.exe
echo или скопируйте ngrok.exe в miniapp\scripts\bin\
pause
exit /b 1
