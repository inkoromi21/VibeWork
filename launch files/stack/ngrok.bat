@echo off
chcp 65001 >nul
cd /d "%~dp0..\.."

powershell -NoProfile -Command "& { Write-Host '▶ Запуск ngrok' -ForegroundColor Cyan -NoNewline; Write-Host ''; Write-Host '  Локальный API → публичный HTTPS · UI туннелей: http://127.0.0.1:4040' -ForegroundColor DarkGray }"

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

powershell -NoProfile -Command "& { Write-Host '✗ ngrok не найден' -ForegroundColor Red; Write-Host '  Установка: https://ngrok.com/ · или tools\ngrok\ngrok.exe · или PATH' -ForegroundColor DarkGray }"
pause
exit /b 1
