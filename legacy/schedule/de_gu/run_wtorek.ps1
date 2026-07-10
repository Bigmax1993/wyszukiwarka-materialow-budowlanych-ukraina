$ErrorActionPreference = "Stop"
if ($env:KANBUD_ALLOW_DE_GU_SCHEDULE -ne "1") {
    Write-Error "DEPRECATED: harmonogram DE GU wylaczony z produkcji. Uzyj odpowiednika w schedule\ua\"
    exit 1
}
# WTOREK — wysylka partia 2 (reszta backlogu, limit 300/dzien).

# Task Scheduler: wtorek 09:00



. "$PSScriptRoot\_common.ps1"

Enter-GuCampaign



$env:SCRAPER_TIMEZONE = "Europe/Berlin"

Remove-Item Env:DISABLE_SEND_WINDOW -ErrorAction SilentlyContinue

Remove-Item Env:SEND_WINDOW_START_HOUR -ErrorAction SilentlyContinue

Remove-Item Env:SEND_WINDOW_END_HOUR -ErrorAction SilentlyContinue



Write-Host "[WTOREK] Wysylka maili partia 2 (--send-emails-only, okno 8-18 Berlin)..."

python de_gu_bauunternehmen_scraper.py --send-emails-only @args

