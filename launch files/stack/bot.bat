@echo off

chcp 65001 >nul

setlocal EnableDelayedExpansion

cd /d "%~dp0..\.."



if not exist "venv\Scripts\python.exe" (

  powershell -NoProfile -Command "& { Write-Host '✗ Нет Python venv в корне репозитория' -ForegroundColor Red; Write-Host '  Команда: python -m venv venv' -ForegroundColor DarkGray }"

  pause

  exit /b 1

)



call venv\Scripts\activate.bat

pip install -q -r miniapp\requirements.txt

if not defined HH_USER_AGENT set "HH_USER_AGENT=VibeWork/1.0 (+https://api.hh.ru)"



if not exist ".env" (

  powershell -NoProfile -Command "& { Write-Host '✗ Нет файла .env в корне' -ForegroundColor Red; Write-Host '  создайте .env — TELEGRAM_BOT_TOKEN (docs/ENV.md)' -ForegroundColor DarkGray }"

  pause

  exit /b 1

)



findstr /r /c:"^TELEGRAM_BOT_TOKEN=." .env >nul 2>&1

if errorlevel 1 (

  powershell -NoProfile -Command "& { Write-Host '✗ В .env нет TELEGRAM_BOT_TOKEN' -ForegroundColor Red; Write-Host '  Получите токен у @BotFather в Telegram' -ForegroundColor DarkGray }"

  pause

  exit /b 1

)



python miniapp\bot\bot.py

set EC=!ERRORLEVEL!

if !EC! neq 0 (

  powershell -NoProfile -Command "& { Write-Host '✗ Ошибка запуска бота' -ForegroundColor Red; Write-Host '  Смотрите сообщения Python выше' -ForegroundColor DarkGray }"

)

pause

exit /b !EC!


