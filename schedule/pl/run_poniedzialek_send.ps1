# PONIEDZIALEK — wysylka partia 1 (PL) 14:00
. "$PSScriptRoot\_common.ps1"
Enter-PlCampaign
$env:SCRAPER_TIMEZONE = "Europe/Warsaw"
Remove-Item Env:DISABLE_SEND_WINDOW -ErrorAction SilentlyContinue
Write-Host "[PL PON] Wysylka partia 1"
python pl_materialy_scraper.py --run-config run_config\pl_materialy.json --send-emails-only --ignore-send-window @args
