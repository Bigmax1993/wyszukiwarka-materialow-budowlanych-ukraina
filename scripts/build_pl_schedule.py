# -*- coding: utf-8 -*-
"""Generator workflowów PL (+5h względem UA) i skryptów schedule/pl."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WF = ROOT / ".github" / "workflows"
SCHED = ROOT / "schedule" / "pl"

UA_TO_PL = [
    ("UA ", "PL "),
    ("ua-pipeline", "pl-pipeline"),
    ("ua_materialy", "pl_materialy"),
    ("ua-materialy", "pl-materialy"),
    ("ua_materialy_scraper.py", "pl_materialy_scraper.py"),
    ("run_config/ua_materialy.json", "run_config/pl_materialy.json"),
    ("--rotate-oblast", "--rotate-wojewodztwo"),
    ("GDRIVE_FOLDER_ID_UA", "GDRIVE_FOLDER_ID_PL"),
    ('--campaign ua', "--campaign pl"),
    ("Sync wyniki Google Drive UA", "Sync wyniki Google Drive PL"),
]

CRON_MAP = {
    "ua_materialy_pi.yml": [
        ('cron: "0 17 * * 1"', 'cron: "0 22 * * 1"'),
        ('cron: "0 15 * * 2"', 'cron: "0 20 * * 2"'),
        ('cron: "0 19 * * 3"', 'cron: "0 0 * * 4"'),
        ('cron: "0 20 * * 4"', 'cron: "0 1 * * 5"'),
        ('cron: "0 16 * * 5"', 'cron: "0 21 * * 5"'),
    ],
    "ua_materialy_thu.yml": [('cron: "30 5 * * 0"', 'cron: "30 10 * * 0"')],
    "sync-google-drive-ua.yml": [('cron: "0 6 * * 1"', 'cron: "0 11 * * 1"')],
    "ua_materialy_mon.yml": [('cron: "0 7 * * 1"', 'cron: "0 12 * * 1"')],
    "ua_materialy_tue.yml": [('cron: "0 9 * * 1"', 'cron: "0 14 * * 1"')],
    "ua_materialy_fri.yml": [('cron: "0 9 * * 2"', 'cron: "0 14 * * 2"')],
}

PL_PI_PHASE_BLOCK = r'''          PHASE="${{ github.event_name == 'workflow_dispatch' && inputs.discovery_phase || 'auto' }}"
          if [ "$PHASE" = "auto" ]; then
            HOUR=$(TZ=Europe/Warsaw date +%H)
            DOW=$(TZ=Europe/Warsaw date +%u)
            case "${HOUR}:${DOW}" in
              22:1) PHASE=mon ;;
              20:2) PHASE=tue ;;
              00:4) PHASE=wed ;;
              01:5) PHASE=thu ;;
              21:5) PHASE=fri ;;
              *)
                case "$DOW" in
                  1) PHASE=mon ;;
                  2) PHASE=tue ;;
                  3) PHASE=wed ;;
                  4) PHASE=thu ;;
                  5) PHASE=fri ;;
                  *) PHASE=thu ;;
                esac
                ;;
            esac
          fi'''

OLD_PI_PHASE = re.compile(
    r'          PHASE="\$\{\{ github\.event_name == \'workflow_dispatch\' && inputs\.discovery_phase \|\| \'auto\' \}\}"\n'
    r"          if \[ \"\$PHASE\" = \"auto\" \]; then\n"
    r"            DOW=\$\(TZ=Europe/Warsaw date \+%u\)\n"
    r"            case \"\$DOW\" in\n"
    r"              1\) PHASE=mon ;;\n"
    r"              2\) PHASE=tue ;;\n"
    r"              3\) PHASE=wed ;;\n"
    r"              4\) PHASE=thu ;;\n"
    r"              5\) PHASE=fri ;;\n"
    r"              \*\) PHASE=thu ;;\n"
    r"            esac\n"
    r"          fi",
    re.MULTILINE,
)


def xform(text: str) -> str:
    for a, b in UA_TO_PL:
        text = text.replace(a, b)
    return text


def build_workflows() -> None:
    mapping = {
        "ua_materialy_pi.yml": "pl_materialy_pi.yml",
        "ua_materialy_thu.yml": "pl_materialy_thu.yml",
        "ua_materialy_mon.yml": "pl_materialy_mon.yml",
        "ua_materialy_tue.yml": "pl_materialy_tue.yml",
        "ua_materialy_fri.yml": "pl_materialy_fri.yml",
        "sync-google-drive-ua.yml": "sync-google-drive-pl.yml",
    }
    for src_name, dst_name in mapping.items():
        text = (WF / src_name).read_text(encoding="utf-8")
        text = xform(text)
        for old, new in CRON_MAP.get(src_name, []):
            text = text.replace(old, new)
        if src_name == "ua_materialy_pi.yml":
            text = OLD_PI_PHASE.sub(PL_PI_PHASE_BLOCK, text, count=1)
            text = text.replace("gh workflow run ua_materialy_pi.yml", "gh workflow run pl_materialy_pi.yml")
        if src_name == "sync-google-drive-ua.yml":
            text = text.replace(
                'description: "Opcjonalnie wymus artefakt (np. ua-materialy-wyniki-thu)"',
                'description: "Opcjonalnie wymus artefakt (np. pl-materialy-wyniki-thu)"',
            )
        (WF / dst_name).write_text(text, encoding="utf-8")
        print(f"Wrote {dst_name}")


PS1_SCRIPTS = {
    "run_poniedzialek_discovery.ps1": (
        "# PONIEDZIALEK — discovery czesc 1 (PL), +5h wzgledem UA.\n"
        '. "$PSScriptRoot\\_common.ps1"\n'
        "Enter-PlCampaign\n"
        '$env:SCRAPER_TIMEZONE = "Europe/Warsaw"\n'
        "Remove-Item Env:DISABLE_SEND_WINDOW -ErrorAction SilentlyContinue\n"
        'Write-Host "[PL PON] Discovery czesc 1 (serper-only) 22:00"\n'
        "python pl_materialy_scraper.py --run-config run_config\\pl_materialy.json "
        "--serper-only-discovery --no-auto-email --rotate-wojewodztwo @args\n"
    ),
    "run_wtorek_discovery.ps1": (
        "# WTOREK — discovery czesc 2 (PL) 20:00\n"
        '. "$PSScriptRoot\\_common.ps1"\n'
        "Enter-PlCampaign\n"
        '$env:SCRAPER_TIMEZONE = "Europe/Warsaw"\n'
        "Remove-Item Env:DISABLE_SEND_WINDOW -ErrorAction SilentlyContinue\n"
        'Write-Host "[PL WT] Discovery czesc 2"\n'
        "python pl_materialy_scraper.py --run-config run_config\\pl_materialy.json "
        "--serper-only-discovery --no-auto-email --rotate-wojewodztwo --respect-cache @args\n"
    ),
    "run_sroda_discovery.ps1": (
        "# SRODA — discovery czesc 3 (PL) 00:00 (czwartek noc)\n"
        '. "$PSScriptRoot\\_common.ps1"\n'
        "Enter-PlCampaign\n"
        '$env:SCRAPER_TIMEZONE = "Europe/Warsaw"\n'
        "Remove-Item Env:DISABLE_SEND_WINDOW -ErrorAction SilentlyContinue\n"
        'Write-Host "[PL SR] Discovery czesc 3"\n'
        "python pl_materialy_scraper.py --run-config run_config\\pl_materialy.json "
        "--serper-only-discovery --no-auto-email --rotate-wojewodztwo --respect-cache @args\n"
    ),
    "run_czwartek_discovery.ps1": (
        "# CZWARTEK — discovery czesc 4 (PL) 01:00 (piatek noc)\n"
        '. "$PSScriptRoot\\_common.ps1"\n'
        "Enter-PlCampaign\n"
        '$env:SCRAPER_TIMEZONE = "Europe/Warsaw"\n'
        "Remove-Item Env:DISABLE_SEND_WINDOW -ErrorAction SilentlyContinue\n"
        'Write-Host "[PL CZW] Discovery czesc 4"\n'
        "python pl_materialy_scraper.py --run-config run_config\\pl_materialy.json "
        "--serper-only-discovery --no-auto-email --rotate-wojewodztwo --respect-cache @args\n"
    ),
    "run_piatek_discovery.ps1": (
        "# PIATEK — discovery czesc 5 (PL) 21:00\n"
        '. "$PSScriptRoot\\_common.ps1"\n'
        "Enter-PlCampaign\n"
        '$env:SCRAPER_TIMEZONE = "Europe/Warsaw"\n'
        "Remove-Item Env:DISABLE_SEND_WINDOW -ErrorAction SilentlyContinue\n"
        'Write-Host "[PL PT] Discovery czesc 5"\n'
        "python pl_materialy_scraper.py --run-config run_config\\pl_materialy.json "
        "--serper-only-discovery --no-auto-email --rotate-wojewodztwo --respect-cache @args\n"
    ),
    "run_niedziela_backfill.ps1": (
        "# NIEDZIELA — backfill (PL) 10:30\n"
        '. "$PSScriptRoot\\_common.ps1"\n'
        "Enter-PlCampaign\n"
        '$env:SCRAPER_TIMEZONE = "Europe/Warsaw"\n'
        "Remove-Item Env:DISABLE_SEND_WINDOW -ErrorAction SilentlyContinue\n"
        'Write-Host "[PL ND] Weryfikacja www..."\n'
        "python pl_materialy_scraper.py --run-config run_config\\pl_materialy.json --verify-pending-contacts\n"
        'Write-Host "[PL ND] Backfill e-maili..."\n'
        "python pl_materialy_scraper.py --run-config run_config\\pl_materialy.json --backfill-emails-from-cache\n"
        'Write-Host "[PL ND] Rebuild Excel..."\n'
        "python pl_materialy_scraper.py --run-config run_config\\pl_materialy.json --rebuild-from-cache\n"
    ),
    "run_poniedzialek_prep.ps1": (
        "# PONIEDZIALEK — prep (PL) 12:00\n"
        '. "$PSScriptRoot\\_common.ps1"\n'
        "Enter-PlCampaign\n"
        '$env:SCRAPER_TIMEZONE = "Europe/Warsaw"\n'
        'Write-Host "[PL PON] Prep rebuild Excel"\n'
        "python pl_materialy_scraper.py --run-config run_config\\pl_materialy.json --rebuild-from-cache @args\n"
    ),
    "run_poniedzialek_send.ps1": (
        "# PONIEDZIALEK — wysylka partia 1 (PL) 14:00\n"
        '. "$PSScriptRoot\\_common.ps1"\n'
        "Enter-PlCampaign\n"
        '$env:SCRAPER_TIMEZONE = "Europe/Warsaw"\n'
        "Remove-Item Env:DISABLE_SEND_WINDOW -ErrorAction SilentlyContinue\n"
        'Write-Host "[PL PON] Wysylka partia 1"\n'
        "python pl_materialy_scraper.py --run-config run_config\\pl_materialy.json "
        "--send-emails-only --ignore-send-window @args\n"
    ),
    "run_wtorek_send.ps1": (
        "# WTOREK — wysylka partia 2 (PL) 14:00\n"
        '. "$PSScriptRoot\\_common.ps1"\n'
        "Enter-PlCampaign\n"
        '$env:SCRAPER_TIMEZONE = "Europe/Warsaw"\n'
        "Remove-Item Env:DISABLE_SEND_WINDOW -ErrorAction SilentlyContinue\n"
        'Write-Host "[PL WT] Wysylka partia 2"\n'
        "python pl_materialy_scraper.py --run-config run_config\\pl_materialy.json "
        "--send-emails-only --ignore-send-window @args\n"
    ),
}

COMMON_PS1 = '''$ErrorActionPreference = "Stop"
$script:RepoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$script:PlCampaignDir = $script:RepoRoot
$script:DefaultRunConfig = "run_config\\pl_materialy.json"

function Import-KanbudDotEnv {
    $libs = if ($env:KANBUD_PROJECT_ROOT) { $env:KANBUD_PROJECT_ROOT } else { Join-Path $RepoRoot "libs" }
    $env:KANBUD_PROJECT_ROOT = $libs
    foreach ($dotenv in @((Join-Path $libs ".env"), (Join-Path $RepoRoot ".env"))) {
        if (-not (Test-Path $dotenv)) { continue }
        Get-Content $dotenv | ForEach-Object {
            if ($_ -match '^\\s*#' -or $_ -notmatch '=') { return }
            $n, $v = $_ -split '=', 2
            Set-Item -Path "Env:$($n.Trim())" -Value $v.Trim().Trim('"')
        }
        break
    }
}

function Set-KanbudGoogleDriveDataDir {
    if ($env:KANBUD_DATA_DIR) { return }
    $names = @("PL Materialy Budowlane Wyniki", "Kanbud PL Materialy Wyniki", "pl_materialy_wyniki")
    $bases = @("G:\\My Drive", (Join-Path $env:USERPROFILE "Google Drive\\My Drive"), (Join-Path $env:USERPROFILE "Google Drive"))
    foreach ($base in $bases) {
        if (-not (Test-Path $base)) { continue }
        foreach ($name in $names) {
            $p = Join-Path $base $name
            if (Test-Path $p) { $env:KANBUD_DATA_DIR = $p; return }
        }
    }
}

function Enter-PlCampaign {
    Import-KanbudDotEnv
    Set-KanbudGoogleDriveDataDir
    Set-Location $PlCampaignDir
}
'''

REGISTER_PS1 = '''# Rejestracja zadan Harmonogramu Windows — kampania PL (+5h wzgledem UA).
param([switch]$Unregister)

$ScheduleDir = $PSScriptRoot
$Pwsh = (Get-Command powershell.exe).Source

function Register-WeekdayTask {
    param([string]$Name, [string]$Script, [string]$Weekday, [string]$Time)
    $action = New-ScheduledTaskAction -Execute $Pwsh -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Script`""
    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Weekday -At $Time
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    Register-ScheduledTask -TaskName $Name -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
    Write-Host "OK: $Name -> $Weekday $Time"
}

$tasks = @(
    @{ Name = "Kanbud_PL_Poniedzialek_Discovery"; Script = Join-Path $ScheduleDir "run_poniedzialek_discovery.ps1"; Day = "Monday"; Time = "22:00" }
    @{ Name = "Kanbud_PL_Wtorek_Discovery"; Script = Join-Path $ScheduleDir "run_wtorek_discovery.ps1"; Day = "Tuesday"; Time = "20:00" }
    @{ Name = "Kanbud_PL_Sroda_Discovery"; Script = Join-Path $ScheduleDir "run_sroda_discovery.ps1"; Day = "Thursday"; Time = "00:00" }
    @{ Name = "Kanbud_PL_Czwartek_Discovery"; Script = Join-Path $ScheduleDir "run_czwartek_discovery.ps1"; Day = "Friday"; Time = "01:00" }
    @{ Name = "Kanbud_PL_Piatek_Discovery"; Script = Join-Path $ScheduleDir "run_piatek_discovery.ps1"; Day = "Friday"; Time = "21:00" }
    @{ Name = "Kanbud_PL_Niedziela_Backfill"; Script = Join-Path $ScheduleDir "run_niedziela_backfill.ps1"; Day = "Sunday"; Time = "10:30" }
    @{ Name = "Kanbud_PL_Poniedzialek_Prep"; Script = Join-Path $ScheduleDir "run_poniedzialek_prep.ps1"; Day = "Monday"; Time = "12:00" }
    @{ Name = "Kanbud_PL_Poniedzialek_Send"; Script = Join-Path $ScheduleDir "run_poniedzialek_send.ps1"; Day = "Monday"; Time = "14:00" }
    @{ Name = "Kanbud_PL_Wtorek_Send"; Script = Join-Path $ScheduleDir "run_wtorek_send.ps1"; Day = "Tuesday"; Time = "14:00" }
)

if ($Unregister) {
    foreach ($t in $tasks) {
        Unregister-ScheduledTask -TaskName $t.Name -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "Usunieto: $($t.Name)"
    }
    exit 0
}

foreach ($t in $tasks) { Register-WeekdayTask @t }
Write-Host "Gotowe. Sprawdz taskschd.msc (Kanbud_PL_*)"
'''

PLAN_MD = '''# Plan tygodniowy PL — +5h względem UA (brak nakładania pipeline)

Kampania **PL materiały budowlane** (`pl_materialy_scraper.py`, `run_config/pl_materialy.json`).
Wysyłka **pon 14:00** + **wt 14:00** (2×300 maili/dzień). Maile po polsku, tel. **516513965**.

## Offset względem UA

Każdy etap PL startuje **5 godzin po** odpowiednim etapie UA — oba pipeline mogą działać równolegle na GitHub Actions (`ua-pipeline` / `pl-pipeline`).

| Etap | UA (PL czas) | PL (+5h) |
|------|--------------|----------|
| Pon discovery | 17:00 | **22:00** |
| Wt discovery | 15:00 | **20:00** |
| Śr discovery | 19:00 | **00:00** (noc czw→pt) |
| Czw discovery | 20:00 | **01:00** (pt noc) |
| Pt discovery | 16:00 | **21:00** |
| Nd backfill | 05:30 | **10:30** |
| Pon sync Drive | 06:00 | **11:00** |
| Pon prep | 07:00 | **12:00** |
| Pon send | 09:00 | **14:00** |
| Wt send | 09:00 | **14:00** |

## Cykl tygodniowy

```
Tydzień N (discovery PL):
  pon 22:00 → wt 20:00 → śr 00:00 → czw 01:00 → pt 21:00   [pl-materialy-wyniki-pi]

Tydzień N-1 (backfill + wysyłka):
  nd 10:30 → pon 11:00 sync → pon 12:00 prep → pon 14:00 send → wt 14:00 send
```

## GitHub Actions

| Workflow | Cron (Europe/Warsaw) |
|----------|----------------------|
| PL discovery | `0 22 * * 1`, `0 20 * * 2`, `0 0 * * 4`, `0 1 * * 5`, `0 21 * * 5` |
| PL niedziela backfill | `30 10 * * 0` |
| Sync Drive PL | `0 11 * * 1` |
| PL poniedzialek prep | `0 12 * * 1` |
| PL poniedzialek send | `0 14 * * 1` |
| PL wtorek send | `0 14 * * 2` |

Secret Drive: `GDRIVE_FOLDER_ID_PL`.

## Task Scheduler (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File "schedule\\pl\\register_tasks_5_dni.ps1"
```
'''


def build_schedule() -> None:
    SCHED.mkdir(parents=True, exist_ok=True)
    (SCHED / "_common.ps1").write_text(COMMON_PS1, encoding="utf-8")
    (SCHED / "register_tasks_5_dni.ps1").write_text(REGISTER_PS1, encoding="utf-8")
    (SCHED / "PLAN_5_DNI_PL.md").write_text(PLAN_MD, encoding="utf-8")
    for name, body in PS1_SCRIPTS.items():
        (SCHED / name).write_text(body, encoding="utf-8")
    print(f"Wrote schedule/pl ({len(PS1_SCRIPTS) + 3} files)")


def patch_gdrive() -> None:
    path = ROOT / "scripts" / "gdrive_upload_wyniki.py"
    text = path.read_text(encoding="utf-8")
    text = text.replace('choices=("gu", "ua")', 'choices=("gu", "ua", "pl")')
    text = text.replace("Kampania: gu | ua", "Kampania: gu | ua | pl")
    path.write_text(text, encoding="utf-8")
    print("Patched gdrive_upload_wyniki.py")


def main() -> None:
    build_workflows()
    build_schedule()
    patch_gdrive()


if __name__ == "__main__":
    main()
