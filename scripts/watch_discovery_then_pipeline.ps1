#Requires -Version 5.1



param(



    [Parameter(Mandatory = $true)]



    [string]$DiscoveryRunId,



    [switch]$ForceResend,



    [switch]$StrictDiscovery



)







$ErrorActionPreference = "Stop"



$Repo = "Bigmax1993/Wyszukiwarka-partnerow"



$Log = Join-Path (Split-Path $PSScriptRoot -Parent) "Wyniki\gha_pipeline_run.log"



$DiscoveryArtifacts = @("de-gu-wyniki-pi")







function Write-Log([string]$Msg) {



    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Msg"



    Write-Host $line



    try {



        Add-Content -Path $Log -Value $line -Encoding UTF8 -ErrorAction Stop



    } catch {



        # log moze byc zablokowany przez inny proces — nie przerywaj pipeline



    }



}







function Get-RunArtifactNames {



    param([string]$RunId)



    $raw = gh api "repos/$Repo/actions/runs/$RunId/artifacts" --jq '.artifacts[].name' 2>$null



    if (-not $raw) { return @() }



    return @($raw -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ })



}







function Test-RunHasDiscoveryArtifact {



    param([string]$RunId)



    $names = Get-RunArtifactNames $RunId



    foreach ($artifact in $DiscoveryArtifacts) {



        if ($names -contains $artifact) { return $true }



    }



    return $false



}







function Wait-Workflow([string]$Name, [string]$RunId) {



    Write-Log "Czekam: $Name (run $RunId)"



    Write-Log "URL: https://github.com/$Repo/actions/runs/$RunId"



    gh run watch $RunId -R $Repo --exit-status



    if ($LASTEXITCODE -eq 0) {



        Write-Log "OK: $Name"



        return



    }



    if (-not $StrictDiscovery -and (Test-RunHasDiscoveryArtifact $RunId)) {



        $conclusion = gh run view $RunId -R $Repo --json conclusion -q .conclusion



        Write-Log "UWAGA: $Name -> $conclusion, ale jest artefakt pi — kontynuuje pipeline."



        return



    }



    throw "Workflow $Name nie powiodl sie (run $RunId)"



}







function Start-Workflow([string]$Name, [hashtable]$Fields = @{}) {



    Write-Log "Start: $Name"



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



    Start-Sleep -Seconds 15



    $runId = gh run list -R $Repo --workflow=$Name -L 1 --json databaseId -q ".[0].databaseId"



    if (-not $runId) { throw "Brak run ID dla $Name" }



    Wait-Workflow $Name $runId



}







Write-Log "=== Pelny pipeline GHA (discovery juz trwa: $DiscoveryRunId) ==="



Wait-Workflow "GU discovery" $DiscoveryRunId



Start-Workflow "Sync wyniki Google Drive"







$pipeArgs = @("-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "run_full_pipeline_gha.ps1"), "-SkipDiscovery")



if ($ForceResend) { $pipeArgs += "-ForceResend" }



if ($StrictDiscovery) { $pipeArgs += "-StrictDiscovery" }



& powershell @pipeArgs







Write-Log "=== Pipeline GHA zakonczony pomyslnie ==="

