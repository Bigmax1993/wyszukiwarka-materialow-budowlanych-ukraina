# Wyszukiwarka partnerów / materiałów budowlanych



Repozytorium: [Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina](https://github.com/Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina)

**Kampanie produkcyjne:** UA materiały + PL materiały (GitHub Actions). DE GU — kod legacy, wyłączony z harmonogramu PC i CI.



## Kampanie



| Kampania | Scraper | Opis |
|----------|---------|------|
| **DE GU** (archiwum) | `legacy/de_gu/de_gu_bauunternehmen_scraper.py` | Wyłączony — patrz [`legacy/README.md`](legacy/README.md) |
| **UA materiały** | `ua_materialy_scraper.py` | Hurtownie / składy budmatów Ukraina |
| **PL materiały** | `pl_materialy_scraper.py` | Hurtownie / składy budmatów Polska |



### UA — materiały budowlane (Ukraina)



Pipeline: **Serper (gl=ua) → crawl www → Claude verify → Excel → maile UA**.



| Moduł | Plik |
|-------|------|
| Scraper | `ua_materialy_scraper.py` |
| Frazy per obwód | `ua_oblast_keywords.py` |
| Rotacja obwodów | `ua_oblast_rotation.py` |
| Filtr dostawców | `ua_materialy_supplier_filter.py` |
| Treść maila UK | `ua_materialy_inquiry_email_uk.py` |



```powershell
pip install -r requirements.txt
$env:KANBUD_PROJECT_ROOT = "$PWD\libs"

python ua_materialy_scraper.py --test
python ua_materialy_scraper.py --rotate-oblast
python ua_materialy_scraper.py --rotation-status
python ua_materialy_scraper.py --oblast Kyiv,Lvivska
python ua_materialy_scraper.py --run-config run_config\ua_kyiv_test.json
python ua_materialy_scraper.py --dry-run-email --send-emails-only
```

Testy UA:

```powershell
python ua_materialy_scraper.py --test
python -m unittest tests.test_ua_materialy_regression -v
python -m pytest tests/test_ua_oblast_keywords.py tests/test_ua_inquiry_email_uk.py tests/test_ua_claude_inquiry_email.py tests/test_ua_supplier_filter.py tests/test_ua_materialy_integration.py -q
```

Maile: **Claude Sonnet** generuje unikalny list ukraiński per firma (nazwa, asortyment ze strony, region). Wymaga `ANTHROPIC_API_KEY`. Wyłączenie: `ENABLE_CLAUDE_INQUIRY_EMAIL=0` w run_config lub env. **Bez załączników** — tylko plain-text.

Nadawca i podpis w mailach UA: `MAIL_SENDER_NAME` (domyślnie Свінчак Максим), telefon `+380977091141` oraz opcjonalnie `INQUIRY_COMPANY_NAME`, `INQUIRY_WEBSITE` w `.env`.



Wyniki: `Wyniki/ua_materialy_cache.json`, `ua_materialy_kontakte.xlsx`, `ua_materialy_oblast_rotation.json`.

Harmonogram tygodnia (identyczny jak DE GU): [`schedule/ua/PLAN_5_DNI_UA.md`](schedule/ua/PLAN_5_DNI_UA.md)

| Dzień | Godzina (PL) | PC | GitHub Actions |
|-------|--------------|-----|----------------|
| **Pon–Pt** | 17:00 / 15:00 / 19:00 / 20:00 / 16:00 | `schedule/ua/run_*_discovery.ps1` | `UA discovery` |
| **Niedziela** | 06:00 | `schedule/ua/run_niedziela_backfill.ps1` | `UA niedziela backfill` (~05:30) |
| **Poniedziałek** | 06:00 / 07:00 / 09:00 | prep + send | `Sync wyniki Google Drive UA` → prep → send |
| **Wtorek** | 09:00 | `schedule/ua/run_wtorek_send.ps1` | `UA wtorek send` |

Task Scheduler UA:

```powershell
powershell -ExecutionPolicy Bypass -File schedule\ua\register_tasks_5_dni.ps1
```

---

### PL — materiały budowlane (Polska)

Pipeline: **Serper (gl=pl) → crawl www → Claude verify (PL) → Excel → maile PL**.

Szczegóły: [`docs/PL_MATERIALY.md`](docs/PL_MATERIALY.md)

| Moduł | Plik |
|-------|------|
| Scraper | `pl_materialy_scraper.py` |
| Frazy per województwo | `pl_wojewodztwo_keywords.py` |
| Rotacja województw | `pl_wojewodztwo_rotation.py` |
| Filtr dostawców | `pl_materialy_supplier_filter.py` |
| Prompty Claude PL | `pl_claude_prompts.py` |
| Contact extract PL | `pl_claude_contact_extract.py` |
| Treść maila PL | `pl_materialy_inquiry_email_pl.py` |

```powershell
python pl_materialy_scraper.py --test
python pl_materialy_scraper.py --run-config run_config\pl_materialy.json --serper-only-discovery --no-auto-email --rotate-wojewodztwo
python pl_materialy_scraper.py --run-config run_config\pl_materialy.json --rebuild-from-cache
python pl_materialy_scraper.py --rotation-status
```

Testy PL:

```powershell
python -m unittest tests.test_pl_materialy_regression -v
python -m pytest tests/test_pl_materialy_integration.py tests/test_pl_claude_contact_extract.py tests/test_pl_claude_prompts.py tests/test_pl_cache.py tests/test_contact_extract_utils_pl.py tests/test_pl_inquiry_email_pl.py -q
```

Maile po polsku, tel. **516513965**. **Bez załączników**.

Wyniki: `Wyniki/pl_materialy_cache.json`, `pl_materialy_kontakte.xlsx`.

Harmonogram (+5h względem UA): [`schedule/pl/PLAN_5_DNI_PL.md`](schedule/pl/PLAN_5_DNI_PL.md)

| Dzień | Godzina (PL) | GitHub Actions |
|-------|--------------|----------------|
| **Pon–Pt** | 22:00 / 20:00 / 00:00 / 01:00 / 21:00 | `PL discovery` |
| **Niedziela** | 10:30 | `PL niedziela backfill` |
| **Poniedziałek** | 11:00 / 12:00 / 14:00 | sync → prep → send |
| **Wtorek** | 14:00 | `PL wtorek send` |

---

### DE GU — Generalunternehmer (legacy, wyłączony z produkcji)

Kod pozostaje w repo; harmonogram `schedule/run_*` i Task Scheduler `Kanbud_GU_*` są wyłączone.
Produkcja: [`schedule/ua/`](schedule/ua/) + workflowy `ua_materialy_*.yml`.



| Moduł | Plik |

|-------|------|

| Scraper | `de_gu_bauunternehmen_scraper.py` |

| Frazy per Bundesland | `de_gu_keywords.py` |

| Rotacja landów | `gu_bundesland_rotation.py` |

| Treść maila DE | `mfg_gu_inquiry_email_de.py` |

| Załącznik PPTX | `mfg_gu_email_attachment.py` |



## Szybki start (lokalnie)



```powershell
git clone https://github.com/Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina.git
cd wyszukiwarka-materialow-budowlanych-ukraina
pip install -r requirements.txt
$env:KANBUD_PROJECT_ROOT = "$PWD\libs"

python ua_materialy_scraper.py --test
```



Pełna bateria testów:



```powershell

powershell -ExecutionPolicy Bypass -File scripts\RUN_ALL_TESTS.ps1

```



## Wyniki



| Plik / folder | Opis |

|---------------|------|

| `Wyniki/de_gu_bauunternehmen_cache.json` | Cache Serper + kontakty (kumulacja tygodniowa) |

| `Wyniki/de_gu_bauunternehmen_kontakte.xlsx` | Excel — **append** (dopisywanie); arkusz **Info** opisuje zasady zapisu |

| `Wyniki/de_gu_bauunternehmen_scraper.log` | Log |

| `Wyniki/de_gu_bundeslaender_rotation.json` | Stan rotacji Bundesland |

| `wyslane/` | Kopie wysłanych maili (.eml) |



**Google Drive:** [folder wyników GU](https://drive.google.com/drive/folders/1tP8oUi72t4EHDbE9GnHFdvfNtNsJe4xf) — [`docs/GOOGLE_DRIVE.md`](docs/GOOGLE_DRIVE.md)



## Uruchomienie scrapera



```powershell

$env:KANBUD_PROJECT_ROOT = "$PWD\libs"



python de_gu_bauunternehmen_scraper.py --test

python de_gu_bauunternehmen_scraper.py --rotate-bundesland

python de_gu_bauunternehmen_scraper.py --rotation-status

python de_gu_bauunternehmen_scraper.py --backfill-emails-from-cache

python de_gu_bauunternehmen_scraper.py --rebuild-from-cache

python de_gu_bauunternehmen_scraper.py --send-emails-only

python de_gu_bauunternehmen_scraper.py --dry-run-email --send-emails-only

```



### Rotacja Bundesland (domyślnie — 1 land / piątek)



```powershell

python de_gu_bauunternehmen_scraper.py --rotate-bundesland

```



Kolejność 16 landów: NRW → Bayern → BW → Niedersachsen → Hessen → Sachsen → … (cykl w `gu_bundesland_rotation.py`).



### Ręcznie wiele landów



```powershell

python de_gu_bauunternehmen_scraper.py --bundesland NRW,BY,BW

python de_gu_bauunternehmen_scraper.py --run-config run_config\welle_nrw_by_bw.json

```



## Limity



| Limit | Wartość |

|-------|---------|

| Serper | 1000 zapytań / dzień |

| E-mail | 300 / dzień kalendarzowy, 2 / domena / dzień (pon 300 + wt 300) |

| 1 Bundesland / tydzień | ~40–60 fraz Serper × 5 dni discovery |



## Harmonogram tygodnia



Szczegóły: [`schedule/PLAN_5_DNI.md`](schedule/PLAN_5_DNI.md)



| Dzień | Godzina (PL) | PC | GitHub Actions |

|-------|--------------|-----|----------------|

| **Poniedziałek** | **17:00** | `run_poniedzialek_discovery.ps1` | `GU discovery` (część 1) |
| **Wtorek** | **15:00** | `run_wtorek_discovery.ps1` | `GU discovery` (część 2) |
| **Środa** | **19:00** | `run_sroda_discovery.ps1` | `GU discovery` (część 3) |
| **Czwartek** | **20:00** | `run_czwartek_discovery.ps1` | `GU discovery` (część 4) |
| **Piątek** | **16:00** | `run_piatek_discovery.ps1` | `GU discovery` (część 5) |

| **Niedziela** | 06:00 | `run_czwartek.ps1` | `GU niedziela backfill` (~05:30) |

| **Poniedziałek** | **06:00** | — | `Sync wyniki Google Drive` |

| **Poniedziałek** | **07:00** | `run_poniedzialek_prep.ps1` | `GU poniedzialek prep` |

| **Poniedziałek** | **09:00** | `run_poniedzialek_send.ps1` | `GU poniedzialek send` (partia 1) |

| **Wtorek** | **09:00** | `run_wtorek.ps1` | `GU wtorek send` (partia 2) |



Task Scheduler:



```powershell

powershell -ExecutionPolicy Bypass -File schedule\register_tasks_5_dni.ps1

```



Pełny pipeline na GitHub Actions (ręcznie):



```powershell

powershell -ExecutionPolicy Bypass -File scripts\run_full_pipeline_gha.ps1 -ForceResend

```



## GitHub Actions



[`docs/GITHUB_ACTIONS.md`](docs/GITHUB_ACTIONS.md) — GU, UA i **PL**




| Secret | Wymagany | Opis |

|--------|----------|------|

| `SERPER_API_KEY` | tak (discovery) | API Serper |

| `ANTHROPIC_API_KEY` | tak (discovery + backfill) | Claude API |

| `CLAUDE_MODEL_FAST` | opcjonalny | Haiku — frazy Serper, cleanup Excel (domyślnie `claude-haiku-4-5`) |

| `CLAUDE_MODEL_VERIFY` | opcjonalny | Sonnet — weryfikacja www, maile z HTML (domyślnie `claude-sonnet-4-6`) |

| `MAIL_USER`, `MAIL_PASSWORD` | tak (pon+wt) | Gmail: hasło aplikacji; yagmail wysyła pocztę |

| `GDRIVE_OAUTH_*` | zalecany | Upload wyników na „Mój dysk” |

| `GDRIVE_SERVICE_ACCOUNT_JSON` | opcjonalny | Konto usługi (Shared Drive) |



## Maile MFG



- Treść: `mfg_gu_inquiry_email_de.py` (tylko niemiecki)

- Załącznik: [Google Slides](https://docs.google.com/presentation/d/1kBnp5x0pdgXZSPzVte9e92IUgn2A5gSe/edit) → PPTX (`mfg_gu_email_attachment.py`)

- Na GitHub Actions: `assets/campaign/MFG_Referenzliste_Einzelhandel.pptx` (podmień po zmianie Slides)

- Cc: tylko z `MAIL_CC` w `.env` — **bez** automatycznego `office@mfg-fliesen.de`



## Struktura repo



```
├── de_gu_bauunternehmen_scraper.py
├── ua_materialy_scraper.py
├── pl_materialy_scraper.py
├── gu_bundesland_rotation.py
├── pl_wojewodztwo_rotation.py
├── libs/
├── schedule/           # PLAN_5_DNI*.md, ua/, pl/
├── run_config/         # pl_materialy.json, ua_materialy.json, …
├── docs/               # GITHUB_ACTIONS.md, PL_MATERIALY.md, GOOGLE_DRIVE.md
├── assets/campaign/    # PPTX na runnerze GitHub (GU)
├── scripts/            # gdrive_*, RUN_ALL_TESTS.ps1
├── tests/              # test_pl_*, test_ua_*, …
├── .github/workflows/
└── Wyniki/             # cache + Excel (lokalnie)
```


