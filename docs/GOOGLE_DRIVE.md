# Google Drive — wyniki kampanii UA

## Produkcja (UA materiały)

Utwórz folder na Drive (np. **Wyniki wyszukiwania materialow budowlanych Ukraina**) i ustaw secret:

| Secret | Opis |
|--------|------|
| `GDRIVE_FOLDER_ID_UA` | ID folderu Drive dla wyników UA |

### Co ma zostać w folderze

| Plik | Opis |
|------|------|
| `ua_materialy_zbiorczy.xlsx` | **Główny Excel** — unia wierszy ze wszystkich Excel (Drive + artefakty GH), kolumny po polsku, nadpisywany w miejscu |
| `ua_materialy_cache.json` | Cache Serper + kontakty |
| `ua_materialy_oblast_rotation.json` | Stan rotacji obwodów |
| `ua_materialy_scraper.log` | Log |

Pozostałe pliki (stare `ua_materialy_kontakte*.xlsx`, inne artefakty) usuwa workflow **UA cleanup Drive** / skrypt `scripts/cleanup_drive_ua_keep_zbiorczy.py` (zostawia tylko zbiorczy + `.json` + `.log`).

### Excel zbiorczy

| | |
|--|--|
| Skrypt | `scripts/merge_drive_excel_pl.py` |
| Workflow ręczny | `UA merge Excel Drive` (`ua_merge_drive_excel.yml`) |
| Po sync poniedziałkowym | krok w `sync-google-drive-ua.yml` |
| Źródła | Excel z Drive + najnowsze artefakty `ua-materialy-wyniki-{thu,pi,mon,tue,fri,reminders}` |
| Zakres | **tylko wiersze z plików Excel** (bez dopisywania odrzuconych z cache JSON) |
| Arkusze | `Info`, `Kontakty`, `Obwody` — append, unia kolumn, nagłówki PL |
| Upload | `version_xlsx=False` — zawsze ten sam `ua_materialy_zbiorczy.xlsx` |

```powershell
python scripts/merge_drive_excel_pl.py --campaign ua
python scripts/merge_drive_excel_pl.py --local-dir Wyniki --dry-run
```

### Sync i cleanup

| Sposób | Kiedy |
|--------|--------|
| **GitHub Actions** | `Sync wyniki Google Drive UA` — poniedziałek **06:00** Europe/Warsaw (upload `Wyniki/` + przebudowa zbiorczego) |
| **Cleanup** | `UA cleanup Drive (keep zbiorczy/json/log)` — ręcznie, po syncu jeśli wrócą stare Excel |
| **Lokalnie** | `python scripts/gdrive_upload_wyniki.py --campaign ua` |
| **PC + Drive for desktop** | `KANBUD_DATA_DIR` → folder UA na dysku |

Artefakt źródłowy sync: domyślnie najnowszy z kolejki `reminders` → `thu` → `mon` → `tue` → `fri` (albo wymuszony `artifact_name`).

Szczegóły workflow: [`GITHUB_ACTIONS.md`](GITHUB_ACTIONS.md).

---

## Upload z GitHub Actions (OAuth)

```powershell
pip install -r requirements-drive.txt
# OAuth Desktop client JSON → secrets\gdrive-oauth-client.json
python scripts/gdrive_oauth_setup.py
```

Skrypt ustawi secrets `GDRIVE_OAUTH_*`. Kolejne runy CI uploadują na folder UA.

Alternatywa: `GDRIVE_SERVICE_ACCOUNT_JSON` + Shared Drive (`GDRIVE_SHARED_DRIVE_ID`).

---

## Zmienne środowiskowe (lokalnie)

| Zmienna | Opis |
|---------|------|
| `KANBUD_DATA_DIR` | Folder wyników (cache, Excel, wyslane/) |
| `GDRIVE_SERVICE_ACCOUNT_FILE` | Ścieżka do JSON konta usługi |
| `GDRIVE_OAUTH_*` | OAuth Desktop (patrz `gdrive_oauth_setup.py`) |
| `GDRIVE_VERSION_XLSX` | `1` (domyślnie): upload `*_kontakte_YYYY-MM-DD_HHMM.xlsx` bez nadpisywania; zbiorczy i tak jest osobnym plikiem bez wersji |

---

## Legacy DE GU

Folder archiwalny GU: `1tP8oUi72t4EHDbE9GnHFdvfNtNsJe4xf` — patrz [`legacy/README.md`](../legacy/README.md). **Nie** używany przez pipeline UA.
