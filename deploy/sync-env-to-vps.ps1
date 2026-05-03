# Заливает корневой .env на VPS и перезапускает API (нужен OpenSSH: ssh, scp).
# Запуск из корня репозитория:  .\deploy\sync-env-to-vps.ps1
param(
    [string] $TargetHost = "195.208.118.116",
    [string] $RemoteUser = "root",
    [string] $RemoteEnvPath = "/opt/vibework/.env"
)
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$localEnv = Join-Path $repoRoot ".env"
if (-not (Test-Path -LiteralPath $localEnv)) {
    Write-Error "Нет файла $localEnv — создайте из miniapp/.env.example"
}
$dest = "${RemoteUser}@${TargetHost}:${RemoteEnvPath}"
Write-Host "Копирую .env -> $dest" -ForegroundColor Cyan
& scp $localEnv $dest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$sh = "sed -i 's/\r$//' $RemoteEnvPath && sudo systemctl restart vibework-api && systemctl is-active vibework-api"
Write-Host "Убираю CRLF, перезапуск vibework-api..." -ForegroundColor Cyan
ssh "${RemoteUser}@${TargetHost}" $sh
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Готово." -ForegroundColor Green
