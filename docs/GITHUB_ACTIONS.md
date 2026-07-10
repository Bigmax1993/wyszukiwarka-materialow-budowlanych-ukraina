# GitHub Actions — kampanie UA i PL

Repozytorium: [wyszukiwarka-materialow-budowlanych-ukraina](https://github.com/Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina)

> **DE GU (legacy):** workflowy `de_gu_*.yml` **nie istnieją** w tym repo. Kod DE pozostaje lokalnie; harmonogram PC wyłączony — patrz [`schedule/PLAN_5_DNI.md`](../schedule/PLAN_5_DNI.md) (DEPRECATED).

## Workflowy (aktywne)

| Workflow | Plik | Trigger | Co robi |
|----------|------|---------|---------|
| **Tests** | `tests.yml` | push, PR | smoke `--test` (UA, PL) + regresja pytest |
| **CI Deploy** | `ci-deploy.yml` | push | smoke UA+PL + walidacja secretów + dry-run maili UA |



## Harmonogram cron (Europe/Warsaw)



| Dzień | Workflow | Cron | Godzina PL |
|-------|----------|------|------------|
| **Poniedziałek** | discovery część 1 | `0 17 * * 1` | **17:00** |
| **Wtorek** | discovery część 2 | `0 15 * * 2` | **15:00** |
| **Środa** | discovery część 3 | `0 19 * * 3` | **19:00** |
| **Czwartek** | discovery część 4 | `0 20 * * 4` | **20:00** |
| **Piątek** | discovery część 5 | `0 16 * * 5` | **16:00** |
| **Niedziela** | backfill | `30 5 * * 0` | **05:30** |
| **Poniedziałek** | sync Drive | `0 6 * * 1` | **06:00** |
| **Poniedziałek** | prep | `0 7 * * 1` | **07:00** |
| **Poniedziałek** | send 1 | `0 9 * * 1` | **09:00** |
| **Wtorek** | send 2 | `0 9 * * 2` | **09:00** |



Wysyłka w oknie **8–18** czasu berlińskiego (bez `DISABLE_SEND_WINDOW` w workflowach send).



## Sekrety



| Secret | Wymagany | Opis |

|--------|----------|------|

| `SERPER_API_KEY` | discovery | API Serper |

| `ANTHROPIC_API_KEY` | discovery + backfill | Claude API |

Modele Claude (domyślnie w kodzie, opcjonalnie env):

| Zadanie | Tier | Domyślny model | Env |
|---------|------|----------------|-----|
| Frazy Serper, cleanup Excel | `fast` | `claude-haiku-4-5` | `CLAUDE_MODEL_FAST` |
| Weryfikacja www, wyciąganie maili | `verify` | `claude-sonnet-4-6` | `CLAUDE_MODEL_VERIFY` (lub legacy `CLAUDE_MODEL`) |

Setup OAuth: `python scripts/gdrive_oauth_setup.py` — szczegóły w [`GOOGLE_DRIVE.md`](GOOGLE_DRIVE.md).



## Artefakty (UA — kampania produkcyjna)

```
pon→pi | wt→pi | sro→pi | czw→pi | pt→pi → niedziela→thu → sync Drive UA → pon prep→mon → pon send→tue → wt send→fri
```

Szczegóły: sekcja **Kampania UA** poniżej. Skrypt `scripts/run_full_pipeline_gha.ps1` nadal odnosi się do GU (legacy) — do aktualizacji w PR #2.

## Kampania UA (materiały budowlane)

Identyczny harmonogram jak GU — szczegóły: [`schedule/ua/PLAN_5_DNI_UA.md`](../schedule/ua/PLAN_5_DNI_UA.md).

| Workflow | Plik | Trigger | Co robi |
|----------|------|---------|---------|
| **UA discovery** | `ua_materialy_pi.yml` | cron, ręcznie | Discovery pon–pt → `ua-materialy-wyniki-pi` |
| **UA niedziela backfill** | `ua_materialy_thu.yml` | cron, ręcznie | Backfill + Excel → `ua-materialy-wyniki-thu` |
| **UA poniedzialek prep** | `ua_materialy_mon.yml` | cron, ręcznie | Rebuild Excel → `ua-materialy-wyniki-mon` |
| **UA poniedzialek send** | `ua_materialy_tue.yml` | cron, ręcznie | Wysyłka partia 1 (do 300) → `ua-materialy-wyniki-tue` |
| **UA wtorek send** | `ua_materialy_fri.yml` | cron, ręcznie | Wysyłka partia 2 → `ua-materialy-wyniki-fri` |
| **Sync wyniki Google Drive UA** | `sync-google-drive-ua.yml` | cron pon 06:00 PL, ręcznie | Upload `Wyniki/` na folder UA (`GDRIVE_FOLDER_ID_UA`) |

Cron (Europe/Warsaw): **identyczny jak GU** — pon 17:00 … pt 16:00 discovery; nd 05:30 backfill; pon 06:00 sync; pon 07:00 prep; pon 09:00 + wt 09:00 send.

Artefakty:

```
pon→pi | wt→pi | sro→pi | czw→pi | pt→pi → niedziela→thu → sync Drive UA → pon prep→mon → pon send→tue → wt send→fri
```

**UA send:** bez załącznika PPTX; `MAIL_SENDER_NAME` → Свінчак Максим; telefon `+380977091141`.

Dodatkowy secret: `GDRIVE_FOLDER_ID_UA` (osobny folder Drive dla wyników UA).

Ręczne uruchomienie:

```powershell
gh workflow run "UA discovery" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina
gh workflow run "UA discovery" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina -f discovery_phase=mon
gh workflow run "UA niedziela backfill" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina
gh workflow run "Sync wyniki Google Drive UA" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina
gh workflow run "UA poniedzialek prep" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina
gh workflow run "UA poniedzialek send" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina -f force_resend=true
gh workflow run "UA wtorek send" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina -f force_resend=true
```

Concurrency: `ua-pipeline` (równolegle z `pl-pipeline`).

---

## Kampania PL (materiały budowlane)

Szczegóły: [`docs/PL_MATERIALY.md`](PL_MATERIALY.md), harmonogram: [`schedule/pl/PLAN_5_DNI_PL.md`](../schedule/pl/PLAN_5_DNI_PL.md).

| Workflow | Plik | Trigger | Co robi |
|----------|------|---------|---------|
| **PL discovery** | `pl_materialy_pi.yml` | cron, ręcznie | Discovery pon–pt (serper-only) → `pl-materialy-wyniki-pi` |
| **PL niedziela backfill** | `pl_materialy_thu.yml` | cron, ręcznie | Crawl www + Excel → `pl-materialy-wyniki-thu` |
| **PL poniedzialek prep** | `pl_materialy_mon.yml` | cron, ręcznie | Rebuild Excel → `pl-materialy-wyniki-mon` |
| **PL poniedzialek send** | `pl_materialy_tue.yml` | cron, ręcznie | Wysyłka partia 1 → `pl-materialy-wyniki-tue` |
| **PL wtorek send** | `pl_materialy_fri.yml` | cron, ręcznie | Wysyłka partia 2 → `pl-materialy-wyniki-fri` |
| **Sync wyniki Google Drive PL** | `sync-google-drive-pl.yml` | cron pon 11:00 PL, ręcznie | Upload `Wyniki/` → folder PL |

Cron (Europe/Warsaw) — **+5h względem UA** (brak kolizji pipeline):

| Dzień | Workflow | Cron | Godzina PL |
|-------|----------|------|------------|
| Poniedziałek | discovery część 1 | `0 22 * * 1` | **22:00** |
| Wtorek | discovery część 2 | `0 20 * * 2` | **20:00** |
| Czwartek | discovery część 3 | `0 0 * * 4` | **00:00** |
| Piątek | discovery część 4 | `0 1 * * 5` | **01:00** |
| Piątek | discovery część 5 | `0 21 * * 5` | **21:00** |
| Niedziela | backfill | `30 10 * * 0` | **10:30** |
| Poniedziałek | sync Drive PL | `0 11 * * 1` | **11:00** |
| Poniedziałek | prep | `0 12 * * 1` | **12:00** |
| Poniedziałek | send 1 | `0 14 * * 1` | **14:00** |
| Wtorek | send 2 | `0 14 * * 2` | **14:00** |

Artefakty:

```
pon→pi | wt→pi | czw→pi | pt→pi (×2) → niedziela→thu → sync Drive PL → pon prep→mon → pon send→tue → wt send→fri
```

**PL send:** bez załącznika; telefon **516513965**; maile po polsku.

Secret Drive: `GDRIVE_FOLDER_ID_PL` = `1O15CdN0TH8rx74sPP5C1GuYSweX81IGw`

Ręczne uruchomienie:

```powershell
gh workflow run "PL discovery" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina
gh workflow run "PL discovery" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina -f discovery_phase=mon
gh workflow run "PL niedziela backfill" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina
gh workflow run "Sync wyniki Google Drive PL" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina
gh workflow run "PL poniedzialek prep" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina
gh workflow run "PL poniedzialek send" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina -f force_resend=true
gh workflow run "PL wtorek send" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina -f force_resend=true
```

Concurrency: `pl-pipeline` (równolegle z `ua-pipeline`).

Cache: po aktualizacji kodu wersja `pl_enrichment_v2` czyści stare buckety przy pierwszym `load_cache()` — szczegóły w [`PL_MATERIALY.md`](PL_MATERIALY.md#cache-json).

