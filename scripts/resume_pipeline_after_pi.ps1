#Requires -Version 5.1
param(
    [string]$PiRunId = "27260899713"
)

$ErrorActionPreference = "Stop"
$Repo = "Bigmax1993/Wyszukiwarka-partnerow"

Write-Host "Czekam na zakonczenie GU discovery (run $PiRunId)..."
gh run watch $PiRunId -R $Repo --exit-status
$watchOk = $LASTEXITCODE -eq 0

if (-not $watchOk) {
    $names = @(gh api "repos/$Repo/actions/runs/$PiRunId/artifacts" --jq '.artifacts[].name' 2>$null)
    if ($names -contains "de-gu-wyniki-pi") {
        Write-Host "Watch/timeout, ale jest artefakt pi - kontynuuje." -ForegroundColor Yellow
    } else {
        throw "Discovery run $PiRunId nie zakonczyl sie pomyslnie i brak artefaktu pi"
    }
}

Write-Host "Piatek discovery zakonczone - uruchamiam reszte pipeline..."
& powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "run_full_pipeline_gha.ps1") -ResumeDiscoveryRunId $PiRunId
