#Requires -Version 5.1
<#
Czeka na zakonczenie GU discovery (sroda) i uruchamia jednorazowy workflow Excel + wysylka.

  powershell -ExecutionPolicy Bypass -File scripts\run_oneoff_wed_excel_send_after_discovery.ps1
  powershell -ExecutionPolicy Bypass -File scripts\run_oneoff_wed_excel_send_after_discovery.ps1 -DiscoveryRunId 27533750486
#>
param(
    [string]$DiscoveryRunId = ""
)

$ErrorActionPreference = "Stop"
$Repo = "Bigmax1993/Wyszukiwarka-partnerow"

if (-not $DiscoveryRunId) {
    $DiscoveryRunId = gh run list -R $Repo --workflow="GU discovery" -L 1 --json databaseId,status -q ".[0].databaseId"
    if (-not $DiscoveryRunId) { throw "Brak run GU discovery" }
}

Write-Host "Czekam na GU discovery (run $DiscoveryRunId)..."
gh run watch $DiscoveryRunId -R $Repo
$conclusion = gh run view $DiscoveryRunId -R $Repo --json conclusion -q .conclusion
Write-Host "Discovery: $conclusion"

$names = @(gh api "repos/$Repo/actions/runs/$DiscoveryRunId/artifacts" --jq '.artifacts[].name' 2>$null)
if ($names -notcontains "de-gu-wyniki-pi") {
    throw "Brak artefaktu de-gu-wyniki-pi w run $DiscoveryRunId"
}

Write-Host "Uruchamiam jednorazowy Excel + wysylka..."
gh workflow run "GU jednorazowo Excel+send po sroda" -R $Repo -f "artifact_run_id=$DiscoveryRunId"
Start-Sleep -Seconds 15
$oneoff = gh run list -R $Repo --workflow="GU jednorazowo Excel+send po sroda" -L 1 --json databaseId -q ".[0].databaseId"
Write-Host "URL: https://github.com/$Repo/actions/runs/$oneoff"
gh run watch $oneoff -R $Repo --exit-status
Write-Host "Gotowe." -ForegroundColor Green
