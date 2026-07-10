# Legacy — kampania DE GU

Kampania **DE Generalunternehmer (Filialbau)** wyłączona z produkcji. Aktywny pipeline: **UA** (`ua_materialy_scraper.py`) + **PL** (`pl_materialy_scraper.py`).

## Zawartość

| Ścieżka | Opis |
|---------|------|
| `de_gu/` | Scraper, maile MFG, rotacja Bundesland |
| `run_config/` | JSON kampanii DE (`mfg_gu_de.json`, …) |
| `schedule/de_gu/` | Harmonogram Task Scheduler (wyłączony) |
| `scripts/` | Narzędzia jednorazowe GU |
| `tests/` | Regresja discovery DE |

## Uruchomienie lokalne (tylko audyt)

```powershell
$env:KANBUD_PROJECT_ROOT = "$PWD\libs"
python legacy/de_gu/de_gu_bauunternehmen_scraper.py --test
```

## Uwaga

Moduły `de_gu_keywords.py` i `de_ost_keywords.py` pozostają w katalogu głównym — współdzielone przez `claude_discovery_terms.py` (używane także w pipeline UA). Docelowa refaktoryzacja: osobny moduł fraz dla UA.
