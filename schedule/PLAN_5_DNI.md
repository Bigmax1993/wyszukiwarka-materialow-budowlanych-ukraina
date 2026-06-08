# Plan 5 dni: sobota → niedziela → poniedziałek → wtorek

Jeden **obrót** na **jedną falę** (1 Bundesland / tydzień, rotacja `--rotate-bundesland`).
Wysyłka **pon 12:00** + **wt 09:00** (2×300 maili/dzień).

## Tabela harmonogramu

| Dzień | Godzina (PL) | Skrypt PC | GitHub Actions |
|-------|--------------|-----------|----------------|
| **Sobota** | **20:10** | `run_sroda.ps1` | `GU sobota discovery` |
| **Niedziela** | 06:00 | `run_czwartek.ps1` | `GU niedziela backfill` (~05:30 Actions) |
| **Poniedziałek** | **06:00** | — | `Sync wyniki Google Drive` |
| **Poniedziałek** | 08:00 | `run_poniedzialek_prep.ps1` | `GU poniedzialek prep` |
| **Poniedziałek** | **12:00** | `run_poniedzialek_send.ps1` | `GU poniedzialek send` (partia 1) |
| **Wtorek** | **09:00** | `run_wtorek.ps1` | `GU wtorek send` (partia 2) |

| Dzień | Co robi |
|-------|---------|
| **Sobota** | Discovery Serper + www → cache JSON |
| **Niedziela** | Backfill e-maili + Excel |
| **Poniedziałek rano** | Rebuild Excel z cache, **bez wysyłki** |
| **Poniedziałek 12:00** | Wysyłka partia 1 (max **300**, okno **8–18** Berlin) |
| **Wtorek 09:00** | Wysyłka partia 2 (kolejne **300** + zaległe) |

W **poniedziałek rano (06:00)**: workflow **Sync wyniki Google Drive** → upload na [folder Drive](../docs/GOOGLE_DRIVE.md) (Excel po niedzielnym backfillu, przed prep 08:00).

## Task Scheduler (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File "schedule\register_tasks_5_dni.ps1"
```

## GitHub Actions — artefakty

```
sobota → wed → niedziela → thu → sync Drive → pon prep → mon → pon send → tue → wt send → fri
```

| Workflow | Plik | Cron UTC (CEST → PL) |
|----------|------|----------------------|
| discovery | `de_gu_wed.yml` | `10 18 * * 6` → **20:10** sobota |
| backfill | `de_gu_thu.yml` | `30 3 * * 0` → **05:30** niedziela |
| prep | `de_gu_mon.yml` | `0 6 * * 1` → **08:00** poniedziałek |
| send 1 | `de_gu_tue.yml` | `0 10 * * 1` → **12:00** poniedziałek |
| send 2 | `de_gu_fri.yml` | `0 7 * * 2` → **09:00** wtorek |
| sync Drive | `sync-google-drive.yml` | `0 4 * * 1` → **06:00** poniedziałek |

**Zimą (CET):** send 1 → `0 11 * * 1` (12:00 PL); sync → `0 5 * * 1` (06:00 PL).
