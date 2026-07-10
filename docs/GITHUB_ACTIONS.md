# GitHub Actions — kampania UA

Repozytorium: [wyszukiwarka-materialow-budowlanych-ukraina](https://github.com/Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina)

> **DE GU (legacy):** workflowy `de_gu_*.yml` **nie istnieją** w tym repo. Kod DE w `legacy/de_gu/`; harmonogram PC wyłączony.

## Workflowy (aktywne)

| Workflow | Plik | Trigger | Co robi |
|----------|------|---------|---------|
| **Tests** | `tests.yml` | push, PR | smoke `--test` UA + regresja pytest |
| **CI Deploy** | `ci-deploy.yml` | push | smoke UA + walidacja secretów + dry-run maili UA |
| **UA discovery** | `ua_materialy_pi.yml` | cron, ręcznie | Discovery pon–pt → `ua-materialy-wyniki-pi` |
| **UA niedziela backfill** | `ua_materialy_thu.yml` | cron, ręcznie | Backfill + Excel → `ua-materialy-wyniki-thu` |
| **UA poniedzialek prep** | `ua_materialy_mon.yml` | cron, ręcznie | Rebuild Excel → `ua-materialy-wyniki-mon` |
| **UA poniedzialek send** | `ua_materialy_tue.yml` | cron, ręcznie | Wysyłka partia 1 (do 300) → `ua-materialy-wyniki-tue` |
| **UA wtorek send** | `ua_materialy_fri.yml` | cron, ręcznie | Wysyłka partia 2 → `ua-materialy-wyniki-fri` |
| **Sync wyniki Google Drive UA** | `sync-google-drive-ua.yml` | cron pon 06:00 PL, ręcznie | Upload `Wyniki/` na folder UA |

## Harmonogram cron (Europe/Warsaw)

| Dzień | Workflow | Cron | Godzina |
|-------|----------|------|---------|
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

## Sekrety

| Secret | Wymagany | Opis |
|--------|----------|------|
| `SERPER_API_KEY` | discovery | API Serper |
| `ANTHROPIC_API_KEY` | discovery + backfill | Claude API |
| `MAIL_USER` | send | SMTP |
| `MAIL_PASSWORD` | send | SMTP |
| `GDRIVE_FOLDER_ID_UA` | sync Drive | ID folderu Drive dla wyników UA |

Setup OAuth: `python scripts/gdrive_oauth_setup.py` — szczegóły w [`GOOGLE_DRIVE.md`](GOOGLE_DRIVE.md).

## Artefakty

```
pon→pi | wt→pi | sro→pi | czw→pi | pt→pi → niedziela→thu → sync Drive UA → pon prep→mon → pon send→tue → wt send→fri
```

**UA send:** bez załącznika PPTX; `MAIL_SENDER_NAME` → Свінчак Максим; telefon `+380977091141`.

Concurrency: `ua-pipeline`.

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

Pełny łańcuch: `scripts/run_full_pipeline_gha.ps1`
