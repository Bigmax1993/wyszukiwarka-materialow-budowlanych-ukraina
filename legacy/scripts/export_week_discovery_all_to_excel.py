# -*- coding: utf-8 -*-
"""
Scal artefakty de-gu-wyniki-pi z kilku dni discovery i zapisz WSZYSTKIE firmy z cache do Excela.

Pomija ostre filtry eksportu (skipped / bez maila też trafiają do arkusza).
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIBS = ROOT / "libs"
SCRIPTS = ROOT / "scripts"
LEGACY_GU = ROOT / "legacy" / "de_gu"
for _p in (ROOT, LIBS, SCRIPTS, LEGACY_GU):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from recover_pi_cache_contacts import recover_contacts_from_cache_file  # noqa: E402

from libs.scraper_email_replies import ReplySyncConfig, write_excel_with_reply_styles  # noqa: E402

import de_gu_bauunternehmen_scraper as scraper  # noqa: E402


def _contact_to_pipeline_row(place_url: str, info: dict) -> dict:
    name = (
        info.get("company_name_clean")
        or info.get("company_name")
        or info.get("company_name_raw")
        or ""
    ).strip()
    email = (info.get("email_target") or "").strip()
    if not email:
        found = [
            x.strip()
            for x in (info.get("emails_found") or "").split(",")
            if x.strip() and "@" in x
        ]
        email = found[0] if found else ""
    phone = (info.get("phones_found") or "").strip()
    if "," in phone:
        phone = phone.split(",", 1)[0].strip()
    return scraper.normalize_row_company_name(
        {
            "url": place_url,
            "www": info.get("official_website") or place_url,
            "official_website": info.get("official_website") or place_url,
            "nazwa": name,
            "company_name_clean": name,
            "company_name_raw": info.get("company_name_raw") or name,
            "email_target": email,
            "emails_found": info.get("emails_found") or "",
            "telefon": phone,
            "phones_found": info.get("phones_found") or phone,
            "full_address": info.get("full_address") or "",
            "adres": info.get("full_address") or "",
            "bundesland": info.get("bundesland") or info.get("discovery_bundesland") or "",
            "discovery_bundesland": info.get("discovery_bundesland") or "",
            "retail_verified": bool(info.get("retail_verified")),
            "verification_reason": (info.get("verification_reason") or "").strip(),
            "page_snippet": (info.get("page_snippet") or "").strip(),
            "retail_chains_found": (info.get("retail_chains_found") or "").strip(),
            "is_gu": bool(info.get("is_gu")),
            "is_small_firm": bool(info.get("is_small_firm", True)),
            "gu_marker": (info.get("gu_marker") or "").strip(),
            "email_status": (info.get("email_status") or "").strip(),
        }
    )


def _pipeline_row_to_export(row: dict) -> dict:
    email = (row.get("email_target") or "").strip()
    if not email:
        found = [
            x.strip()
            for x in (row.get("emails_found") or "").split(",")
            if x.strip() and "@" in x
        ]
        if found:
            email, _ = scraper.pick_best_email_for_inquiry(
                found, row.get("official_website") or row.get("www") or ""
            )
    table = scraper.row_to_excel_kontakte_columns(row, email)
    reason = (row.get("verification_reason") or "").strip()
    return {
        **table,
        "WWW_geprueft": "ja" if row.get("retail_verified") else "nein",
        "Kleinunternehmen": "ja" if row.get("is_small_firm") else "nein",
        "GU": "ja" if row.get("is_gu") or scraper._row_has_gu_signal(row) else "nein",
        "GU_Marker": (row.get("gu_marker") or "").strip(),
        "Status": scraper._excel_status_label(row),
        "Weryfikacja": reason[:200] if reason else "",
    }


def _load_cache_file(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _download_pi_artifact(run_id: str, dest: Path, *, repo: str) -> Path | None:
    dest.mkdir(parents=True, exist_ok=True)
    cmd = [
        "gh",
        "run",
        "download",
        str(run_id),
        "-R",
        repo,
        "-n",
        "de-gu-wyniki-pi",
        "-D",
        str(dest),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        logging.warning("Pomijam run %s: %s", run_id, (proc.stderr or proc.stdout).strip())
        return None
    cache_path = dest / "Wyniki" / "de_gu_bauunternehmen_cache.json"
    return cache_path if cache_path.is_file() else None


def merge_contacts_from_run_ids(
    run_ids: list[str],
    *,
    repo: str,
    skip_corrupt: bool = True,
) -> tuple[dict, list[str]]:
    merged: dict[str, dict] = {}
    loaded: list[str] = []
    for run_id in run_ids:
        run_id = run_id.strip()
        if not run_id:
            continue
        with tempfile.TemporaryDirectory(prefix=f"gu-pi-{run_id}-") as tmp:
            cache_path = _download_pi_artifact(run_id, Path(tmp), repo=repo)
            if not cache_path:
                continue
            try:
                cache = _load_cache_file(cache_path)
                contacts = cache.get("contacts") or {}
            except json.JSONDecodeError as exc:
                if skip_corrupt:
                    logging.warning(
                        "run %s: uszkodzony JSON (%s) — probuje odzysku contacts",
                        run_id,
                        exc,
                    )
                    contacts = recover_contacts_from_cache_file(cache_path)
                else:
                    raise
            if not isinstance(contacts, dict):
                continue
            for url, info in contacts.items():
                if isinstance(info, dict):
                    merged[url] = info
            loaded.append(run_id)
            logging.info(
                "run %s: +%s kontaktow (lacznie %s)", run_id, len(contacts), len(merged)
            )
    return merged, loaded


def export_merged_contacts(
    contacts: dict[str, dict],
    *,
    label: str = "",
) -> tuple[list[dict], dict]:
    logger = logging.getLogger("week_export")
    cache = scraper._empty_cache()
    cache["contacts"] = dict(contacts)
    rows = []
    for place_url, info in contacts.items():
        if not isinstance(info, dict):
            continue
        row = _contact_to_pipeline_row(place_url, info)
        name = (row.get("nazwa") or "").strip()
        url = (row.get("url") or "").strip()
        if not name and not url:
            continue
        rows.append(row)
    rows.sort(key=lambda r: ((r.get("nazwa") or "").lower(), r.get("url") or ""))
    if not rows:
        raise SystemExit("Brak firm do eksportu po scaleniu cache.")
    scraper.sync_pipeline_rows_to_contacts_cache(rows, cache)
    if label:
        cache.setdefault("week_export_meta", {})["label"] = label
        cache["week_export_meta"]["exported_rows"] = len(rows)
    logger.info("Eksport tygodnia: %s unikalnych firm", len(rows))
    return rows, cache


def write_excel(rows: list[dict], cache: dict, logger: logging.Logger, output: Path | None = None) -> Path:
    export_rows = [_pipeline_row_to_export(r) for r in rows]
    state_rows = scraper.build_bundesland_rows(rows)
    out = output or scraper.OUTPUT_FILE
    out.parent.mkdir(parents=True, exist_ok=True)
    cfg = ReplySyncConfig(
        cache_path=scraper.CACHE_FILE,
        xlsx_path=out,
        lang="de",
        campaign_id="de_gu_bauunternehmen",
    )
    write_excel_with_reply_styles(
        out,
        {
            "Info": scraper.build_excel_info_sheet_rows(),
            "Kontakte": export_rows,
            "Wojewodztwa": state_rows,
        },
        cache,
        cfg,
        logger,
    )
    scraper.save_cache(cache, logger)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scal pi z tygodnia discovery i zapisz wszystkie firmy do Excela"
    )
    parser.add_argument(
        "--run-ids",
        required=True,
        help="Lista run ID (de-gu-wyniki-pi), po przecinku",
    )
    parser.add_argument(
        "--repo",
        default="Bigmax1993/Wyszukiwarka-partnerow",
        help="GitHub repo (owner/name)",
    )
    parser.add_argument(
        "--label",
        default="",
        help="Etykieta tygodnia (np. 2026-06-15_2026-06-21)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Sciezka docelowego Excela (domyslnie Wyniki/de_gu_bauunternehmen_kontakte.xlsx)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger("week_export")

    run_ids = [x.strip() for x in args.run_ids.split(",") if x.strip()]
    contacts, loaded = merge_contacts_from_run_ids(run_ids, repo=args.repo)
    if not loaded:
        raise SystemExit("Nie udalo sie pobrac zadnego artefaktu pi.")
    rows, cache = export_merged_contacts(contacts, label=args.label)
    out = write_excel(rows, cache, logger, output=args.output)

    with_email = sum(1 for r in rows if (r.get("email_target") or "").strip())
    print(
        f"Zapisano {len(rows)} firm ({with_email} z e-mailem) -> {out}\n"
        f"Zrodlo: run IDs {', '.join(loaded)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
