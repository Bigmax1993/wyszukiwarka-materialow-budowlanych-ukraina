#Requires -Version 5.1

<#

Uruchamia pelny pipeline GU na GitHub Actions (recznie, krok po kroku).



  powershell -ExecutionPolicy Bypass -File scripts\run_full_pipeline_gha.ps1



Opcje:

  -SkipDiscovery   pomin discovery + pierwszy sync

  -SkipBackfill    pomin backfill (sync -> prep -> send po gotowym thu)

  -ForceResend     ponowna wysylka (--force-resend na obu partiach)

  -FullDiscovery   uruchom 5 etapow discovery (mon..fri) po kolei, potem backfill+send

  -StrictDiscovery przy timeout/failure discovery przerwij (domyslnie: kontynuuj gdy jest artefakt pi)

#>

param(

    [switch]$SkipDiscovery,

    [switch]$SkipBackfill,

    [switch]$ForceResend,

    [switch]$FullDiscovery,

    [switch]$StrictDiscovery,

    [string]$DiscoveryRunId = "",

    [string]$ResumeDiscoveryRunId = ""

)



$ErrorActionPreference = "Stop"

$Repo = "Bigmax1993/Wyszukiwarka-partnerow"
$DiscoveryWorkflow = "GU discovery"

$DiscoveryArtifacts = @("de-gu-wyniki-pi")

$script:DiscoveryRunIds = @()



function Get-RunConclusion {

    param([string]$RunId)

    gh run view $RunId -R $Repo --json conclusion -q .conclusion

}



function Get-RunArtifactNames {

    param([string]$RunId)

    $raw = gh api "repos/$Repo/actions/runs/$RunId/artifacts" --jq '.artifacts[].name' 2>$null

    if (-not $raw) { return @() }

    return @($raw -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ })

}



function Test-RunHasDiscoveryArtifact {

    param(

        [string]$RunId,

        [string[]]$AlsoCheckRunIds = @()

    )

    $runs = @($RunId) + @($AlsoCheckRunIds) | Where-Object { $_ } | Select-Object -Unique

    foreach ($rid in $runs) {

        $names = Get-RunArtifactNames $rid

        foreach ($artifact in $DiscoveryArtifacts) {

            if ($names -contains $artifact) { return $true }

        }

    }

    return $false

}



function Wait-GhaRun {

    param(

        [string]$Name,

        [string]$RunId,

        [switch]$ContinueOnDiscoveryArtifact

    )

    Write-Host "URL: https://github.com/$Repo/actions/runs/$RunId"

    gh run watch $RunId -R $Repo --exit-status

    if ($LASTEXITCODE -eq 0) {

        Write-Host "OK: $Name" -ForegroundColor Green

        return

    }

    if ($ContinueOnDiscoveryArtifact -and -not $StrictDiscovery) {

        if (Test-RunHasDiscoveryArtifact -RunId $RunId -AlsoCheckRunIds $script:DiscoveryRunIds) {

            $conclusion = Get-RunConclusion $RunId

            Write-Host ""

            Write-Host "UWAGA: $Name zakonczyl sie jako '$conclusion' (run $RunId, np. timeout 720 min)." -ForegroundColor Yellow

            Write-Host "       Jest artefakt de-gu-wyniki-pi - kontynuuje pipeline (backfill itd.)." -ForegroundColor Yellow

            return

        }

    }

    throw "Workflow $Name nie powiodl sie (run $RunId)"

}



function Invoke-GhaWorkflow {

    param(

        [string]$Name,

        [hashtable]$Fields = @{},

        [switch]$ContinueOnDiscoveryArtifact

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

    Wait-GhaRun -Name $Name -RunId $runId -ContinueOnDiscoveryArtifact:$ContinueOnDiscoveryArtifact

    if ($ContinueOnDiscoveryArtifact) {

        $script:DiscoveryRunIds += $runId

    }

    return $runId

}



$sendFields = @{}

if ($ForceResend) { $sendFields["force_resend"] = "true" }



if ($DiscoveryRunId) {

    Write-Host ""

    Write-Host "=== $DiscoveryWorkflow (juz trwa: $DiscoveryRunId) ===" -ForegroundColor Cyan

    Wait-GhaRun -Name $DiscoveryWorkflow -RunId $DiscoveryRunId -ContinueOnDiscoveryArtifact

    $script:DiscoveryRunIds += $DiscoveryRunId

} elseif (-not $SkipDiscovery) {

    if ($ResumeDiscoveryRunId) {

        Invoke-GhaWorkflow $DiscoveryWorkflow @{

            resume_artifact_run_id = $ResumeDiscoveryRunId

        } -ContinueOnDiscoveryArtifact

    } elseif ($FullDiscovery) {

        foreach ($phase in @("mon", "tue", "wed", "thu", "fri")) {

            Invoke-GhaWorkflow $DiscoveryWorkflow @{ discovery_phase = $phase } -ContinueOnDiscoveryArtifact

        }

    } else {

        Invoke-GhaWorkflow $DiscoveryWorkflow @{} -ContinueOnDiscoveryArtifact

    }

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

