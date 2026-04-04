@echo off
setlocal
cd /d "%~dp0..\..\.."
set "NEED=0"
if not exist ".env" goto :done_check
findstr /I /R /C:"USE_OLLAMA=1" /C:"USE_OLLAMA=true" /C:"USE_OLLAMA=yes" /C:"USE_OLLAMA=on" ".env" >nul 2>&1 && set "NEED=1"
findstr /I "127.0.0.1:11434" ".env" >nul 2>&1 && set "NEED=1"
findstr /I "localhost:11434" ".env" >nul 2>&1 && set "NEED=1"
:done_check
if "%NEED%"=="0" exit /b 0

curl -s -f "http://127.0.0.1:11434/api/tags" >nul 2>&1
if not errorlevel 1 (
  echo Ollama already on :11434
  exit /b 0
)

echo Starting Ollama (local LLM in .env^)...
where ollama >nul 2>&1
if not errorlevel 1 (
  start "Ollama" cmd /k "ollama serve"
) else (
  if exist "%LOCALAPPDATA%\Programs\Ollama\Ollama.exe" (
    start "" "%LOCALAPPDATA%\Programs\Ollama\Ollama.exe"
  ) else (
    echo Warning: Ollama not found. Install from https://ollama.com
    exit /b 0
  )
)

timeout /t 8 /nobreak >nul
exit /b 0
