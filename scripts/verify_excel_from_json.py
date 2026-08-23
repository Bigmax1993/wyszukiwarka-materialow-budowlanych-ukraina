# -*- coding: utf-8 -*-
"""
Niedzielny sync: weryfikuje Excel vs cache JSON, uzupelnia braki i zapisuje.

Walidacja przepuszcza z JSON pola potrzebne w Excelu (nazwa, e-mail, telefon,
adres, wojewodztwo, www, URL) — bez filtra GU/retail.
Po zapisie ponownie czyta caly plik; przy lukach znow JSON → uzupelnienie → zapis.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIBS = ROOT / "libs"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(LIBS) not in sys.path:
    sys.path.insert(0, str(LIBS))

from scripts.excel_from_json_validate import (  # noqa: E402
    fill_export_from_json,
    json_contact_has_needed_data,
    merge_contacts_maps,
    pipeline_row_from_json,
    verify_and_fill_until_complete,
)
from scripts.recover_pi_cache_contacts import recover_contacts_from_cache_file  # noqa: E402
from libs.scraper_email_replies import ReplySyncConfig, write_excel_with_reply_styles  # noqa: E402

CAMPAIGNS = {
    "pl": {
        "module": "pl_materialy_scraper",
        "lang": "pl",
        "campaign_id": "pl_materialy",
        "xlsx_name": "pl_materialy_kontakte.xlsx",
        "cache_glob": "*_cache.json",
    },
    "ua": {
        "module": "ua_materialy_scraper",
        "lang": "uk",
        "campaign_id": "ua_materialy",
        "xlsx_name": "ua_materialy_kontakte.xlsx",
        "cache_glob": "*_cache.json",
    },
}


def _load_scraper(campaign: str):
    spec = CAMPAIGNS[campaign]
    return __import__(spec["module"]), spec


def _cell(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def pipeline_row_as_info(row: dict) -> dict:
    return {
        "company_name_clean": _cell(row.get("company_name_clean") or row.get("nazwa")),
        "company_name": _cell(row.get("nazwa")),
        "email_target": _cell(row.get("email_target")),
        "emails_found": _cell(row.get("emails_found")),
        "phones_found": _cell(row.get("phones_found") or row.get("telefon")),
        "full_address": _cell(row.get("full_address") or row.get("adres")),
        "official_website": _cell(row.get("official_website") or row.get("www")),
        "bundesland": _cell(row.get("bundesland")),
        "retail_chains_found": _cell(row.get("retail_chains_found")),
        "email_status": _cell(row.get("email_status")),
        "retail_verified": bool(row.get("retail_verified")),
        "is_gu": bool(row.get("is_gu")),
        "is_small_firm": row.get("is_small_firm", True),
        "gu_marker": _cell(row.get("gu_marker")),
    }


def collect_needed_contacts(wyniki: Path, xlsx: Path, scraper, logger: logging.Logger) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    for cache_path in sorted(wyniki.glob("*_cache.json")):
        recovered = recover_contacts_from_cache_file(cache_path)
        logger.info("%s: contacts=%s", cache_path.name, len(recovered))
        merged = merge_contacts_maps(merged, recovered)
    if xlsx.is_file():
        rows, _ = scraper.load_existing_output(xlsx, logger)
        excel_contacts = {}
        for row in rows:
            url = _cell(row.get("url") or row.get("www") or row.get("official_website"))
            if url:
                excel_contacts[url] = pipeline_row_as_info(row)
        logger.info("%s: excel_rows=%s", xlsx.name, len(excel_contacts))
        merged = merge_contacts_maps(merged, excel_contacts)
    needed = {}
    for url, info in merged.items():
        if not json_contact_has_needed_data(url, info):
            continue
        if scraper.is_public_portal_url(url) or scraper.is_public_portal_url(
            (info or {}).get("official_website") or ""
        ):
            continue
        needed[url] = info
    logger.info("Do Excela z JSON: %s z %s contacts", len(needed), len(merged))
    return needed


def write_sheets(
    scraper,
    spec: dict,
    xlsx: Path,
    export_rows: list[dict],
    pipeline_rows: list[dict],
    cache: dict,
    logger,
) -> None:
    state_rows = scraper.build_bundesland_rows(pipeline_rows) if pipeline_rows else []
    cfg = ReplySyncConfig(
        cache_path=scraper.CACHE_FILE,
        xlsx_path=xlsx,
        lang=spec["lang"],
        campaign_id=spec["campaign_id"],
    )
    write_excel_with_reply_styles(
        xlsx,
        {
            "Info": scraper.build_excel_info_sheet_rows(),
            "Kontakte": export_rows,
            "Wojewodztwa": state_rows,
        },
        cache,
        cfg,
        logger,
    )


def verify_and_save(scraper, spec: dict, contacts: dict, xlsx: Path, cache: dict, logger) -> tuple[int, list[dict]]:
    pipeline_rows = [pipeline_row_from_json(url, info) for url, info in contacts.items()]
    export_rows = scraper.build_export_rows(
        pipeline_rows, logger=logger, cache=cache, require_eligible=False
    )
    export_rows, n_fill = fill_export_from_json(contacts, export_rows)
    logger.info("Uzupelnienie z JSON: %s zmian", n_fill)
    export_rows, gaps, rounds = verify_and_fill_until_complete(contacts, export_rows)
    logger.info("Weryfikacja pamieci: rund=%s luk=%s wierszy=%s", rounds, len(gaps), len(export_rows))
    write_sheets(scraper, spec, xlsx, export_rows, pipeline_rows, cache, logger)

    extra = 0
    gaps_after: list[dict] = []
    loaded_export = export_rows
    loaded_pipeline = pipeline_rows
    for disk_round in range(5):
        loaded, _ = scraper.load_existing_output(xlsx, logger)
        loaded_pipeline = loaded
        loaded_export = scraper.build_export_rows(
            loaded, logger=logger, cache=cache, require_eligible=False
        )
        loaded_export, gaps_after, fill_rounds = verify_and_fill_until_complete(
            contacts, loaded_export
        )
        extra += fill_rounds
        if fill_rounds or gaps_after:
            logger.warning(
                "Po odczycie dysku (runda %s) JSON uzupelnia i zapisuje: rund=%s luki=%s",
                disk_round + 1,
                fill_rounds,
                len(gaps_after),
            )
            write_sheets(scraper, spec, xlsx, loaded_export, loaded_pipeline, cache, logger)
            if fill_rounds:
                continue
        break
    logger.info(
        "Weryfikacja koncowa: wierszy=%s luki=%s rund_dysku=%s",
        len(loaded_export),
        len(gaps_after),
        extra,
    )
    return len(loaded_export), gaps_after


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", choices=sorted(CAMPAIGNS), default="pl")
    parser.add_argument("--wyniki", type=Path, default=ROOT / "Wyniki")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger("verify_excel_json")

    scraper, spec = _load_scraper(args.campaign)
    xlsx = args.wyniki / spec["xlsx_name"]
    contacts = collect_needed_contacts(args.wyniki, xlsx, scraper, logger)
    if not contacts:
        raise SystemExit("Brak contacts JSON z danymi do Excela")
    cache = {"contacts": contacts}
    n_rows, gaps = verify_and_save(scraper, spec, contacts, xlsx, cache, logger)
    if gaps:
        print(f"VERIFY_FAIL rows={n_rows} gaps={len(gaps)}")
        for g in gaps[:20]:
            print(f"  {g['url']}: {g['reason']} {g['columns']}")
        return 1
    print(f"VERIFY_OK rows={n_rows} contacts_json={len(contacts)} file={xlsx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
