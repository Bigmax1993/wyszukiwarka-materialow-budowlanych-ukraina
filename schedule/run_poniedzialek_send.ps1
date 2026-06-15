# PONIEDZIALEK — wysylka partia 1 (okno 8-18 wg Europe/Berlin, limit 300/dzien).
# Task Scheduler: poniedzialek 09:00 (po prep 07:00)



. "$PSScriptRoot\_common.ps1"

Enter-GuCampaign



$env:SCRAPER_TIMEZONE = "Europe/Berlin"

Remove-Item Env:DISABLE_SEND_WINDOW -ErrorAction SilentlyContinue

Remove-Item Env:SEND_WINDOW_START_HOUR -ErrorAction SilentlyContinue

Remove-Item Env:SEND_WINDOW_END_HOUR -ErrorAction SilentlyContinue



Write-Host "[PONIEDZIALEK] Wysylka maili partia 1 (--send-emails-only, okno 8-18 Berlin)..."

python de_gu_bauunternehmen_scraper.py --send-emails-only @args

