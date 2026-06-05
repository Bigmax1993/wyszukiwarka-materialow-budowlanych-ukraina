# GitHub Actions — kampania GU

Repozytorium: [Wyszukiwarka-partnerow](https://github.com/Bigmax1993/Wyszukiwarka-partnerow)

## Workflowy

| Workflow | Plik | Trigger | Co robi |
|----------|------|---------|---------|
| **Tests** | `tests.yml` | push, PR | `py_compile` + smoke `--test` |
| **CI Deploy** | `ci-deploy.yml` | push | smoke + walidacja secretów + dry-run maili |
| **GU sobota discovery** | `de_gu_wed.yml` | cron, ręcznie | Rotacja 1 Bundesland, kumulacja cache → `de-gu-wyniki-wed` |
| **GU niedziela backfill** | `de_gu_thu.yml` | cron, ręcznie | Backfill + Excel → `de-gu-wyniki-thu` |
| **GU poniedzialek prep** | `de_gu_mon.yml` | cron, ręcznie | Rebuild Excel → `de-gu-wyniki-mon` |
| **GU poniedzialek send** | `de_gu_tue.yml` | cron, ręcznie | Wysyłka partia 1 (do 300) → `de-gu-wyniki-tue` |
| **GU wtorek send** | `de_gu_fri.yml` | cron, ręcznie | Wysyłka partia 2 → `de-gu-wyniki-fri` |
| **Sync wyniki Google Drive** | `sync-google-drive.yml` | po wtorku, cron, ręcznie | Upload `Wyniki/` na Drive |

## Harmonogram cron (UTC → czas PL, CEST)

| Dzień | Workflow | Cron UTC | ≈ czas PL |
|-------|----------|----------|-----------|
| **Sobota** | discovery | `10 18 * * 6` | **20:10** |
| **Niedziela** | backfill | `30 3 * * 0` | **05:30** |
| **Poniedziałek** | prep | `0 6 * * 1` | **08:00** |
| **Poniedziałek** | send 1 | `0 10 * * 1` | **12:00** |
| **Wtorek** | send 2 | `0 7 * * 2` | **09:00** |
| **Wtorek** | sync Drive | `0 12 * * 2` | 14:00 |

Zimą (CET): discovery `10 19 * * 6`, send 1 `0 11 * * 1`.

Wysyłka w oknie **8–18** czasu berlińskiego (bez `DISABLE_SEND_WINDOW` w workflowach send).

## Sekrety

| Secret | Wymagany | Opis |
|--------|----------|------|
| `SERPER_API_KEY` | discovery | API Serper |
| `MAIL_USER` | pon+wt send | Login SMTP |
| `MAIL_PASSWORD` | pon+wt send | Hasło SMTP / IMAP |
| `GDRIVE_OAUTH_CLIENT_ID` | zalecany | OAuth Desktop — upload na „Mój dysk” |
| `GDRIVE_OAUTH_CLIENT_SECRET` | zalecany | OAuth Desktop |
| `GDRIVE_OAUTH_REFRESH_TOKEN` | zalecany | OAuth Desktop |
| `GDRIVE_SERVICE_ACCOUNT_JSON` | opcjonalny | Konto usługi (Shared Drive) |

Setup OAuth: `python scripts/gdrive_oauth_setup.py` — szczegóły w [`GOOGLE_DRIVE.md`](GOOGLE_DRIVE.md).

## Artifacty

```
sobota → wed → niedziela → thu → pon prep → mon → pon send → tue → wt send → fri → sync Drive
```

Sobota discovery pobiera poprzedni `de-gu-wyniki-fri` (kumulacja tygodniowa cache + Excel).

## Załącznik PPTX na runnerze

Workflowy send ustawiają:

`MFG_EMAIL_ATTACHMENT_PATH=assets/campaign/MFG_Referenzliste_Einzelhandel.pptx`

Po zmianie prezentacji w [Google Slides](https://docs.google.com/presentation/d/1Q66gIF_Y6R7r98NYzo2dtQy0Jr_K8mTl/edit) — pobierz PPTX i wgraj do repo w `assets/campaign/`.

## Ręczne uruchomienie

Pełny cykl (PC, czeka na każdy krok):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_full_pipeline_gha.ps1 -ForceResend
```

Pojedyncze kroki (`gh`):

```powershell
gh workflow run "GU sobota discovery" -R Bigmax1993/Wyszukiwarka-partnerow
gh workflow run "GU niedziela backfill" -R Bigmax1993/Wyszukiwarka-partnerow
gh workflow run "GU poniedzialek prep" -R Bigmax1993/Wyszukiwarka-partnerow
gh workflow run "GU poniedzialek send" -R Bigmax1993/Wyszukiwarka-partnerow -f force_resend=true
gh workflow run "GU wtorek send" -R Bigmax1993/Wyszukiwarka-partnerow -f force_resend=true
gh workflow run "Sync wyniki Google Drive" -R Bigmax1993/Wyszukiwarka-partnerow
```

Kolejność: discovery → backfill → prep → pon send → wt send → sync Drive.
