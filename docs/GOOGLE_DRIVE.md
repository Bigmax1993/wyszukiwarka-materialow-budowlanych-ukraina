# Google Drive — wyniki kampanii UA

## Produkcja (UA materiały)

Utwórz folder na Drive (np. **UA Materialy Budowlane Wyniki**) i ustaw secret:

| Secret | Opis |
|--------|------|
| `GDRIVE_FOLDER_ID_UA` | ID folderu Drive dla wyników UA |

| Plik / folder | Opis |
|---------------|------|
| `ua_materialy_cache.json` | Cache Serper + kontakty |
| `ua_materialy_kontakte.xlsx` | Excel kontaktów |
| `ua_materialy_scraper.log` | Log |
| `ua_materialy_oblast_rotation.json` | Stan rotacji obwodów |
| `wyslane/*.eml` | Kopie wysłanych maili |

| Sposób | Kiedy |
|--------|--------|
| **GitHub Actions** | `Sync wyniki Google Drive UA` — poniedziałek **06:00** Europe/Warsaw |
| **Lokalnie** | `python scripts/gdrive_upload_wyniki.py --campaign ua` |
| **PC + Drive for desktop** | `KANBUD_DATA_DIR` → folder `UA Materialy Budowlane Wyniki` |

Artefakt źródłowy sync: `ua-materialy-wyniki-thu` (niedzielny backfill). Kolejność fallback: `thu` → `mon` → `tue` → `fri`.

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

---

## Legacy DE GU

Folder archiwalny GU: `1tP8oUi72t4EHDbE9GnHFdvfNtNsJe4xf` — patrz [`legacy/README.md`](../legacy/README.md). **Nie** używany przez pipeline UA.
