# Copies repo root .env to VPS, optional git pull on VPS, restart vibework-api (OpenSSH: scp, ssh).
#
# Default: git pull origin main (credentials must work on VPS: PAT in remote, or credential.helper).
# Private repo: PAT only. Repo slug from git remote, or from .git/config (no git.exe needed), or:
#   $env:VIBEWORK_GITHUB_PAT = "github_pat_..."
#   $env:VIBEWORK_GITHUB_REPO = "owner/VibeWork"
# Fine-grained PAT: GitHub needs your login as HTTPS username (not x-access-token).
# If you omit VIBEWORK_GITHUB_USER, the first part of owner/repo is used (ok for user/VibeWork; for org/repo set the login).
#
# Run from repo root:
#   .\deploy\sync-env-to-vps.ps1
#   .\deploy\sync-env-to-vps.ps1 -NoGitPull
param(
    [string] $TargetHost = "195.208.118.116",
    [string] $RemoteUser = "root",
    [string] $RemoteEnvPath = "/opt/vibework/.env",
    [string] $Branch = "main",
    [string] $GitHubRepo = "",
    [string] $GitHubUser = "",
    [string] $GitHubPat = "",
    [switch] $NoRestart,
    [switch] $NoGitPull
)
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$localEnv = Join-Path $repoRoot ".env"
if (-not (Test-Path -LiteralPath $localEnv)) {
    Write-Error "Missing file: $localEnv"
}

# Do not use Split-Path for /opt/vibework/.env on Windows — it can break the path for SSH/bash.
if ($RemoteEnvPath -match '^(.+)/[^/]+$') {
    $RemoteRoot = $Matches[1]
} else {
    Write-Error "RemoteEnvPath must look like /opt/vibework/.env (got: $RemoteEnvPath)"
}

if (-not $GitHubPat) { $GitHubPat = $env:VIBEWORK_GITHUB_PAT }
if (-not $GitHubUser) { $GitHubUser = $env:VIBEWORK_GITHUB_USER }

$pullUrl = $null
if (-not $NoGitPull -and $GitHubPat) {
    if (-not $GitHubRepo) { $GitHubRepo = $env:VIBEWORK_GITHUB_REPO }
    if (-not $GitHubRepo) {
        $origin = $null
        if (Get-Command git -CommandType Application -ErrorAction SilentlyContinue) {
            $origin = git -C $repoRoot remote get-url origin 2>$null
        }
        if ($origin -match 'github\.com[:/]([^/]+/[^/.]+?)(?:\.git)?/?$') {
            $GitHubRepo = $Matches[1]
        }
    }
    if (-not $GitHubRepo) {
        $cfgPath = Join-Path $repoRoot ".git\config"
        if (Test-Path -LiteralPath $cfgPath) {
            foreach ($line in Get-Content -LiteralPath $cfgPath) {
                if ($line -match '^\s*url\s*=\s*(.+)$') {
                    $u = $Matches[1].Trim()
                    if ($u -match 'github\.com[:/]([^/]+/[^/.]+?)(?:\.git)?/?$') {
                        $GitHubRepo = $Matches[1]
                        break
                    }
                }
            }
        }
    }
    if (-not $GitHubRepo) {
        Write-Error "Set -GitHubRepo 'owner/repo' or env VIBEWORK_GITHUB_REPO. (No git.exe on PATH and could not read .git/config.)"
    }
    $userForUrl = if ($GitHubUser) {
        $GitHubUser
    } elseif ($GitHubRepo -match '^([^/]+)/') {
        $Matches[1]
    } else {
        "x-access-token"
    }
    $encUser = [uri]::EscapeDataString($userForUrl)
    $encPat = [uri]::EscapeDataString($GitHubPat)
    $pullUrl = "https://${encUser}:${encPat}@github.com/${GitHubRepo}.git"
}

$dest = "${RemoteUser}@${TargetHost}:${RemoteEnvPath}"
Write-Host "scp .env -> $dest" -ForegroundColor Cyan
& scp $localEnv $dest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($NoRestart) {
    Write-Host "scp only, skip git pull and restart (NoRestart)." -ForegroundColor Yellow
    exit 0
}

if ($NoGitPull) {
    $pullStep = "true"
} elseif ($pullUrl) {
    $urlQ = ($pullUrl -replace "'", "'\\''")
    $pullStep = "git pull '${urlQ}' $Branch"
} else {
    $pullStep = "git pull origin $Branch"
}

$sh = "cd '$RemoteRoot' && $pullStep && sudo bash deploy/vps-update.sh"
Write-Host "ssh: git pull + deploy/vps-update.sh (venv pip, restart)..." -ForegroundColor Cyan
ssh "${RemoteUser}@${TargetHost}" $sh
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Done." -ForegroundColor Green
