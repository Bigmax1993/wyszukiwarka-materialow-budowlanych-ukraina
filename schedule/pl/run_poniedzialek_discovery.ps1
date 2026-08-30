# PONIEDZIALEK — discovery czesc 1 (PL), +5h wzgledem UA.
. "$PSScriptRoot\_common.ps1"
Enter-PlCampaign
$env:SCRAPER_TIMEZONE = "Europe/Warsaw"
Remove-Item Env:DISABLE_SEND_WINDOW -ErrorAction SilentlyContinue
Write-Host "[PL PON] Discovery czesc 1 (serper-only) 22:00"
python pl_materialy_scraper.py --run-config run_config\pl_materialy.json --serper-only-discovery --no-auto-email --rotate-wojewodztwo @args
