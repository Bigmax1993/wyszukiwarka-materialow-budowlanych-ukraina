# GitHub Actions — kampania UA

Repozytorium: [wyszukiwarka-materialow-budowlanych-ukraina](https://github.com/Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina)

Kampania PL (osobne repo): [wyszukiwarka-materialow-budowlanych-polska](https://github.com/Bigmax1993/wyszukiwarka-materialow-budowlanych-polska)

> **DE GU:** workflowy `de_gu_*.yml` nie istnieją. Kod w `legacy/de_gu/`.

## Workflowy (9)

| Workflow | Plik | Trigger | Co robi |
|----------|------|---------|---------|
| **Tests** | `tests.yml` | push, PR | smoke UA + pytest + `test_repo_isolation` |
| **CI Deploy** | `ci-deploy.yml` | push | smoke UA + secrets + dry-run maili |
| **UA discovery** | `ua_materialy_pi.yml` | cron, ręcznie | Discovery pon–pt → `ua-materialy-wyniki-pi` |
| **UA niedziela backfill** | `ua_materialy_thu.yml` | cron, ręcznie | Backfill + Excel → `ua-materialy-wyniki-thu` |
| **UA poniedzialek prep** | `ua_materialy_mon.yml` | cron, ręcznie | Rebuild Excel → `ua-materialy-wyniki-mon` |
| **UA poniedzialek send** | `ua_materialy_tue.yml` | cron, ręcznie | Wysyłka partia 1 (300) → `ua-materialy-wyniki-tue` |
| **UA wtorek send** | `ua_materialy_fri.yml` | cron, ręcznie | Wysyłka partia 2 → `ua-materialy-wyniki-fri` |
| **UA sync + przypomnienia** | `ua_materialy_reminders.yml` | cron co 3 dni, ręcznie | IMAP + przypomnienia → `ua-materialy-wyniki-reminders` |
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
| Co 3 dni | sync + przypomnienia | `0 10 1,4,7,10,13,16,19,22,25,28 * *` | **10:00** |

## Odpowiedzi i przypomnienia

Skrypt `ua_sync_replies_and_reminders.py`:

1. Skanuje INBOX (IMAP) i aktualizuje cache (`reply_at`, `has_reply`, ceny…).
2. Wysyła max. **1 przypomnienie** (język ukraiński) do firm bez odpowiedzi — min. **3 dni** po **pierwszym** zapytaniu (`email_sent_at`). Odpowiedź w ciągu tych 3 dni = pominięcie.

```powershell
python ua_sync_replies_and_reminders.py              # podgląd
python ua_sync_replies_and_reminders.py --send       # wysyłka
```

Artefakt GHA: `ua-materialy-wyniki-reminders`.

## Sekrety

| Secret | Wymagany | Opis |
|--------|----------|------|
| `SERPER_API_KEY` | tak | API Serper |
| `ANTHROPIC_API_KEY` | tak | Claude API (discovery + klasyfikacja odpowiedzi IMAP) |
| `MAIL_USER`, `MAIL_PASSWORD` | tak | Gmail SMTP **i** IMAP (ten sam login / hasło aplikacji) |
| `MAIL_SENDER_NAME` | tak | Свінчак Максим (wysyłka + przypomnienia) |
| `GDRIVE_FOLDER_ID_UA` | tak | Folder Drive UA |
| `GDRIVE_OAUTH_*` | zalecany | OAuth upload |
| `GDRIVE_SERVICE_ACCOUNT_JSON` | opcjonalny | Konto usługi |

**Nie ustawiaj** `GDRIVE_FOLDER_ID_PL` w tym repo.

Workflow **UA sync odpowiedzi i przypomnienia**: `MAIL_USER`, `MAIL_PASSWORD`, `MAIL_SENDER_NAME`, `ANTHROPIC_API_KEY`. `IMAP_HOST` opcjonalny (Gmail → `imap.gmail.com` w kodzie).

## Artefakty

```
pon→pi | wt→pi | sro→pi | czw→pi | pt→pi → nd→thu → sync UA → pon prep→mon → pon send→tue → wt send→fri
```

**UA send:** bez załącznika; tel. `+380977091141`.

**Maile spersonalizowane (od 2026-07-13):** Claude wybiera średnią regionalną firmę budowlaną z obwodu discovery i podaje **realny adres** obiektu z bazy `ua_regional_construction_refs.py`. W GHA: `UA_REGIONAL_INQUIRY_EMAIL_FROM=2026-07-13`.

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
gh workflow run "UA sync odpowiedzi i przypomnienia" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina
```

Pełny łańcuch: `scripts/run_full_pipeline_gha.ps1`

Harmonogram PC: [`schedule/ua/PLAN_5_DNI_UA.md`](../schedule/ua/PLAN_5_DNI_UA.md)
