#Requires -Version 5.1
<#
Pelna bateria testow lokalnych (UA + opcjonalnie legacy).

  powershell -ExecutionPolicy Bypass -File scripts\RUN_ALL_TESTS.ps1
  powershell -ExecutionPolicy Bypass -File scripts\RUN_ALL_TESTS.ps1 -IncludeLegacy
#>
param(
    [switch]$IncludeLegacy
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root
$env:KANBUD_PROJECT_ROOT = Join-Path $Root "libs"
$env:PYTHONUTF8 = "1"
$env:UA_REGIONAL_INQUIRY_EMAIL_FROM = "2026-07-13"
$env:PYTHONPATH = @(
    $Root,
    $env:KANBUD_PROJECT_ROOT,
    (Join-Path $Root "scripts")
) -join [IO.Path]::PathSeparator

$failed = @()
$passed = @()

function Test-Step {
    param([string]$Name, [scriptblock]$Block)
    Write-Host "`n>> $Name" -ForegroundColor Cyan
    try {
        & $Block
        if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw "exit $LASTEXITCODE" }
        $script:passed += $Name
        Write-Host "OK: $Name" -ForegroundColor Green
    } catch {
        $script:failed += "${Name}: $_"
        Write-Host "FAIL: $Name - $_" -ForegroundColor Red
    }
}

Test-Step "py_compile (core)" {
    @(
        "kanbud_bootstrap.py",
        "campaign_data_paths.py",
        "ua_materialy_scraper.py",
        "ua_oblast_keywords.py",
        "ua_sync_replies_and_reminders.py",
        "website_full_crawl.py",
        "http_page_guard.py",
        "ua_excel_pl.py",
        "libs\email_reply_intelligence.py",
        "scripts\merge_drive_excel_pl.py",
        "scripts\cleanup_drive_ua_keep_zbiorczy.py"
    ) | ForEach-Object {
        python -m py_compile $_
        if ($LASTEXITCODE -ne 0) { throw $_ }
    }
}

Test-Step "smoke --test (UA materialy)" { python ua_materialy_scraper.py --test }

Test-Step "pytest tests/ (caly katalog)" {
    python -m pytest tests/ -q
}

if ($IncludeLegacy) {
    Test-Step "pytest legacy/tests/" {
        $env:PYTHONPATH = @(
            $Root,
            $env:KANBUD_PROJECT_ROOT,
            (Join-Path $Root "legacy\de_gu"),
            (Join-Path $Root "scripts")
        ) -join [IO.Path]::PathSeparator
        python -m pytest legacy/tests/ -q
    }
}

Test-Step "gdrive_upload_wyniki --help" {
    python scripts/gdrive_upload_wyniki.py --help | Out-Null
}

Test-Step "merge_drive_excel_pl --help" {
    python scripts/merge_drive_excel_pl.py --help | Out-Null
}

Write-Host "`n======== PODSUMOWANIE ========" -ForegroundColor Yellow
Write-Host "Passed: $($passed.Count)"
$passed | ForEach-Object { Write-Host "  + $_" }
if ($failed.Count) {
    Write-Host "Failed: $($failed.Count)" -ForegroundColor Red
    $failed | ForEach-Object { Write-Host "  - $_" }
    exit 1
}
Write-Host "Wszystkie testy OK (UA)" -ForegroundColor Green
