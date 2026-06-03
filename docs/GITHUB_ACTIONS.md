# GitHub Actions — kampania GU

Repozytorium: [Wyszukiwarka-partnerow](https://github.com/Bigmax1993/Wyszukiwarka-partnerow)

## Workflowy

| Workflow | Plik | Trigger | Co robi |
|----------|------|---------|---------|
| **Tests** | `tests.yml` | push, PR | smoke `--test`, py_compile |
| **CI Deploy** | `ci-deploy.yml` | push | smoke + walidacja secretów + dry-run maili |
| **GU sroda discovery** | `de_gu_wed.yml` | cron, ręcznie | Serper + www → artifact `de-gu-wyniki-wed` |
| **GU czwartek backfill** | `de_gu_thu.yml` | cron, ręcznie | Pobiera artifact środy → backfill + Excel → `de-gu-wyniki-thu` |
| **GU piatek send** | `de_gu_fri.yml` | cron, ręcznie | Pobiera artifact czwartku → wysyłka SMTP → `de-gu-wyniki-fri` |
| **Sync wyniki Google Drive** | `sync-google-drive.yml` | po piątku, cron pt 12:00 UTC, ręcznie | Upload `Wyniki/` na Drive |

## Harmonogram cron (UTC → czas PL)

GitHub Actions używa **UTC**. Poniżej dla **CEST** (lato, UTC+2):

| Dzień | Workflow | Cron UTC | ≈ czas PL |
|-------|----------|----------|-----------|
| **Środa** | discovery | `10 18 * * 3` | **20:10** |
| **Czwartek** | backfill | `30 3 * * 4` | **05:30** |
| **Piątek** | send | `0 7 * * 5` | **09:00** |
| **Piątek** | sync Drive | `0 12 * * 5` | 14:00 |

**Uwaga:** Task Scheduler na PC ma czwartek o **06:00** — GitHub uruchamia backfill o **05:30** (różnica 30 min). Zimą (CET) przesuń cron środy na `10 19 * * 3` (20:10 PL).

## Sekrety (Settings → Secrets → Actions)

| Secret | Wymagany | Opis |
|--------|----------|------|
| `SERPER_API_KEY` | tak | API Serper |
| `MAIL_USER` | tak (piątek) | Login SMTP |
| `MAIL_PASSWORD` | tak (piątek) | Hasło SMTP / IMAP |
| `GDRIVE_SERVICE_ACCOUNT_JSON` | opcjonalny | **Cały** JSON konta usługi Google |

**Nie potrzeba:** `KANBUD_PROJECT_ROOT` (w repo jest `libs/`), `GOOGLE_AI_STUDIO_API_KEY` (Gemini wyłączone w GU).

Zmienne w `de_gu_fri.yml` (nie secrets): `SMTP_HOST`, `IMAP_HOST`, `SMTP_PORT`, …

## Artifacty między dniami

Runner GitHub **nie ma** cache z PC. Pipeline przenosi dane przez artifacty:

```
środa  → de-gu-wyniki-wed  → czwartek → de-gu-wyniki-thu → piątek → de-gu-wyniki-fri → sync Drive
```

Przed pierwszym tygodniem artifacty nie istnieją — to normalne.

## Ręczne uruchomienie

Actions → wybierz workflow → **Run workflow**.

Lub CLI:

```powershell
gh workflow run "GU sroda discovery" -R Bigmax1993/Wyszukiwarka-partnerow
gh workflow run "Sync wyniki Google Drive" -R Bigmax1993/Wyszukiwarka-partnerow
gh run list -R Bigmax1993/Wyszukiwarka-partnerow
```

## Walidacja po deploy

Po push na `master` automatycznie: **Tests** + **CI Deploy**.

Sprawdź: https://github.com/Bigmax1993/Wyszukiwarka-partnerow/actions
