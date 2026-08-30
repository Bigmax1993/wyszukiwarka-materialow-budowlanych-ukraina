# Plan tygodniowy PL — +5h względem UA (brak nakładania pipeline)

Kampania **PL materiały budowlane** (`pl_materialy_scraper.py`, `run_config/pl_materialy.json`).

Dokumentacja techniczna: [`docs/PL_MATERIALY.md`](../../docs/PL_MATERIALY.md)

Wysyłka **pon 14:00** + **wt 14:00** (2×300 maili/dzień). Maile po polsku, tel. **516513965**.

## Offset względem UA

Każdy etap PL startuje **5 godzin po** odpowiednim etapie UA — oba pipeline mogą działać równolegle na GitHub Actions (`ua-pipeline` / `pl-pipeline`).

| Etap | UA (PL czas) | PL (+5h) |
|------|--------------|----------|
| Pon discovery | 17:00 | **22:00** |
| Wt discovery | 15:00 | **20:00** |
| Śr discovery | 19:00 (śr) | **00:00** (czw) |
| Czw discovery | 20:00 (czw) | **01:00** (pt) |
| Pt discovery | 16:00 | **21:00** |
| Nd backfill | 05:30 | **10:30** |
| Pon sync Drive | 06:00 | **11:00** |
| Pon prep | 07:00 | **12:00** |
| Pon send | 09:00 | **14:00** |
| Wt send | 09:00 | **14:00** |

## Cykl tygodniowy

```
Tydzień N (discovery PL, serper-only):
  pon 22:00 → wt 20:00 → czw 00:00 → pt 01:00 + 21:00   [pl-materialy-wyniki-pi]

Tydzień N-1 (backfill + wysyłka):
  nd 10:30 → pon 11:00 sync → pon 12:00 prep → pon 14:00 send → wt 14:00 send
```

### Discovery (pon–pt)

- `--serper-only-discovery` — kandydaci bez pełnego crawla (status `pending_www_verify`)
- `--respect-cache` (wt–pt) — oszczędza kontakty; row enrichment wygasa po TTL (7 dni)
- Rotacja: 1 województwo / tydzień od `rotation_start_date` w config

### Backfill (niedziela)

- Pełny crawl www, weryfikacja Claude, uzupełnienie telefonów (`+48`) i e-maili
- `--rebuild-from-cache` — odświeżony Excel

## GitHub Actions

| Workflow | Cron (Europe/Warsaw) |
|----------|----------------------|
| PL discovery | `0 22 * * 1`, `0 20 * * 2`, `0 0 * * 4`, `0 1 * * 5`, `0 21 * * 5` |
| PL niedziela backfill | `30 10 * * 0` |
| Sync Drive PL | `0 11 * * 1` |
| PL poniedzialek prep | `0 12 * * 1` |
| PL poniedzialek send | `0 14 * * 1` |
| PL wtorek send | `0 14 * * 2` |

Secret Drive: `GDRIVE_FOLDER_ID_PL` = `1O15CdN0TH8rx74sPP5C1GuYSweX81IGw`

Folder: [PL Materialy — Google Drive](https://drive.google.com/drive/folders/1O15CdN0TH8rx74sPP5C1GuYSweX81IGw?usp=drive_link)

## Pliki wynikowe

| Plik | Opis |
|------|------|
| `pl_materialy_kontakte.xlsx` | Excel kontaktów (append; wersjonowany z datą na Drive) |
| `pl_materialy_cache.json` | Cache Serper, contacts, Claude, crawl |
| `pl_materialy_wojewodztwo_rotation.json` | Stan rotacji województw |

### Cache (`pl_enrichment_v2`)

Po wdrożeniu nowej wersji kodu pierwszy run czyści stare buckety discovery/enrichment/crawl.
TTL domyślnie **7 dni** (`claude_discovery_cache_days` w `run_config/pl_materialy.json`).

## Task Scheduler (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File "schedule\pl\register_tasks_5_dni.ps1"
```

Skrypty w `schedule/pl/`:

| Skrypt | Etap |
|--------|------|
| `run_poniedzialek_discovery.ps1` | Pon discovery (bez `--respect-cache`) |
| `run_wtorek_discovery.ps1` … `run_piatek_discovery.ps1` | Kontynuacja z `--respect-cache` |
| `run_niedziela_backfill.ps1` | Backfill + rebuild |
| `run_poniedzialek_prep.ps1` | Prep przed wysyłką |
| `run_poniedzialek_send.ps1`, `run_wtorek_send.ps1` | Wysyłka maili |

## Testy

```powershell
python pl_materialy_scraper.py --test
python -m unittest tests.test_pl_materialy_regression -v
python -m pytest tests/test_pl_*.py tests/test_contact_extract_utils_pl.py -q
```
