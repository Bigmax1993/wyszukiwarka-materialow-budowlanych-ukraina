# CZWARTEK — discovery czesc 4 (PL) 01:00 (piatek noc)
. "$PSScriptRoot\_common.ps1"
Enter-PlCampaign
$env:SCRAPER_TIMEZONE = "Europe/Warsaw"
Remove-Item Env:DISABLE_SEND_WINDOW -ErrorAction SilentlyContinue
Write-Host "[PL CZW] Discovery czesc 4"
python pl_materialy_scraper.py --run-config run_config\pl_materialy.json --serper-only-discovery --no-auto-email --rotate-wojewodztwo --respect-cache @args
