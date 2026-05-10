# From Windows: scp .env, git pull via HTTPS + Fine-grained PAT (no prompt), vps-update.sh.
#
# Before run (do not commit token). PAT only. Repo from git or .git/config; else set:
#   $env:VIBEWORK_GITHUB_PAT = "github_pat_..."
#   $env:VIBEWORK_GITHUB_REPO = "owner/VibeWork"
#   cd d:\fork\VibeWork; .\deploy\vps-full-update.ps1
# SSH key: -IdentityFile "$env:USERPROFILE\.ssh\id_ed25519"
param(
    # SSH target is your VPS, not your PC.
    [string] $TargetHost = "195.208.118.116",
    [string] $RemoteUser = "root",
    [string] $RemoteRoot = "/opt/vibework",
    [string] $Branch = "main",
    [string] $GitHubRepo = "",
    [string] $GitHubUser = "",
    [string] $GitHubPat = "",
    [string] $IdentityFile = ""
)
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

if (-not $GitHubPat) { $GitHubPat = $env:VIBEWORK_GITHUB_PAT }
if (-not $GitHubUser) { $GitHubUser = $env:VIBEWORK_GITHUB_USER }
if (-not $GitHubPat) {
    Write-Error "Set GitHubPat (param -GitHubPat or env VIBEWORK_GITHUB_PAT)."
}

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
    Write-Error "Set -GitHubRepo 'owner/repo' or env VIBEWORK_GITHUB_REPO. (No git on PATH and could not read .git/config.)"
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

$localEnv = Join-Path $repoRoot ".env"
if (-not (Test-Path -LiteralPath $localEnv)) {
    Write-Error "Missing file: $localEnv"
}

$sshExtra = @()
if ($IdentityFile -and (Test-Path -LiteralPath $IdentityFile)) {
    $sshExtra = @("-i", $IdentityFile)
}

$dest = "${RemoteUser}@${TargetHost}:${RemoteRoot}/.env"
Write-Host "1/3 scp .env -> $dest" -ForegroundColor Cyan
& scp @sshExtra $localEnv $dest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$urlQ = ($pullUrl -replace "'", "'\\''")
$remote = "cd '$RemoteRoot' && sed -i 's/\r$//' .env && git pull '${urlQ}' $Branch && sudo bash deploy/vps-update.sh"
Write-Host "2/3 ssh: git pull (PAT) + vps-update.sh" -ForegroundColor Cyan
& ssh @sshExtra "${RemoteUser}@${TargetHost}" $remote
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "3/3 Done: .env, git pull, services restarted." -ForegroundColor Green
