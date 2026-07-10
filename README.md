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

Wyniki: `Wyniki/ua_materialy_cache.json`, `ua_materialy_kontakte.xlsx`, `ua_materialy_oblast_rotation.json`.

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
python ua_materialy_scraper.py --test
python -m unittest tests.test_ua_materialy_regression -v
python -m pytest tests/test_ua_oblast_keywords.py tests/test_ua_inquiry_email_uk.py tests/test_ua_claude_inquiry_email.py tests/test_ua_supplier_filter.py tests/test_ua_materialy_integration.py tests/test_ua_email_targeting.py tests/test_ua_claude_contact_extract.py tests/test_ua_contact_pipeline_integration.py tests/test_repo_isolation.py -q
```

Pełna bateria: `powershell -ExecutionPolicy Bypass -File scripts\RUN_ALL_TESTS.ps1`

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

8 workflowów: `ua_materialy_{pi,thu,mon,tue,fri}.yml`, `sync-google-drive-ua.yml`, `tests.yml`, `ci-deploy.yml`.

Concurrency: `ua-pipeline` (w tym repo).

### GitHub Secrets

| Secret | Wymagany | Opis |
|--------|----------|------|
| `SERPER_API_KEY` | tak | API Serper |
| `ANTHROPIC_API_KEY` | tak | Claude API |
| `MAIL_USER`, `MAIL_PASSWORD` | tak (send) | SMTP / Gmail |
| `MAIL_SENDER_NAME` | tak | Свінчак Максим |
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
