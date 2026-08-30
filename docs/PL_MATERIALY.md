# Kampania PL — materiały budowlane (Polska)

Scraper B2B: hurtownie, składy i dystrybutorzy materiałów budowlanych w Polsce.

| Element | Wartość |
|---------|---------|
| Scraper | `pl_materialy_scraper.py` |
| Run config | `run_config/pl_materialy.json` |
| Serper | `gl=pl`, `hl=pl` |
| Cache | `Wyniki/pl_materialy_cache.json` |
| Excel | `Wyniki/pl_materialy_kontakte.xlsx` |
| Rotacja | `Wyniki/pl_materialy_wojewodztwo_rotation.json` |
| Drive | `GDRIVE_FOLDER_ID_PL` → [folder PL](https://drive.google.com/drive/folders/1O15CdN0TH8rx74sPP5C1GuYSweX81IGw) |

Harmonogram: [`schedule/pl/PLAN_5_DNI_PL.md`](../schedule/pl/PLAN_5_DNI_PL.md)  
GitHub Actions: [`docs/GITHUB_ACTIONS.md`](GITHUB_ACTIONS.md#kampania-pl-materiały-budowlane)

---

## Pipeline

```
Serper (gl=pl)
  → filtr dostawcy (pl_materialy_supplier_filter)
  → [pon–pt: serper-only discovery] lub [niedziela: pełny crawl www]
  → Claude page verify (pl_claude_prompts — po polsku)
  → regex kontaktów (+48) + Claude contact extract (pl_claude_contact_extract)
  → Claude row cleanup → Excel
  → [pon/wt: wysyłka maili PL]
```

### Tryb discovery (pon–pt)

Workflow `PL discovery` uruchamia `--serper-only-discovery`:

- Zapis kandydatów do artefaktu `pl-materialy-wyniki-pi`
- Pełna weryfikacja www i crawl — **niedziela** (`PL niedziela backfill`)
- Flagi: `--no-auto-email`, `--rotate-wojewodztwo`

### Tryb backfill (niedziela)

- `--verify-pending-contacts`, `--reverify-all-contacts`
- `--backfill-emails-from-cache`, `--rebuild-from-cache`
- Uzupełnia telefony, e-maile i adresy z crawla www

---

## Moduły

| Moduł | Plik | Rola |
|-------|------|------|
| Scraper | `pl_materialy_scraper.py` | Orchestracja, Serper, cache, Excel |
| Frazy / województwa | `pl_wojewodztwo_keywords.py` | Zapytania Serper per województwo |
| Rotacja | `pl_wojewodztwo_rotation.py` | 1 województwo / tydzień (od `rotation_start_date`) |
| Filtr dostawców | `pl_materialy_supplier_filter.py` | Odrzuca biura, remonty bez hurtu |
| Prompty Claude | `pl_claude_prompts.py` | Page verify, row cleanup, contact extract, maile |
| Contact extract | `pl_claude_contact_extract.py` | Claude + hinty regex (PL, nie DE/UA) |
| Page verify | `pl_claude_page_verify.py` | Weryfikacja strony www |
| Maile | `pl_materialy_inquiry_email_pl.py` | Szablon i podpis PL, tel. **516513965** |
| Normalizacja tel. | `contact_extract_utils.py` | `+48` i `+49` |

---

## Jakość danych (od `pl_enrichment_v2`)

| Obszar | Zachowanie |
|--------|------------|
| **Telefony** | Regex i normalizacja `+48` / `0XX…`; crawl nie kasuje numeru z Serpera |
| **Adres** | Z pola `address` Serpera (nie snippet SEO); snippet tylko w `page_snippet` |
| **Województwo** | Lista 16 województw PL; inferencja z kodu pocztowego (`PL_PLZ_PREFIX_TO_WOJEWODZTWO`) |
| **Prompty Claude** | Wyłącznie po polsku (B2B hurtownie PL) |
| **Geo hints** | `PL_COUNTRY_HINTS` — miasta i domeny `.pl` |

---

## Cache JSON

Plik: `Wyniki/pl_materialy_cache.json`

### Wersjonowanie

- `cache_meta.pl_enrichment_version` = `pl_enrichment_v2`
- Przy pierwszym `load_cache()` po aktualizacji kodu **automatycznie czyszczone** są buckety:
  `serper_discovery`, `claude_row_enrichment`, `claude_contact_extract`, `website_crawl`

### TTL (domyślnie 7 dni)

Sterowane przez `claude_discovery_cache_days` w `run_config/pl_materialy.json` (dziedziczone na):

| Klucz config (opcjonalny) | Bucket |
|---------------------------|--------|
| `claude_discovery_cache_days` | Bazowy TTL |
| `serper_discovery_cache_days` | `serper_discovery` |
| `claude_row_enrichment_cache_days` | `claude_row_enrichment` |
| `website_crawl_cache_days` | `website_crawl` |

### Buckety

| Bucket | Zawartość |
|--------|-----------|
| `serper_discovery` | Wyniki zapytań Serper (z `version` + `at`) |
| `claude_row_enrichment` | Cleanup Excel per URL |
| `claude_contact_extract` | Fallback kontaktów z Claude |
| `website_crawl` | Pełny crawl domeny |
| `contacts` | Enrichment per URL (`adres`, `telefon`, `bundesland`, …) |

### `--respect-cache`

- **Kontakty/www** (wt–pt): nie pobiera ponownie, jeśli URL już w `contacts`
- **Row enrichment**: wygasa po TTL — przeterminowany cleanup jest ponawiany

---

## Uruchomienie lokalne

```powershell
pip install -r requirements.txt
$env:KANBUD_PROJECT_ROOT = "$PWD\libs"
$env:SERPER_API_KEY = "..."
$env:ANTHROPIC_API_KEY = "..."

python pl_materialy_scraper.py --test
python pl_materialy_scraper.py --run-config run_config/pl_materialy.json --serper-only-discovery --no-auto-email --rotate-wojewodztwo
python pl_materialy_scraper.py --run-config run_config/pl_materialy.json --rebuild-from-cache
python pl_materialy_scraper.py --run-config run_config/pl_materialy.json --send-emails-only --dry-run-email
python pl_materialy_scraper.py --rotation-status
```

Task Scheduler:

```powershell
powershell -ExecutionPolicy Bypass -File schedule\pl\register_tasks_5_dni.ps1
```

---

## Testy

```powershell
python pl_materialy_scraper.py --test
python -m unittest tests.test_pl_materialy_regression -v
python -m pytest `
  tests/test_pl_materialy_integration.py `
  tests/test_pl_claude_contact_extract.py `
  tests/test_pl_claude_prompts.py `
  tests/test_pl_cache.py `
  tests/test_contact_extract_utils_pl.py `
  tests/test_pl_inquiry_email_pl.py `
  -v
```

Pełna bateria (wszystkie kampanie): `scripts\RUN_ALL_TESTS.ps1`

---

## Maile

- Język: **polski**
- Claude generuje unikalny list per firma (`enable_claude_inquiry_email`)
- Telefon w podpisie: **516513965** (bez `+380` / `+49`)
- **Bez załączników** — plain text
- Limity: jak GU/UA (300/dzień, 2/domena/dzień)

---

## run_config/pl_materialy.json

| Pole | Domyślnie | Opis |
|------|-----------|------|
| `active_bundeslaender` | 16 województw | Lista aktywnych regionów |
| `min_contacts_target` | 100 | Cel nowych firm / tydzień |
| `geo_filter_enabled` | false | Filtr PLZ/odległość wyłączony |
| `enable_claude_*` | true | Wszystkie etapy Claude włączone |
| `claude_discovery_cache_days` | 7 | TTL cache discovery i enrichment |
| `rotate_wojewodztwo` | true | Rotacja 1 woj./tydzień |
| `rotation_start_date` | 2026-07-14 | Start rotacji województw |

---

## Artefakty GitHub Actions

```
pon 22:00 → wt 20:00 → śr 00:00 → czw 01:00 → pt 21:00  [pl-materialy-wyniki-pi]
nd 10:30 backfill → pon 11:00 sync → pon 12:00 prep → pon 14:00 + wt 14:00 send
```

Concurrency: `pl-pipeline` (równolegle z `ua-pipeline` i `gu-pipeline`).
