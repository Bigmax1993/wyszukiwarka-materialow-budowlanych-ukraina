#Requires -Version 5.1
<#
Pelna bateria testow lokalnych (jak CI + rozszerzenia).

  powershell -ExecutionPolicy Bypass -File scripts\RUN_ALL_TESTS.ps1
#>
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root
$env:KANBUD_PROJECT_ROOT = Join-Path $Root "libs"
$env:PYTHONUTF8 = "1"

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

Test-Step "py_compile (wszystkie .py)" {
    Get-ChildItem -Recurse -Filter *.py |
        Where-Object { $_.FullName -notmatch '\\\.venv\\' } |
        ForEach-Object {
            python -m py_compile $_.FullName
            if ($LASTEXITCODE -ne 0) { throw $_.FullName }
        }
}

Test-Step "smoke --test (DE GU)" { python de_gu_bauunternehmen_scraper.py --test }

Test-Step "smoke --test (UA materialy)" { python ua_materialy_scraper.py --test }

Test-Step "smoke --test (PL materialy)" { python pl_materialy_scraper.py --test }

Test-Step "regresja discovery GU" {
    python -m unittest tests.test_gu_discovery_regression -v
}

Test-Step "regresja UA materialy" {
    python -m unittest tests.test_ua_materialy_regression -v
}

Test-Step "regresja PL materialy" {
    python -m unittest tests.test_pl_materialy_regression -v
}

Test-Step "pytest UA (jednostkowe + integracyjne)" {
    python -m pytest `
        tests/test_ua_oblast_keywords.py `
        tests/test_ua_inquiry_email_uk.py `
        tests/test_ua_claude_inquiry_email.py `
        tests/test_ua_supplier_filter.py `
        tests/test_ua_materialy_integration.py `
        tests/test_ua_email_targeting.py `
        tests/test_ua_claude_contact_extract.py `
        tests/test_ua_contact_pipeline_integration.py `
        -q
}

Test-Step "pytest PL (jednostkowe + integracyjne)" {
    python -m pytest `
        tests/test_pl_inquiry_email_pl.py `
        tests/test_pl_materialy_integration.py `
        tests/test_pl_claude_contact_extract.py `
        tests/test_pl_claude_prompts.py `
        tests/test_pl_cache.py `
        tests/test_contact_extract_utils_pl.py `
        -q
}

Test-Step "ua_oblast_rotation" {
    python -c @"
from pathlib import Path
import tempfile
from ua_oblast_rotation import (
    load_rotation_state, peek_next_oblast, commit_rotation_after_run,
    rotation_state_path, OBLAST_ROTATION_ORDER,
)
d = Path(tempfile.mkdtemp())
p = rotation_state_path(d)
s = load_rotation_state(p)
oblast = peek_next_oblast(s)
assert oblast in OBLAST_ROTATION_ORDER
commit_rotation_after_run(p, s, oblast)
"@
}

Test-Step "ua_materialy — brak zalacznikow i MFG" {
    python -c @"
from ua_materialy_inquiry_email_uk import DEFAULT_INQUIRY_PHONE_UK, build_fixed_material_inquiry_uk
import ua_materialy_scraper as ua
assert ua.get_email_attachments_ua_materialy() == []
assert ua.UA_EMAIL_ALLOW_ATTACHMENTS is False
assert DEFAULT_INQUIRY_PHONE_UK == '+380977091141'
body = build_fixed_material_inquiry_uk()
assert 'mfg' not in body.lower()
assert '+380977091141' in body
"@
}

Test-Step "gu_bundesland_rotation" {
    python -c @"
from pathlib import Path
import tempfile
from gu_bundesland_rotation import (
    load_rotation_state, peek_next_bundesland, commit_rotation_after_run,
    rotation_state_path, BUNDESLAND_ROTATION_ORDER,
)
d = Path(tempfile.mkdtemp())
p = rotation_state_path(d)
s = load_rotation_state(p)
land = peek_next_bundesland(s)
assert land in BUNDESLAND_ROTATION_ORDER
commit_rotation_after_run(p, s, land)
"@
}

Test-Step "mfg_mail_recipients (bez office Cc)" {
    python -c @"
from mfg_mail_recipients import merge_mfg_campaign_cc
cc = merge_mfg_campaign_cc('kontakt@firma.de', '')
assert 'office@mfg-fliesen.de' not in [a.lower() for a in cc]
"@
}

Test-Step "mfg_gu_email_attachment (ID Slides)" {
    python -c @"
from mfg_gu_email_attachment import GOOGLE_SLIDES_PRESENTATION_ID
assert GOOGLE_SLIDES_PRESENTATION_ID == '1kBnp5x0pdgXZSPzVte9e92IUgn2A5gSe'
"@
}

Test-Step "de_gu_keywords Sachsen" {
    python -c @"
from de_gu_keywords import build_discovery_terms
terms = build_discovery_terms(['Sachsen'], max_terms=96)
assert len(terms) >= 10
"@
}

Test-Step "run_config JSON" {
    python -c @"
from pathlib import Path
from scraper_run_config import load_run_config_file
for cfg in ['run_config/welle_nrw_by_bw.json','run_config/bundesland_nrw.json']:
    d = load_run_config_file(cfg, Path('.'))
    assert d['config_type'] == 'de_gu_filialbau'
"@
}

Test-Step "mfg_gu_inquiry_email_de (tylko DE)" {
    python -c @"
from mfg_gu_inquiry_email_de import FIXED_GU_INQUIRY_DE
for w in ('Wspolpraca', 'dziekuje', 'pozdrawiam'):
    assert w.lower() not in FIXED_GU_INQUIRY_DE.lower()
assert 'Sehr geehrte' in FIXED_GU_INQUIRY_DE
"@
}

Test-Step "dry-run wysylki" {
    python de_gu_bauunternehmen_scraper.py --dry-run-email --send-emails-only | Out-Null
}

if (Test-Path "Wyniki\de_gu_bauunternehmen_cache.json") {
    Test-Step "rebuild-from-cache" {
        python de_gu_bauunternehmen_scraper.py --rebuild-from-cache | Out-Null
    }
}

Test-Step "gdrive_upload_wyniki --help" {
    python scripts/gdrive_upload_wyniki.py --help | Out-Null
}

Write-Host "`n======== PODSUMOWANIE ========" -ForegroundColor Yellow
Write-Host "Passed: $($passed.Count)"
$passed | ForEach-Object { Write-Host "  + $_" }
if ($failed.Count) {
    Write-Host "Failed: $($failed.Count)" -ForegroundColor Red
    $failed | ForEach-Object { Write-Host "  - $_" }
    exit 1
}
Write-Host "Wszystkie testy OK" -ForegroundColor Green
