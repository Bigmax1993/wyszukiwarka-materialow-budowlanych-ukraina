# Plan 3 dni: środa → czwartek → piątek (fala GU NRW+BY+BW)

Jeden **obrót** pipeline’u na **jedną falę** (~96 zapytań Serper). Cała kampania bundesweit = wiele takich tygodni.

## Tabela harmonogramu

| Dzień | Godzina (PL) | Skrypt PC | GitHub Actions |
|-------|--------------|-----------|----------------|
| **Środa** | **20:10** | `run_sroda.ps1` | `GU sroda discovery` |
| **Czwartek** | 06:00 | `run_czwartek.ps1` | `GU czwartek backfill` (~05:30 na Actions) |
| **Piątek** | 09:00 | `run_piatek.ps1` | `GU piatek send` |

| Dzień | Skrypt | Co robi |
|-------|--------|---------|
| **Środa** | `run_sroda.ps1` | Discovery: Serper + strony www → `Wyniki/de_gu_bauunternehmen_cache.json` |
| **Czwartek** | `run_czwartek.ps1` | Backfill e-maili + Excel (bez nowego Serpera) |
| **Piątek** | `run_piatek.ps1` | Wysyłka maili (`--send-emails-only`, okno **8–18** czas niemiecki) |

Po piątku (lub ręcznie): workflow **Sync wyniki Google Drive** → upload na [folder Drive](../docs/GOOGLE_DRIVE.md).

## Środa — discovery (20:10)

- `run_config\welle_nrw_by_bw.json`: `enable_auto_email: false`, `dry_run_email: true` (zostaw na środę).
- Limit Serper: **300/dzień** — jedna fala mieści się w środę.
- Start **20:10** — skan trwa wieczorem i w nocy (zwykle **2–8 h**); komputer nie może iść w uśpienie do rana (albo do końca joba).

```powershell
powershell -ExecutionPolicy Bypass -File "schedule\run_sroda.ps1"
```

## Czwartek — backfill + Excel (06:00)

- Dopina `email_target` (Punycode, scoring) i odświeża `de_gu_bauunternehmen_kontakte.xlsx`.
- Jeśli środa **nie skończyła** skanu: najpierw ponów `run_sroda.ps1`, dopiero potem czwartek.

```powershell
powershell -ExecutionPolicy Bypass -File "schedule\run_czwartek.ps1"
```

## Piątek — wysyłka (09:00)

- **Bez** `DISABLE_SEND_WINDOW` — maile tylko **8:00–18:00** (Berlin).
- Limit: **300 maili/dzień**, **2/domena/dzień**; pełna sesja ~**2–4 h**.
- Na produkcję: w `welle_nrw_by_bw.json` ustaw `dry_run_email: false` i `enable_auto_email: true`, albo trzymaj tylko `--send-emails-only` (jak w skrypcie).

```powershell
powershell -ExecutionPolicy Bypass -File "schedule\run_piatek.ps1"
```

## Task Scheduler (Windows)

Zarejestruj 3 zadania (użytkownik z Pythonem w PATH i `.env` / secretami):

```powershell
powershell -ExecutionPolicy Bypass -File "schedule\register_tasks_3_dni.ps1"
```

Godziny w Schedulerze: **środa 20:10**, czwartek 06:00, piątek 09:00.

Usunięcie: `register_tasks_3_dni.ps1 -Unregister`

## GitHub Actions

Szczegóły workflowów, sekrety, cron UTC: [`docs/GITHUB_ACTIONS.md`](../docs/GITHUB_ACTIONS.md)

| Workflow | Cron UTC (CEST → PL) |
|----------|----------------------|
| `de_gu_wed.yml` | `10 18 * * 3` → **20:10** środa |
| `de_gu_thu.yml` | `30 3 * * 4` → **05:30** czwartek |
| `de_gu_fri.yml` | `0 7 * * 5` → **09:00** piątek |
| `sync-google-drive.yml` | `0 12 * * 5` → 14:00 piątek (+ po zakończeniu send) |

Artifacty: `de-gu-wyniki-wed` → `de-gu-wyniki-thu` → `de-gu-wyniki-fri`.

**Zimą (CET):** w `de_gu_wed.yml` zmień cron na `10 19 * * 3` (20:10 PL).

## Kolejny tydzień

| Tydzień | Środa | Czwartek | Piątek |
|---------|-------|----------|--------|
| 1 | Fala 1 NRW+BY+BW | backfill | wysyłka |
| 2 | Fala 2 (np. HE, NI, RP) — nowy `run_config` | backfill | wysyłka + reszta limitu z tygodnia 1 |
| … | kolejne Bundesländer | … | … |

## Pierwszy tydzień kampanii

- **Piątek tygodnia 1**: wysyłka tylko z kontaktów zebrane w **środę–czwartek** (może być mniej niż 300).
- Od **tygodnia 2** piątek wysyła też zaległe z poprzednich fal, jeśli zostały w cache.
