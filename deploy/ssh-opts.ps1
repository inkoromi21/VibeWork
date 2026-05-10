# Общие опции OpenSSH для скриптов деплоя (ключ, без интерактивного пароля).
# Подключается через: . "$PSScriptRoot\ssh-opts.ps1"

function Resolve-VibeWorkSshTarget {
    param(
        [string] $SshAlias = "",
        [string] $RemoteUser = "root",
        [string] $TargetHost = ""
    )
    if ($SshAlias) { return $SshAlias }
    if (-not $TargetHost) { throw "Укажите -TargetHost или -SshAlias (Host из ~/.ssh/config)." }
    return "${RemoteUser}@${TargetHost}"
}

function Get-VibeWorkSshScpSshOpts {
    param(
        [string] $IdentityFile = "",
        [switch] $AllowPasswordPrompt
    )
    $opts = @()
    if ($IdentityFile) {
        $p = (Resolve-Path -LiteralPath $IdentityFile).Path
        if (-not (Test-Path -LiteralPath $p)) { throw "Файл ключа не найден: $IdentityFile" }
        $opts += "-i", $p
        $opts += "-o", "IdentitiesOnly=yes"
    }
    if (-not $AllowPasswordPrompt) {
        $opts += "-o", "BatchMode=yes"
    }
    return $opts
}
