$ErrorActionPreference = "Stop"
if ($env:KANBUD_ALLOW_DE_GU_SCHEDULE -ne "1") {
    Write-Error "DEPRECATED: harmonogram DE GU wylaczony z produkcji. Uzyj odpowiednika w schedule\ua\"
    exit 1
}
# SRODA — discovery czesc 3 (kontynuacja), bez wysylki maili.

# Task Scheduler: sroda 19:00



. "$PSScriptRoot\_common.ps1"

Enter-GuCampaign



$env:SCRAPER_TIMEZONE = "Europe/Warsaw"

Remove-Item Env:DISABLE_SEND_WINDOW -ErrorAction SilentlyContinue

Remove-Item Env:SCRAPER_IGNORE_SEND_WINDOW -ErrorAction SilentlyContinue



if ($args.Count -gt 0 -and $args[0] -like "run_config\*") {

    $config = $args[0]

    $rest = @($args | Select-Object -Skip 1)

    Write-Host "[SRODA] Discovery (reczny run_config): $config"

    python de_gu_bauunternehmen_scraper.py --run-config $config @rest

} else {

    Write-Host "[SRODA] Discovery czesc 3: kontynuacja (--respect-cache)"

    python de_gu_bauunternehmen_scraper.py --run-config run_config\mfg_gu_de.json --serper-only-discovery --no-auto-email --respect-cache @args

}

