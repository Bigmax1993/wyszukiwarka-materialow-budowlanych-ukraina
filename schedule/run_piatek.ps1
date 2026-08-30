# [Legacy] Przekierowanie na run_poniedzialek_send.ps1 (pon 12:00, partia 1).

. "$PSScriptRoot\_common.ps1"
Write-Warning "run_piatek.ps1 jest legacy — uzyj run_poniedzialek_send.ps1 (pon 12) i run_wtorek.ps1 (wt 9)."
& (Join-Path $PSScriptRoot "run_poniedzialek_send.ps1") @args
