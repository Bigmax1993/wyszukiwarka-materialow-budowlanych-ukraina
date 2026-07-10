$ErrorActionPreference = "Stop"
if ($env:KANBUD_ALLOW_DE_GU_SCHEDULE -ne "1") {
    Write-Error "DEPRECATED: harmonogram DE GU wylaczony z produkcji. Uzyj odpowiednika w schedule\ua\"
    exit 1
}
# [Legacy] Wysylka w srode — zastapione: partia 1 pon 12:00, partia 2 wt 09:00



. "$PSScriptRoot\_common.ps1"

Write-Warning "run_sroda_wysylka.ps1 jest legacy — uzyj run_poniedzialek_send.ps1 (pon 12) i run_wtorek.ps1 (wt 9)."

& (Join-Path $PSScriptRoot "run_wtorek.ps1") @args

