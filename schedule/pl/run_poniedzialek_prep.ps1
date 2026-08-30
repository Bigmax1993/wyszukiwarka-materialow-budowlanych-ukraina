# PONIEDZIALEK — prep (PL) 12:00
. "$PSScriptRoot\_common.ps1"
Enter-PlCampaign
$env:SCRAPER_TIMEZONE = "Europe/Warsaw"
Write-Host "[PL PON] Prep rebuild Excel"
python pl_materialy_scraper.py --run-config run_config\pl_materialy.json --rebuild-from-cache @args
