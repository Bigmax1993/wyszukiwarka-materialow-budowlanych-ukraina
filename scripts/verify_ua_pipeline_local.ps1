#Requires -Version 5.1
<#
Szybka weryfikacja pipeline UA (jak tests.yml + smoke CLI).

  powershell -ExecutionPolicy Bypass -File scripts\verify_ua_pipeline_local.ps1
#>
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root
$env:KANBUD_PROJECT_ROOT = Join-Path $Root "libs"
$env:PYTHONUTF8 = "1"
$env:DISABLE_SEND_WINDOW = "1"

python ua_materialy_scraper.py --test
python -m unittest tests.test_ua_materialy_regression -v
python -m pytest `
    tests/test_ua_oblast_keywords.py `
    tests/test_ua_inquiry_email_uk.py `
    tests/test_ua_claude_inquiry_email.py `
    tests/test_ua_supplier_filter.py `
    tests/test_ua_materialy_integration.py `
    -q

Write-Host "OK: verify_ua_pipeline_local" -ForegroundColor Green
