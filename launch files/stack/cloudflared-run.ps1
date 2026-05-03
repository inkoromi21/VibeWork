# Cloudflare quick tunnel + TELEGRAM_PUBLIC_BASE_URL in repo .env
$ErrorActionPreference = "Continue"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $RepoRoot

foreach ($n in @("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")) {
    Remove-Item "Env:$n" -ErrorAction SilentlyContinue
}

$Cf = Join-Path $RepoRoot "tools\cloudflared\cloudflared.exe"
if (-not (Test-Path $Cf)) {
    $Cf = Join-Path $env:USERPROFILE "Downloads\cloudflared-windows-amd64.exe"
}
if (-not (Test-Path $Cf)) {
    $Cf = Join-Path $env:USERPROFILE "Downloads\cloudflared.exe"
}
if (-not (Test-Path $Cf)) {
    $w = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($w) { $Cf = $w.Source }
}

if (-not (Test-Path $Cf)) {
    Write-Host "cloudflared not found. Put tools\cloudflared\cloudflared.exe" -ForegroundColor Red
    exit 1
}

Write-Host "Cloudflare Tunnel (quick)" -ForegroundColor Cyan
Write-Host "  Binary: $Cf" -ForegroundColor DarkGray
Write-Host "  URL from log will be saved to .env as TELEGRAM_PUBLIC_BASE_URL" -ForegroundColor DarkGray
Write-Host ""
& $Cf --version
Write-Host ""

$Py = Join-Path $RepoRoot "venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    $Py = "python"
}
$Upsert = Join-Path $RepoRoot "miniapp\scripts\upsert_env.py"
$EnvFile = Join-Path $RepoRoot ".env"

$regionArgs = @()
if ($env:VIBEWORK_CLOUDFLARED_REGION -and $env:VIBEWORK_CLOUDFLARED_REGION.Trim()) {
    $regionArgs = @("--region", $env:VIBEWORK_CLOUDFLARED_REGION.Trim())
}

$written = $false
& $Cf @regionArgs tunnel --url http://127.0.0.1:8000 --protocol http2 --edge-ip-version 4 2>&1 | ForEach-Object {
    $line = [string]$_
    Write-Host $line
    if ($written) {
        return
    }
    if ($line -notmatch '(https://[a-zA-Z0-9.-]+\.trycloudflare\.com)') {
        return
    }
    $u = $Matches[1].TrimEnd('/')
    # Лог cloudflared иногда содержит https://api.trycloudflare.com — это НЕ ваш туннель (530 / wrong host).
    if ($u -match '(?i)://(api|www)\.trycloudflare\.com') {
        return
    }
    & $Py $Upsert $EnvFile "TELEGRAM_PUBLIC_BASE_URL" $u
    if ($LASTEXITCODE -ne 0) {
        return
    }
    $written = $true
    Write-Host ""
    Write-Host "[VibeWork] TELEGRAM_PUBLIC_BASE_URL saved in .env. In Telegram send /start again." -ForegroundColor Green
    Write-Host ""
}

exit $LASTEXITCODE
