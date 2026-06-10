#Requires -Version 5.1
<#
Uruchamia pelny pipeline GU na GitHub Actions (recznie, krok po kroku).

  powershell -ExecutionPolicy Bypass -File scripts\run_full_pipeline_gha.ps1

Opcje:
  -SkipDiscovery   pomin discovery + pierwszy sync
  -SkipBackfill    pomin backfill (sync -> prep -> send po gotowym thu)
  -ForceResend     ponowna wysylka (--force-resend na obu partiach)
#>
param(
    [switch]$SkipDiscovery,
    [switch]$SkipBackfill,
    [switch]$ForceResend,
    [string]$DiscoveryRunId = "",
    [string]$ResumeDiscoveryRunId = ""
)

$ErrorActionPreference = "Stop"
$Repo = "Bigmax1993/Wyszukiwarka-partnerow"

function Invoke-GhaWorkflow {
    param(
        [string]$Name,
        [hashtable]$Fields = @{}
    )
    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    if ($Fields.Count -gt 0) {
        $wfArgs = @()
        foreach ($k in $Fields.Keys) {
            $wfArgs += "-f"
            $wfArgs += "${k}=$($Fields[$k])"
        }
        gh workflow run $Name -R $Repo @wfArgs
    } else {
        gh workflow run $Name -R $Repo
    }
    Start-Sleep -Seconds 12
    $runId = gh run list -R $Repo --workflow=$Name -L 1 --json databaseId -q ".[0].databaseId"
    if (-not $runId) { throw "Brak run ID dla $Name" }
    Write-Host "URL: https://github.com/$Repo/actions/runs/$runId"
    gh run watch $runId -R $Repo --exit-status
    if ($LASTEXITCODE -ne 0) {
        throw "Workflow $Name nie powiodl sie (run $runId)"
    }
    Write-Host "OK: $Name" -ForegroundColor Green
}

$sendFields = @{}
if ($ForceResend) { $sendFields["force_resend"] = "true" }

if ($DiscoveryRunId) {
    Write-Host ""
    Write-Host "=== GU sobota discovery (juz trwa: $DiscoveryRunId) ===" -ForegroundColor Cyan
    Write-Host "URL: https://github.com/$Repo/actions/runs/$DiscoveryRunId"
    gh run watch $DiscoveryRunId -R $Repo --exit-status
    if ($LASTEXITCODE -ne 0) {
        throw "Workflow GU sobota discovery nie powiodl sie (run $DiscoveryRunId)"
    }
    Write-Host "OK: GU sobota discovery" -ForegroundColor Green
} elseif (-not $SkipDiscovery) {
    if ($ResumeDiscoveryRunId) {
        Invoke-GhaWorkflow "GU sobota discovery" @{ resume_artifact_run_id = $ResumeDiscoveryRunId }
    } else {
        Invoke-GhaWorkflow "GU piatek discovery"
        Invoke-GhaWorkflow "GU sobota discovery"
    }
    Invoke-GhaWorkflow "Sync wyniki Google Drive"
}
if (-not $SkipBackfill) {
    Invoke-GhaWorkflow "GU niedziela backfill"
}
Invoke-GhaWorkflow "Sync wyniki Google Drive" @{ artifact_name = "de-gu-wyniki-thu" }
Invoke-GhaWorkflow "GU poniedzialek prep"
Invoke-GhaWorkflow "GU poniedzialek send" $sendFields
Invoke-GhaWorkflow "GU wtorek send" $sendFields

Write-Host ""
Write-Host "Pipeline zakonczony pomyslnie." -ForegroundColor Green
