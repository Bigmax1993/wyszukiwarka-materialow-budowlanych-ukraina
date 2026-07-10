$ErrorActionPreference = "Stop"
if ($env:KANBUD_ALLOW_DE_GU_SCHEDULE -ne "1") {
    Write-Error "DEPRECATED: harmonogram DE GU wylaczony z produkcji. Uzyj odpowiednika w schedule\ua\"
    exit 1
}
# PONIEDZIALEK — przygotowanie (rebuild Excel z cache, bez wysylki).
# Task Scheduler: poniedzialek 07:00 (przed wysylka 09:00)



. "$PSScriptRoot\_common.ps1"

Enter-GuCampaign



$env:SCRAPER_TIMEZONE = "Europe/Warsaw"

Remove-Item Env:DISABLE_SEND_WINDOW -ErrorAction SilentlyContinue



Write-Host "[PONIEDZIALEK] Rebuild Excel z cache (bez wysylki)..."

python de_gu_bauunternehmen_scraper.py --rebuild-from-cache @args

