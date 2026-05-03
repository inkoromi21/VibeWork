# Ждём, пока cloudflared-run.ps1 допишет TELEGRAM_PUBLIC_BASE_URL (quick tunnel), чтобы бот стартовал уже с HTTPS.
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
    [int]$MaxSeconds = 90,
    [int]$IntervalSec = 2
)
$ErrorActionPreference = "SilentlyContinue"
$envFile = Join-Path $RepoRoot ".env"
$deadline = (Get-Date).AddSeconds($MaxSeconds)
while ((Get-Date) -lt $deadline) {
    if (Test-Path $envFile) {
        foreach ($line in Get-Content -LiteralPath $envFile -Encoding UTF8) {
            $t = $line.Trim()
            if (-not $t -or $t.StartsWith("#")) { continue }
            if ($t -match '^\s*TELEGRAM_PUBLIC_BASE_URL\s*=\s*(.+)\s*$') {
                $val = $Matches[1].Trim().TrimEnd('/')
                if ($val -match '^https://[^/]+\.trycloudflare\.com') {
                    if ($val -notmatch '(?i)://(api|www)\.trycloudflare\.com') {
                        Write-Host "[VibeWork] TELEGRAM_PUBLIC_BASE_URL ready ($val)" -ForegroundColor Green
                        exit 0
                    }
                }
            }
        }
    }
    Start-Sleep -Seconds $IntervalSec
}
Write-Host "[VibeWork] Туннель в .env пока не появился за ${MaxSeconds}s — бот всё равно запустится и подхватит URL при следующем сообщении." -ForegroundColor Yellow
exit 0
