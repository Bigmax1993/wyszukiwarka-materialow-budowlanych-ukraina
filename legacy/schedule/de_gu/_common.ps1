$ErrorActionPreference = "Stop"
$script:RepoRoot = Split-Path $PSScriptRoot -Parent
$script:GuCampaignDir = $script:RepoRoot
$script:DefaultRunConfig = "run_config\mfg_gu_de.json"

function Import-KanbudDotEnv {
    $libs = if ($env:KANBUD_PROJECT_ROOT) { $env:KANBUD_PROJECT_ROOT } else { Join-Path $RepoRoot "libs" }
    $env:KANBUD_PROJECT_ROOT = $libs
    foreach ($dotenv in @((Join-Path $libs ".env"), (Join-Path $RepoRoot ".env"))) {
        if (-not (Test-Path $dotenv)) { continue }
        Get-Content $dotenv | ForEach-Object {
            if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
            $n, $v = $_ -split '=', 2
            Set-Item -Path "Env:$($n.Trim())" -Value $v.Trim().Trim('"')
        }
        break
    }
}

function Set-KanbudGoogleDriveDataDir {
    if ($env:KANBUD_DATA_DIR -or $env:KANBUD_GOOGLE_DRIVE_GU_PATH) { return }
    $names = @("GU Bauunternehmen Wyniki", "Kanbud GU Wyniki", "de_gu_wyniki")
    $bases = @("G:\My Drive", (Join-Path $env:USERPROFILE "Google Drive\My Drive"), (Join-Path $env:USERPROFILE "Google Drive"))
    foreach ($base in $bases) {
        if (-not (Test-Path $base)) { continue }
        foreach ($name in $names) {
            $p = Join-Path $base $name
            if (Test-Path $p) { $env:KANBUD_GOOGLE_DRIVE_GU_PATH = $p; $env:KANBUD_DATA_DIR = $p; return }
        }
    }
}

function Enter-GuCampaign {
    Import-KanbudDotEnv
    Set-KanbudGoogleDriveDataDir
    Set-Location $GuCampaignDir
}
