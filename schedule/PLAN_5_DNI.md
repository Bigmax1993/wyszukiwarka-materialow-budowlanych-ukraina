# Plan tygodniowy: środa–piątek discovery → niedziela → poniedziałek → wtorek

Jeden **obrót** na **jedną falę** (1 Bundesland / tydzień, rotacja `--rotate-bundesland`).
Wysyłka **pon 07:00** + **wt 09:00** (2×300 maili/dzień).

## Tabela harmonogramu

| Dzień | Godzina (PL) | Skrypt PC | GitHub Actions |
|-------|--------------|-----------|----------------|
| **Środa** | **20:00** | `run_sroda_discovery.ps1` | `GU discovery` (faza wed) |
| **Czwartek** | **20:00** | `run_czwartek_discovery.ps1` | `GU discovery` (faza thu) |
| **Piątek** | **17:00** | `run_piatek_discovery.ps1` | `GU discovery` (faza fri) |
| **Niedziela** | 06:00 | `run_czwartek.ps1` | `GU niedziela backfill` (~05:30 Actions) |
| **Poniedziałek** | **06:00** | — | `Sync wyniki Google Drive` |
| **Poniedziałek** | 08:00 | `run_poniedzialek_prep.ps1` | `GU poniedzialek prep` |
| **Poniedziałek** | **07:00** | `run_poniedzialek_send.ps1` | `GU poniedzialek send` (partia 1) |
| **Wtorek** | **09:00** | `run_wtorek.ps1` | `GU wtorek send` (partia 2) |

| Dzień | Co robi |
|-------|---------|
| **Środa 20:00** | Discovery część 1 — nowy tydzień, cache z `fri` → `de-gu-wyniki-pi` |
| **Czwartek 20:00** | Discovery część 2 — `--respect-cache`, kumulacja `pi` |
| **Piątek 17:00** | Discovery część 3 — `--respect-cache`, domknięcie tygodnia |
| **Niedziela** | Backfill e-maili + Excel (`de-gu-wyniki-thu`) |
| **Poniedziałek rano** | Rebuild Excel z cache, **bez wysyłki** |
| **Poniedziałek 07:00** | Wysyłka partia 1 (max **300**, okno **8–18** Berlin) |
| **Wtorek 09:00** | Wysyłka partia 2 (kolejne **300** + zaległe) |

W **poniedziałek rano (06:00)**: workflow **Sync wyniki Google Drive** → upload na [folder Drive](../docs/GOOGLE_DRIVE.md) (Excel po niedzielnym backfillu, przed prep 08:00).

## Task Scheduler (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File "schedule\register_tasks_5_dni.ps1"
```

## GitHub Actions — artefakty

```
sro→pi | czw→pi | pt→pi → niedziela→thu → sync Drive → pon prep → mon → pon send → tue → wt send → fri
```

| Workflow | Plik | Cron (Europe/Warsaw) |
|----------|------|----------------------|
| discovery | `de_gu_pi.yml` | `0 20 * * 3` **śro 20:00**, `0 20 * * 4` **czw 20:00**, `0 17 * * 5` **pt 17:00** |
| backfill | `de_gu_thu.yml` | `30 3 * * 0` UTC → **05:30** niedziela |
| prep | `de_gu_mon.yml` | `0 6 * * 1` UTC → **08:00** poniedziałek |
| send 1 | `de_gu_tue.yml` | `0 7 * * 1` → **07:00** poniedziałek |
| send 2 | `de_gu_fri.yml` | `0 7 * * 2` UTC → **09:00** wtorek |
| sync Drive | `sync-google-drive.yml` | `0 6 * * 1` → **06:00** poniedziałek |

**Sync Drive — stała reguła:** pon 06:00 PL, artefakt **`thu`** (backfill); fallback: `mon` → `tue` → `fri`. Ta sama kolejność w `scripts/upload_wyniki_to_drive.ps1`.

**Wznowienie discovery:** `gh workflow run "GU discovery" -R Bigmax1993/Wyszukiwarka-partnerow -f resume_artifact_run_id=RUN_ID`

**Pełny cykl discovery (test):** `-f discovery_phase=wed`, potem `thu`, potem `fri`.
