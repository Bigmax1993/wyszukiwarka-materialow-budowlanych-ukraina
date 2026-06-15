# GitHub Actions — kampania GU



Repozytorium: [Wyszukiwarka-partnerow](https://github.com/Bigmax1993/Wyszukiwarka-partnerow)



## Workflowy



| Workflow | Plik | Trigger | Co robi |

|----------|------|---------|---------|

| **Tests** | `tests.yml` | push, PR | `py_compile` + smoke `--test` |

| **CI Deploy** | `ci-deploy.yml` | push | smoke + walidacja secretów + dry-run maili |

| **GU piatek discovery** | `de_gu_pi.yml` | cron, ręcznie | Discovery część 1 (max 6 h) → `de-gu-wyniki-pi` |
| **GU sobota discovery** | `de_gu_wed.yml` | cron, ręcznie | Część 2 jeśli Serper w piątek nie wyczerpany → `de-gu-wyniki-wed` |

| **GU niedziela backfill** | `de_gu_thu.yml` | cron, ręcznie | Backfill + Excel → `de-gu-wyniki-thu` |

| **GU poniedzialek prep** | `de_gu_mon.yml` | cron, ręcznie | Rebuild Excel → `de-gu-wyniki-mon` |

| **GU poniedzialek send** | `de_gu_tue.yml` | cron, ręcznie | Wysyłka partia 1 (do 300) → `de-gu-wyniki-tue` |

| **GU wtorek send** | `de_gu_fri.yml` | cron, ręcznie | Wysyłka partia 2 → `de-gu-wyniki-fri` |

| **Sync wyniki Google Drive** | `sync-google-drive.yml` | cron pon 06:00 PL, ręcznie | Upload `Wyniki/` na Drive |



## Harmonogram cron (UTC → czas PL, CEST)



| Dzień | Workflow | Cron UTC | ≈ czas PL |

|-------|----------|----------|-----------|

| **Piątek** | discovery część 1 | `0 18 * * 5` | **20:00** |
| **Sobota** | discovery część 2 | `10 18 * * 6` | **20:10** (pomijane gdy piątek wyczerpał Serper) |

| **Niedziela** | backfill | `30 3 * * 0` | **05:30** |

| **Poniedziałek** | sync Drive | `0 4 * * 1` | **06:00** |

| **Poniedziałek** | prep | `0 6 * * 1` | **08:00** |

| **Poniedziałek** | send 1 | `0 7 * * 1` (Europe/Warsaw) | **07:00** |

| **Wtorek** | send 2 | `0 7 * * 2` | **09:00** |



Zimą (CET): piątek discovery `0 19 * * 5`, sobota `10 19 * * 6`, send 1 `0 11 * * 1`, sync Drive `0 5 * * 1`.



Wysyłka w oknie **8–18** czasu berlińskiego (bez `DISABLE_SEND_WINDOW` w workflowach send).



## Sekrety



| Secret | Wymagany | Opis |

|--------|----------|------|

| `SERPER_API_KEY` | discovery | API Serper |

| `ANTHROPIC_API_KEY` | discovery + backfill | Claude: frazy Serper (sobota) + weryfikacja www (niedziela) |

| `MAIL_USER` | pon+wt send | Login SMTP |

| `MAIL_PASSWORD` | pon+wt send | Hasło SMTP / IMAP |

| `GDRIVE_OAUTH_CLIENT_ID` | zalecany | OAuth Desktop — upload na „Mój dysk” |

| `GDRIVE_OAUTH_CLIENT_SECRET` | zalecany | OAuth Desktop |

| `GDRIVE_OAUTH_REFRESH_TOKEN` | zalecany | OAuth Desktop |

| `GDRIVE_SERVICE_ACCOUNT_JSON` | opcjonalny | Konto usługi (Shared Drive) |



Setup OAuth: `python scripts/gdrive_oauth_setup.py` — szczegóły w [`GOOGLE_DRIVE.md`](GOOGLE_DRIVE.md).



## Artifacty



```

piatek → pi → sobota → wed (opcjonalnie) → niedziela → thu → sync Drive → pon prep → mon → pon send → tue → wt send → fri

```



Piątek discovery: `de-gu-wyniki-fri` → `de-gu-wyniki-pi`. Sobota: kontynuacja z `pi` (`--respect-cache`) tylko gdy w piątek nie wyczerpano limitu Serper; wynik → `de-gu-wyniki-wed`. Niedziela backfill: najnowszy `wed` lub `pi`.

**Sync Drive** (pon 06:00 PL) pobiera **`de-gu-wyniki-thu`** z niedzielnego backfillu — kolejność: `thu` → `wed` → `mon` → `tue` → `fri`. Nie używa `fri`/`tue` z poprzedniej wysyłki, dopóki istnieje `thu`.



## Załącznik PPTX na runnerze



Workflowy send ustawiają:



`MFG_EMAIL_ATTACHMENT_PATH=assets/campaign/MFG_Referenzliste_Einzelhandel.pptx`



Przed wysyłką workflow **pobiera świeży PPTX** ze Slides (`scripts/export_mfg_slides_attachment.py`).  
Źródło: [Google Slides MFG](https://docs.google.com/presentation/d/1kBnp5x0pdgXZSPzVte9e92IUgn2A5gSe/edit) (OAuth `GDRIVE_OAUTH_*` na GHA).



## Ręczne uruchomienie



Pełny cykl (PC, czeka na każdy krok). Przy **timeout 360 min** discovery (status failure) skrypt **kontynuuje**, jeśli run zapisał artefakt `de-gu-wyniki-pi` lub `de-gu-wyniki-wed` (`-StrictDiscovery` = stare zachowanie, przerwij):



```powershell

powershell -ExecutionPolicy Bypass -File scripts\run_full_pipeline_gha.ps1 -ForceResend

```



Pojedyncze kroki (`gh`):



```powershell

gh workflow run "GU sobota discovery" -R Bigmax1993/Wyszukiwarka-partnerow

gh workflow run "GU niedziela backfill" -R Bigmax1993/Wyszukiwarka-partnerow

gh workflow run "Sync wyniki Google Drive" -R Bigmax1993/Wyszukiwarka-partnerow

gh workflow run "GU poniedzialek prep" -R Bigmax1993/Wyszukiwarka-partnerow

gh workflow run "GU poniedzialek send" -R Bigmax1993/Wyszukiwarka-partnerow -f force_resend=true

gh workflow run "GU wtorek send" -R Bigmax1993/Wyszukiwarka-partnerow -f force_resend=true

```



Kolejność: discovery → backfill → sync Drive → prep → pon send → wt send.


