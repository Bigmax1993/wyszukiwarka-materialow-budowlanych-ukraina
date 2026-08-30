# Plan tygodniowy: poniedziałek–piątek discovery → niedziela → poniedziałek → wtorek

Jeden **obrót** na **jedną falę** (1 Bundesland / tydzień, rotacja `--rotate-bundesland`).
Wysyłka **pon 09:00** + **wt 09:00** (2×300 maili/dzień).

## Cykl tygodniowy

```
Tydzień N (discovery):
  pon 17:00 → wt 15:00 → śr 19:00 → czw 20:00 → pt 16:00   [de-gu-wyniki-pi]

Tydzień N (przetwarzanie + wysyłka poprzedniej fali):
  nd 05:30 backfill → pon 06:00 sync Drive → pon 07:00 prep → pon 09:00 send → wt 09:00 send
```

**Poniedziałek ma dwa tryby:** rano (06–09) kończy poprzednią falę (backfill → wysyłka), wieczorem (17:00) startuje **nowy** tydzień discovery (cache z `fri`).

## Tabela harmonogramu

| Dzień | Godzina (PL) | Skrypt PC | GitHub Actions |
|-------|--------------|-----------|----------------|
| **Poniedziałek** | **17:00** | `run_poniedzialek_discovery.ps1` | `GU discovery` (faza mon) |
| **Wtorek** | **15:00** | `run_wtorek_discovery.ps1` | `GU discovery` (faza tue) |
| **Środa** | **19:00** | `run_sroda_discovery.ps1` | `GU discovery` (faza wed) |
| **Czwartek** | **20:00** | `run_czwartek_discovery.ps1` | `GU discovery` (faza thu) |
| **Piątek** | **16:00** | `run_piatek_discovery.ps1` | `GU discovery` (faza fri) |
| **Niedziela** | 06:00 | `run_czwartek.ps1` | `GU niedziela backfill` (~05:30 Actions) |
| **Poniedziałek** | **06:00** | — | `Sync wyniki Google Drive` |
| **Poniedziałek** | **07:00** | `run_poniedzialek_prep.ps1` | `GU poniedzialek prep` |
| **Poniedziałek** | **09:00** | `run_poniedzialek_send.ps1` | `GU poniedzialek send` (partia 1) |
| **Wtorek** | **09:00** | `run_wtorek.ps1` | `GU wtorek send` (partia 2) |

| Dzień | Co robi |
|-------|---------|
| **Poniedziałek 17:00** | Discovery część 1 — nowy tydzień, cache z `fri` → `de-gu-wyniki-pi` |
| **Wtorek 15:00** | Discovery część 2 — `--respect-cache` |
| **Środa 19:00** | Discovery część 3 — `--respect-cache` |
| **Czwartek 20:00** | Discovery część 4 — `--respect-cache` |
| **Piątek 16:00** | Discovery część 5 — `--respect-cache`, domknięcie tygodnia |
| **Niedziela 05:30** | Verify www + backfill e-maili + Excel (`de-gu-wyniki-thu`) z piątkowego `pi` |
| **Poniedziałek 06:00** | Upload Excel na Drive (artefakt `thu`) |
| **Poniedziałek 07:00** | Rebuild Excel z cache (`de-gu-wyniki-mon`), **bez wysyłki** |
| **Poniedziałek 09:00** | Wysyłka partia 1 (max **300**, okno **8–18** Berlin) |
| **Wtorek 09:00** | Wysyłka partia 2 (kolejne **300** + zaległe) |

## Task Scheduler (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File "schedule\register_tasks_5_dni.ps1"
```

## GitHub Actions — artefakty

```
pon→pi | wt→pi | sro→pi | czw→pi | pt→pi → niedziela→thu → sync Drive → pon prep→mon → pon send→tue → wt send→fri
```

| Workflow | Plik | Cron (Europe/Warsaw) |
|----------|------|----------------------|
| discovery | `de_gu_pi.yml` | `0 17 * * 1` **pon 17:00**, `0 15 * * 2` **wt 15:00**, `0 19 * * 3` **śr 19:00**, `0 20 * * 4` **czw 20:00**, `0 16 * * 5` **pt 16:00** |
| backfill | `de_gu_thu.yml` | `30 5 * * 0` → **05:30** niedziela |
| sync Drive | `sync-google-drive.yml` | `0 6 * * 1` → **06:00** poniedziałek |
| prep | `de_gu_mon.yml` | `0 7 * * 1` → **07:00** poniedziałek |
| send 1 | `de_gu_tue.yml` | `0 9 * * 1` → **09:00** poniedziałek |
| send 2 | `de_gu_fri.yml` | `0 9 * * 2` → **09:00** wtorek |

**Sync Drive:** pon 06:00 PL, artefakt **`thu`** (backfill); fallback: `mon` → `tue` → `fri`.

**Wznowienie discovery:** `gh workflow run "GU discovery" -R Bigmax1993/Wyszukiwarka-partnerow -f resume_artifact_run_id=RUN_ID`

**Pełny cykl discovery (test):** `-f discovery_phase=mon`, potem `tue`, `wed`, `thu`, `fri`.

Kampania **UA** (ten sam harmonogram): [`schedule/ua/PLAN_5_DNI_UA.md`](ua/PLAN_5_DNI_UA.md).

**Pełny pipeline po piątku (GHA):**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_full_pipeline_gha.ps1 -SkipDiscovery
```

**Czekaj na discovery i kontynuuj:**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\resume_pipeline_after_pi.ps1 -PiRunId RUN_ID
```
