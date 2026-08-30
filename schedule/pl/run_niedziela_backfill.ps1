# NIEDZIELA — backfill (PL) 10:30
. "$PSScriptRoot\_common.ps1"
Enter-PlCampaign
$env:SCRAPER_TIMEZONE = "Europe/Warsaw"
Remove-Item Env:DISABLE_SEND_WINDOW -ErrorAction SilentlyContinue
Write-Host "[PL ND] Weryfikacja www..."
python pl_materialy_scraper.py --run-config run_config\pl_materialy.json --verify-pending-contacts
Write-Host "[PL ND] Backfill e-maili..."
python pl_materialy_scraper.py --run-config run_config\pl_materialy.json --backfill-emails-from-cache
Write-Host "[PL ND] Rebuild Excel..."
python pl_materialy_scraper.py --run-config run_config\pl_materialy.json --rebuild-from-cache
