# UA — odczyt odpowiedzi IMAP + przypomnienia (co 3 dni).
. "$PSScriptRoot\_common.ps1"
Enter-UaCampaign
$env:SCRAPER_TIMEZONE = "Europe/Warsaw"
Write-Host "[UA] Sync odpowiedzi + przypomnienia (3 dni)"
python ua_sync_replies_and_reminders.py @args
