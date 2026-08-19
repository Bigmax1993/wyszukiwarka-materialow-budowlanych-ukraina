# -*- coding: utf-8 -*-
"""
Pobiera (juz sciagniete) artefakty GHA, scala cache JSON, buduje jeden Excel,
waliduje vs JSON (uzupelnia braki w petli) i zapisuje Wyniki/.
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.excel_from_json_validate import (  # noqa: E402
    fill_export_from_json,
    json_contact_has_needed_data,
    load_kontakte_rows,
    merge_contacts_maps,
    pipeline_row_from_json,
    verify_and_fill_until_complete,
)
from scripts.recover_pi_cache_contacts import recover_contacts_from_cache_file  # noqa: E402

import ua_materialy_scraper as scraper  # noqa: E402
from libs.scraper_email_replies import ReplySyncConfig, write_excel_with_reply_styles  # noqa: E402

CACHE_NAME = "ua_materialy_cache.json"
XLSX_NAME = "ua_materialy_kontakte.xlsx"


def _iter_artifact_dirs(src: Path) -> list[Path]:
    if not src.is_dir():
        return []
    return sorted(p for p in src.iterdir() if p.is_dir())


def _wyniki_dir(art: Path) -> Path:
    return art / "Wyniki" if (art / "Wyniki").is_dir() else art


def _iter_cache_files(src: Path) -> list[Path]:
    if src.is_file() and src.suffix.lower() == ".json":
        return [src]
    found: list[Path] = []
    seen: set[Path] = set()

    def _add(path: Path) -> None:
        resolved = path.resolve()
        if resolved in seen or not path.is_file():
            return
        seen.add(resolved)
        found.append(path)

    if src.is_dir():
        for cache_path in src.glob("*_cache.json"):
            _add(cache_path)
        wyniki = src / "Wyniki"
        if wyniki.is_dir():
            for cache_path in wyniki.glob("*_cache.json"):
                _add(cache_path)
        for art in _iter_artifact_dirs(src):
            wdir = _wyniki_dir(art)
            for cache_path in wdir.glob("*_cache.json"):
                _add(cache_path)
    return found


def collect_contacts(src: Path, logger: logging.Logger) -> dict[str, dict]:
    maps: list[dict] = []
    for cache_path in _iter_cache_files(src):
        contacts = recover_contacts_from_cache_file(cache_path)
        logger.info("%s: contacts=%s", cache_path.name, len(contacts))
        maps.append(contacts)
    merged = merge_contacts_maps(*maps)
    needed = {
        url: info
        for url, info in merged.items()
        if json_contact_has_needed_data(url, info)
    }
    logger.info(
        "JSON po scaleniu: %s contacts, z tego %s z danymi do Excela",
        len(merged),
        len(needed),
    )
    return needed


def copy_supporting_files(src: Path, wyniki: Path, wyslane: Path, logger: logging.Logger) -> None:
    wyniki.mkdir(parents=True, exist_ok=True)
    wyslane.mkdir(parents=True, exist_ok=True)
    best_cache: tuple[int, Path] | None = None
    best_rot: Path | None = None
    eml_n = 0
    for cache_path in _iter_cache_files(src):
        size = cache_path.stat().st_size
        if best_cache is None or size > best_cache[0]:
            best_cache = (size, cache_path)
    search_roots = [src]
    if src.is_dir():
        search_roots.extend(_iter_artifact_dirs(src))
    for root in search_roots:
        wdir = _wyniki_dir(root) if root != src or (src / "Wyniki").is_dir() else src
        if not wdir.is_dir():
            continue
        for rot in wdir.glob("*_rotation.json"):
            best_rot = rot
        sdir = root / "wyslane"
        if sdir.is_dir():
            for eml in sdir.rglob("*.eml"):
                dest = wyslane / eml.name
                if not dest.exists() or eml.stat().st_size > dest.stat().st_size:
                    shutil.copy2(eml, dest)
                    eml_n += 1
    if best_cache:
        dest = wyniki / CACHE_NAME
        if best_cache[1].resolve() != dest.resolve():
            shutil.copy2(best_cache[1], dest)
        logger.info("Cache bazowy: %s (%s MB)", dest.name, best_cache[0] // (1024 * 1024))
    if best_rot:
        dest_rot = wyniki / best_rot.name
        if best_rot.resolve() != dest_rot.resolve():
            shutil.copy2(best_rot, dest_rot)
    logger.info("Skopiowano .eml: %s", eml_n)


def _write_xlsx(xlsx_path: Path, export_rows: list[dict], state_rows: list[dict], cache: dict, logger: logging.Logger) -> None:
    cfg = ReplySyncConfig(
        cache_path=scraper.CACHE_FILE,
        xlsx_path=xlsx_path,
        lang="uk",
        campaign_id="ua_materialy",
    )
    write_excel_with_reply_styles(
        xlsx_path,
        {
            "Info": scraper.build_excel_info_sheet_rows(),
            "Kontakte": export_rows,
            "Wojewodztwa": state_rows,
        },
        cache,
        cfg,
        logger,
    )


def write_validated_excel(
    contacts: dict[str, dict],
    xlsx_path: Path,
    cache: dict,
    logger: logging.Logger,
) -> tuple[int, list[dict]]:
    rows = [pipeline_row_from_json(url, info) for url, info in contacts.items()]
    export_rows = scraper.build_export_rows(
        rows, logger=logger, cache=cache, require_eligible=False
    )
    export_rows, n_fill = fill_export_from_json(contacts, export_rows)
    logger.info("Uzupelnienie z JSON (runda 0): %s zmian", n_fill)
    export_rows, gaps, rounds = verify_and_fill_until_complete(contacts, export_rows)
    logger.info("Weryfikacja po %s rundach: luk=%s, wierszy=%s", rounds, len(gaps), len(export_rows))
    if gaps:
        export_rows, n_fill = fill_export_from_json(contacts, export_rows)
        logger.info("Doliczona runda: +%s zmian, ponowna weryfikacja", n_fill)
        export_rows, gaps, _ = verify_and_fill_until_complete(contacts, export_rows)
    state_rows = scraper.build_bundesland_rows(rows)
    _write_xlsx(xlsx_path, export_rows, state_rows, cache, logger)

    loaded_export = load_kontakte_rows(xlsx_path)
    loaded_export, gaps_after, extra_rounds = verify_and_fill_until_complete(
        contacts, loaded_export
    )
    if gaps_after:
        logger.warning("Po zapisie nadal luki=%s — JSON → walidacja → uzupelnienie → zapis", len(gaps_after))
        loaded_export, _ = fill_export_from_json(contacts, loaded_export)
        loaded_export, gaps_after, extra_rounds = verify_and_fill_until_complete(
            contacts, loaded_export
        )
        _write_xlsx(xlsx_path, loaded_export, state_rows, cache, logger)
        loaded_export = load_kontakte_rows(xlsx_path)
        loaded_export, gaps_after, extra_rounds = verify_and_fill_until_complete(
            contacts, loaded_export
        )
        if gaps_after:
            loaded_export, _ = fill_export_from_json(contacts, loaded_export)
            loaded_export, gaps_after, extra_rounds = verify_and_fill_until_complete(
                contacts, loaded_export
            )
            _write_xlsx(xlsx_path, loaded_export, state_rows, cache, logger)
    logger.info(
        "Weryfikacja koncowa: wierszy=%s luki=%s extra_rund=%s",
        len(loaded_export),
        len(gaps_after),
        extra_rounds,
    )
    return len(loaded_export), gaps_after


def overlay_merged_contacts_into_cache(cache_path: Path, contacts: dict[str, dict]) -> dict:
    data: dict = {}
    if cache_path.is_file():
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {"contacts": recover_contacts_from_cache_file(cache_path)}
    if not isinstance(data, dict):
        data = {}
    data["contacts"] = merge_contacts_maps(data.get("contacts") or {}, contacts)
    cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--src",
        type=Path,
        required=True,
        help="Katalog z rozpakowanymi artefaktami, Wyniki/ albo plik *_cache.json",
    )
    parser.add_argument("--wyniki", type=Path, default=ROOT / "Wyniki")
    parser.add_argument("--wyslane", type=Path, default=ROOT / "wyslane")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger("rebuild_excel_all")

    copy_supporting_files(args.src, args.wyniki, args.wyslane, logger)
    contacts = collect_contacts(args.src, logger)
    if not contacts:
        contacts = collect_contacts(args.wyniki, logger)
    if not contacts:
        raise SystemExit("Brak contacts JSON z danymi do Excela")

    cache_path = args.wyniki / CACHE_NAME
    cache = overlay_merged_contacts_into_cache(cache_path, contacts)
    xlsx = args.wyniki / XLSX_NAME
    n_rows, gaps = write_validated_excel(contacts, xlsx, cache, logger)
    if gaps:
        print(f"VERIFY_FAIL rows={n_rows} gaps={len(gaps)}")
        for g in gaps[:20]:
            print(f"  {g['url']}: {g['reason']} {g['columns']}")
        return 1
    print(f"VERIFY_OK rows={n_rows} contacts_json={len(contacts)} file={xlsx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
