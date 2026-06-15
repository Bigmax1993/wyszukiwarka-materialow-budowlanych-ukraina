# Wyszukiwarka partnerów — kampania GU (bundesweit)



Repozytorium: [Bigmax1993/Wyszukiwarka-partnerow](https://github.com/Bigmax1993/Wyszukiwarka-partnerow) (private)



Pipeline: **Serper → strony www → cache/Excel → maile MFG** (Generalunternehmer / Filialbau DE).



| Moduł | Plik |

|-------|------|

| Scraper | `de_gu_bauunternehmen_scraper.py` |

| Frazy per Bundesland | `de_gu_keywords.py` |

| Rotacja landów | `gu_bundesland_rotation.py` |

| Treść maila DE | `mfg_gu_inquiry_email_de.py` |

| Załącznik PPTX | `mfg_gu_email_attachment.py` |



## Szybki start (lokalnie)



```powershell

git clone https://github.com/Bigmax1993/Wyszukiwarka-partnerow.git

cd Wyszukiwarka-partnerow

pip install -r requirements.txt

$env:KANBUD_PROJECT_ROOT = "$PWD\libs"

python de_gu_bauunternehmen_scraper.py --test

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

| Serper | 1500 zapytań / dzień |

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



[`docs/GITHUB_ACTIONS.md`](docs/GITHUB_ACTIONS.md)



| Secret | Wymagany | Opis |

|--------|----------|------|

| `SERPER_API_KEY` | tak (discovery) | API Serper |

| `ANTHROPIC_API_KEY` | tak (discovery + backfill) | Claude API |

| `CLAUDE_MODEL_FAST` | opcjonalny | Haiku — frazy Serper, cleanup Excel (domyślnie `claude-haiku-4-5`) |

| `CLAUDE_MODEL_VERIFY` | opcjonalny | Sonnet — weryfikacja www, maile z HTML (domyślnie `claude-sonnet-4-6`) |

| `MAIL_USER`, `MAIL_PASSWORD` | tak (pon+wt) | SMTP + IMAP |

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

├── gu_bundesland_rotation.py

├── libs/

├── schedule/           # PLAN_5_DNI.md, register_tasks_5_dni.ps1

├── run_config/

├── assets/campaign/    # PPTX na runnerze GitHub

├── scripts/            # gdrive_*, run_full_pipeline_gha.ps1, RUN_ALL_TESTS.ps1

├── .github/workflows/

└── docs/

```


