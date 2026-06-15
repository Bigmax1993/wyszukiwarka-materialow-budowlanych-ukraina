# CZWARTEK — dzień 2: backfill e-maili + przebudowa Excela (bez Serpera, bez wysyłki).
# Task Scheduler: niedziela 06:00
# Jeśli piątek nie skończył discovery — najpierw dokończ: run_piatek_discovery.ps1, potem ten skrypt.

. "$PSScriptRoot\_common.ps1"
Enter-GuCampaign

$env:SCRAPER_TIMEZONE = "Europe/Warsaw"
Remove-Item Env:DISABLE_SEND_WINDOW -ErrorAction SilentlyContinue

Write-Host "[NIEDZIELA] Weryfikacja www (pending ze sro-czw-pt)..."
python de_gu_bauunternehmen_scraper.py --verify-pending-contacts

Write-Host "[NIEDZIELA] Backfill e-maili z cache..."
python de_gu_bauunternehmen_scraper.py --backfill-emails-from-cache

Write-Host "[NIEDZIELA] Rebuild Excel z cache..."
python de_gu_bauunternehmen_scraper.py --rebuild-from-cache
