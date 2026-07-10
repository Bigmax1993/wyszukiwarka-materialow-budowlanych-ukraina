# -*- coding: utf-8 -*-
"""
Zapis 7 firm do Excel z artefaktu piątkowego discovery (de-gu-wyniki-pi).

5 firm z arkusza Kontakte + 2 z cache JSON (Gropp bg-hd.de, Münch+Muench),
które wypadają przy ostrych filtrach eksportu (sieć „dm” poza whitelistą).
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIBS = ROOT / "libs"
LEGACY_GU = ROOT / "legacy" / "de_gu"
for _p in (ROOT, LIBS, LEGACY_GU):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from libs.scraper_email_replies import ReplySyncConfig, write_excel_with_reply_styles  # noqa: E402

import de_gu_bauunternehmen_scraper as scraper  # noqa: E402

# Dwie firmy z piątkowego cache, których nie ma w xlsx po filtrach.
_EXTRA_CACHE_URLS = (
    "https://bg-hd.de",
    "https://muenchundmuench.com",
)


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
            "bundesland": info.get("bundesland") or "",
            "retail_verified": bool(info.get("retail_verified")),
            "verification_reason": (info.get("verification_reason") or "").strip(),
            "page_snippet": (info.get("page_snippet") or "").strip(),
            "retail_chains_found": (info.get("retail_chains_found") or "").strip(),
            "is_gu": bool(info.get("is_gu")),
            "is_small_firm": bool(info.get("is_small_firm")),
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
    return {
        **table,
        "WWW_geprueft": "ja" if row.get("retail_verified") else "nein",
        "Kleinunternehmen": "ja" if row.get("is_small_firm") else "nein",
        "GU": "ja" if row.get("is_gu") or scraper._row_has_gu_signal(row) else "nein",
        "GU_Marker": (row.get("gu_marker") or "").strip(),
        "Status": scraper._excel_status_label(row),
    }


def build_seven_rows(logger: logging.Logger) -> tuple[list[dict], dict]:
    cache = scraper.load_cache(logger)
    rows, _ = scraper.load_existing_output(scraper.OUTPUT_FILE, logger)
    by_url = scraper.index_all_rows_by_url(rows)
    contacts = cache.get("contacts") or {}

    for place_url in _EXTRA_CACHE_URLS:
        info = contacts.get(place_url)
        if not isinstance(info, dict):
            logger.warning("Brak kontaktu w cache: %s", place_url)
            continue
        row = _contact_to_pipeline_row(place_url, info)
        url = (row.get("url") or place_url).strip()
        if url in by_url:
            by_url[url].update(row)
        else:
            rows.append(row)
            by_url[url] = row

    scraper.sync_pipeline_rows_to_contacts_cache(rows, cache)

    if len(rows) < 7:
        raise SystemExit(
            f"Za malo firm do zapisu: {len(rows)} (oczekiwano 7). "
            "Uruchom na artefakcie de-gu-wyniki-pi z piatku."
        )

    return rows[:7], cache


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger("excel_seven")

    rows, cache = build_seven_rows(logger)
    export_rows = [_pipeline_row_to_export(r) for r in rows]
    state_rows = scraper.build_bundesland_rows(rows)

    cfg = ReplySyncConfig(
        cache_path=scraper.CACHE_FILE,
        xlsx_path=scraper.OUTPUT_FILE,
        lang="de",
        campaign_id="de_gu_bauunternehmen",
    )
    write_excel_with_reply_styles(
        scraper.OUTPUT_FILE,
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

    names = [r.get("Nazwa firmy") or "" for r in export_rows]
    print(f"Zapisano {len(export_rows)} firm w {scraper.OUTPUT_FILE}:")
    for i, name in enumerate(names, 1):
        print(f"  {i}. {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
