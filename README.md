# Wyszukiwarka materiałów budowlanych — Ukraina (UA)

Repozytorium: [wyszukiwarka-materialow-budowlanych-ukraina](https://github.com/Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina)

Kampania siostrzana (Polska): [wyszukiwarka-materialow-budowlanych-polska](https://github.com/Bigmax1993/wyszukiwarka-materialow-budowlanych-polska)

**Produkcja:** `ua_materialy` — hurtownie i składy budowlane na Ukrainie (GitHub Actions + opcjonalnie Task Scheduler PC).

**Archiwum:** kampania DE GU w [`legacy/de_gu/`](legacy/README.md) — wyłączona z CI i harmonogramu.

---

## Pipeline

**Serper (gl=ua) → crawl www → Claude verify → Excel → maile UA**

| Moduł | Plik |
|-------|------|
| Scraper | `ua_materialy_scraper.py` |
| Frazy per obwód | `ua_oblast_keywords.py` |
| Rotacja obwodów | `ua_oblast_rotation.py` |
| Filtr dostawców | `ua_materialy_supplier_filter.py` |
| Treść maila UK | `ua_materialy_inquiry_email_uk.py` |

Maile: Claude Sonnet, język ukraiński, **bez załączników**. Nadawca: `MAIL_SENDER_NAME` (domyślnie Свінчак Максим), tel. `+380977091141`.

Przypomnienia: **jedno** — dopiero po **3 dniach** od pierwszego maila; pomijane, jeśli odpowiedź przyszła w tym oknie.

Wyniki lokalne: `Wyniki/ua_materialy_cache.json`, `ua_materialy_kontakte.xlsx`, `ua_materialy_oblast_rotation.json`.

Na Google Drive docelowo: **`ua_materialy_zbiorczy.xlsx`** (unia Excel), cache JSON, rotacja, log — patrz [`docs/GOOGLE_DRIVE.md`](docs/GOOGLE_DRIVE.md).

---

## Szybki start

```powershell
git clone https://github.com/Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina.git
cd wyszukiwarka-materialow-budowlanych-ukraina
pip install -r requirements.txt
$env:KANBUD_PROJECT_ROOT = "$PWD\libs"

python ua_materialy_scraper.py --test
python ua_materialy_scraper.py --rotate-oblast
python ua_materialy_scraper.py --rotation-status
python ua_materialy_scraper.py --run-config run_config\ua_materialy.json --dry-run-email --send-emails-only
```

Skopiuj `.env.example` → `.env` (lokalnie; na CI ustaw [GitHub Secrets](#github-secrets)).

---

## Testy

```powershell
$env:KANBUD_PROJECT_ROOT = "$PWD\libs"
$env:UA_REGIONAL_INQUIRY_EMAIL_FROM = "2026-07-13"
python ua_materialy_scraper.py --test
python -m pytest tests/ -q
python -m pytest legacy/tests/ -q   # opcjonalnie: archiwum DE GU
```

Pełna bateria (compile + smoke + `pytest tests/`): `powershell -ExecutionPolicy Bypass -File scripts\RUN_ALL_TESTS.ps1`  
Z legacy DE: dodaj `-IncludeLegacy`.

CI (`tests.yml`) odpalą smoke + subset pytest (m.in. izolacja PL, crawl, Excel PL, reminder). Lokalnie `pytest tests/` = cały katalog.

`tests/test_repo_isolation.py` — regresja: brak plików kampanii PL w tym repo.

---

## Harmonogram

Szczegóły: [`schedule/ua/PLAN_5_DNI_UA.md`](schedule/ua/PLAN_5_DNI_UA.md)

| Dzień | Godzina (Europe/Warsaw) | GitHub Actions |
|-------|------------------------|----------------|
| Pon–Pt | 17:00 / 15:00 / 19:00 / 20:00 / 16:00 | `UA discovery` |
| Niedziela | 05:30 | `UA niedziela backfill` |
| Poniedziałek | 06:00 / 07:00 / 09:00 | sync Drive → prep → send |
| Wtorek | 09:00 | `UA wtorek send` |

Task Scheduler (PC):

```powershell
powershell -ExecutionPolicy Bypass -File schedule\ua\register_tasks_5_dni.ps1
```

Ręczny pełny pipeline GHA:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_full_pipeline_gha.ps1
```

## Odpowiedzi i przypomnienia (co 3 dni)

```powershell
python ua_sync_replies_and_reminders.py              # podgląd (IMAP + lista kandydatów)
python ua_sync_replies_and_reminders.py --send       # wysyłka przypomnień UA
```

IMAP wymaga tych samych `MAIL_USER` / `MAIL_PASSWORD` co wysyłka. **Jedno** przypomnienie na firmę, min. **3 dni** od pierwszego zapytania; odpowiedź w tym czasie = brak przypomnienia.

---

## Limity

| Limit | Wartość |
|-------|---------|
| Serper | 1000 zapytań / dzień |
| E-mail | 300 / dzień, 2 / domena / dzień (pon + wt) |
| Rotacja | 1 obwód / tydzień (od `rotation_start_date`) |

---

## GitHub Actions

Dokumentacja: [`docs/GITHUB_ACTIONS.md`](docs/GITHUB_ACTIONS.md)

11 workflowów produkcyjnych/docs: discovery/send/reminders + `sync-google-drive-ua.yml`, `ua_merge_drive_excel.yml`, `ua_cleanup_drive.yml`, `tests.yml`, `ci-deploy.yml`.

Concurrency: `ua-pipeline` (discovery/send/backfill). Merge Excel i cleanup Drive poza tą grupą.

### GitHub Secrets

| Secret | Wymagany | Opis |
|--------|----------|------|
| `SERPER_API_KEY` | tak | API Serper |
| `ANTHROPIC_API_KEY` | tak | Claude API (discovery + klasyfikacja odpowiedzi IMAP) |
| `MAIL_USER`, `MAIL_PASSWORD` | tak | Gmail SMTP **i** IMAP (ten sam login / hasło aplikacji) |
| `MAIL_SENDER_NAME` | tak | Свінчак Максим (wysyłka + przypomnienia) |
| `GDRIVE_FOLDER_ID_UA` | tak | Sync Drive pon 06:00 |
| `GDRIVE_OAUTH_*` | zalecany | Upload OAuth |
| `GDRIVE_SERVICE_ACCOUNT_JSON` | opcjonalny | Konto usługi |

**Nie ustawiaj** `GDRIVE_FOLDER_ID_PL` w tym repo.

Google Drive: [`docs/GOOGLE_DRIVE.md`](docs/GOOGLE_DRIVE.md)

---

## Struktura repo

```
├── ua_materialy_scraper.py
├── ua_oblast_rotation.py
├── run_config/ua_materialy.json
├── schedule/ua/
├── legacy/de_gu/              # archiwum DE (wyłączone)
├── .github/workflows/ua_materialy_*.yml
├── docs/GITHUB_ACTIONS.md
├── scripts/run_full_pipeline_gha.ps1
├── tests/test_ua_* + test_repo_isolation.py
└── Wyniki/
```
