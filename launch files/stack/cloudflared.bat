@echo off

REM Quick tunnel + запись TELEGRAM_PUBLIC_BASE_URL в .env (см. cloudflared-run.ps1)

chcp 65001 >nul

cd /d "%~dp0..\.."

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0cloudflared-run.ps1"

exit /b %ERRORLEVEL%
