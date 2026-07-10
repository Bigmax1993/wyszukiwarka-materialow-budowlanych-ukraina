$ErrorActionPreference = "Stop"
if ($env:KANBUD_ALLOW_DE_GU_SCHEDULE -ne "1") {
    Write-Error "DEPRECATED: harmonogram DE GU wylaczony z produkcji. Uzyj odpowiednika w schedule\ua\"
    exit 1
}
# Przekierowanie na run_sroda_discovery.ps1 (sroda 19:00).
& (Join-Path $PSScriptRoot "run_sroda_discovery.ps1") @args
