# GitHub Actions — kampania UA

Repozytorium: [wyszukiwarka-materialow-budowlanych-ukraina](https://github.com/Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina)

Kampania PL (osobne repo): [wyszukiwarka-materialow-budowlanych-polska](https://github.com/Bigmax1993/wyszukiwarka-materialow-budowlanych-polska)

> **DE GU:** workflowy `de_gu_*.yml` nie istnieją. Kod w `legacy/de_gu/`.

## Workflowy (8)

| Workflow | Plik | Trigger | Co robi |
|----------|------|---------|---------|
| **Tests** | `tests.yml` | push, PR | smoke UA + pytest + `test_repo_isolation` |
| **CI Deploy** | `ci-deploy.yml` | push | smoke UA + secrets + dry-run maili |
| **UA discovery** | `ua_materialy_pi.yml` | cron, ręcznie | Discovery pon–pt → `ua-materialy-wyniki-pi` |
| **UA niedziela backfill** | `ua_materialy_thu.yml` | cron, ręcznie | Backfill + Excel → `ua-materialy-wyniki-thu` |
| **UA poniedzialek prep** | `ua_materialy_mon.yml` | cron, ręcznie | Rebuild Excel → `ua-materialy-wyniki-mon` |
| **UA poniedzialek send** | `ua_materialy_tue.yml` | cron, ręcznie | Wysyłka partia 1 (300) → `ua-materialy-wyniki-tue` |
| **UA wtorek send** | `ua_materialy_fri.yml` | cron, ręcznie | Wysyłka partia 2 → `ua-materialy-wyniki-fri` |
| **Sync wyniki Google Drive UA** | `sync-google-drive-ua.yml` | cron pon 06:00, ręcznie | Upload `Wyniki/` → folder UA |

## Harmonogram cron (Europe/Warsaw)

| Dzień | Workflow | Cron | Godzina |
|-------|----------|------|---------|
| Poniedziałek | discovery 1 | `0 17 * * 1` | **17:00** |
| Wtorek | discovery 2 | `0 15 * * 2` | **15:00** |
| Środa | discovery 3 | `0 19 * * 3` | **19:00** |
| Czwartek | discovery 4 | `0 20 * * 4` | **20:00** |
| Piątek | discovery 5 | `0 16 * * 5` | **16:00** |
| Niedziela | backfill | `30 5 * * 0` | **05:30** |
| Poniedziałek | sync Drive | `0 6 * * 1` | **06:00** |
| Poniedziałek | prep | `0 7 * * 1` | **07:00** |
| Poniedziałek | send 1 | `0 9 * * 1` | **09:00** |
| Wtorek | send 2 | `0 9 * * 2` | **09:00** |

## Sekrety

| Secret | Wymagany | Opis |
|--------|----------|------|
| `SERPER_API_KEY` | tak | API Serper |
| `ANTHROPIC_API_KEY` | tak | Claude API |
| `MAIL_USER`, `MAIL_PASSWORD` | tak | SMTP |
| `MAIL_SENDER_NAME` | tak | Свінчак Максим |
| `GDRIVE_FOLDER_ID_UA` | tak | Folder Drive UA |
| `GDRIVE_OAUTH_*` | zalecany | OAuth upload |
| `GDRIVE_SERVICE_ACCOUNT_JSON` | opcjonalny | Konto usługi |

**Nie ustawiaj** `GDRIVE_FOLDER_ID_PL` w tym repo.

## Artefakty

```
pon→pi | wt→pi | sro→pi | czw→pi | pt→pi → nd→thu → sync UA → pon prep→mon → pon send→tue → wt send→fri
```

**UA send:** bez załącznika; tel. `+380977091141`.

Concurrency: `ua-pipeline`.

## Ręczne uruchomienie

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

Harmonogram PC: [`schedule/ua/PLAN_5_DNI_UA.md`](../schedule/ua/PLAN_5_DNI_UA.md)
