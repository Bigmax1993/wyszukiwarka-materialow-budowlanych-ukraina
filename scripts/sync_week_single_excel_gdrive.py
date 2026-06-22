# -*- coding: utf-8 -*-
"""
Jednorazowy sync tygodnia discovery: jeden plik Excel na Google Drive, usuniecie starych kopii.

Uzycie (GHA lub lokalnie z OAuth):
  python scripts/sync_week_single_excel_gdrive.py \\
    --run-ids "27533750486,27638016924,27787280147,27837533068" \\
    --week-label "2026-06-15_2026-06-21"
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
for _p in (ROOT, SCRIPTS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from campaign_data_paths import GOOGLE_DRIVE_GU_FOLDER_ID  # noqa: E402
import export_week_discovery_all_to_excel as week_export  # noqa: E402
import gdrive_upload_wyniki as gdrive  # noqa: E402
from recover_pi_cache_contacts import recover_contacts_from_cache_file  # noqa: E402

_KONTAKTE_PREFIX = "de_gu_bauunternehmen_kontakte"


def _list_kontakte_xlsx(service, folder_id: str) -> list[dict]:
    q = (
        f"'{folder_id}' in parents and trashed = false and "
        f"mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' and "
        f"name contains '{_KONTAKTE_PREFIX}'"
    )
    files: list[dict] = []
    page_token = None
    while True:
        res = (
            service.files()
            .list(
                q=q,
                fields="nextPageToken, files(id,name)",
                pageSize=100,
                pageToken=page_token,
                corpora="allDrives",
                **gdrive._LIST_OPTS,
            )
            .execute()
        )
        files.extend(res.get("files") or [])
        page_token = res.get("nextPageToken")
        if not page_token:
            break
    return files


def _delete_drive_files(service, files: list[dict]) -> int:
    n = 0
    for f in files:
        fid = f.get("id")
        name = f.get("name") or fid
        if not fid:
            continue
        service.files().delete(fileId=fid, **gdrive._DRIVE_API_OPTS).execute()
        print(f"  Usunieto: {name}")
        n += 1
    return n


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Jeden Excel z tygodnia discovery na Drive (usuwa stare kopie kontakte)"
    )
    parser.add_argument("--run-ids", required=True)
    parser.add_argument("--repo", default="Bigmax1993/Wyszukiwarka-partnerow")
    parser.add_argument("--week-label", default="2026-06-15_2026-06-21")
    parser.add_argument(
        "--folder-id",
        default=os.environ.get("GDRIVE_FOLDER_ID", GOOGLE_DRIVE_GU_FOLDER_ID),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Tylko eksport lokalny, bez Drive",
    )
    args = parser.parse_args()

    import logging

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger("week_single_sync")

    excel_name = f"{_KONTAKTE_PREFIX}_{args.week_label}.xlsx"
    wyniki = ROOT / "Wyniki"
    wyniki.mkdir(parents=True, exist_ok=True)
    output = wyniki / excel_name

    run_ids = [x.strip() for x in args.run_ids.split(",") if x.strip()]
    contacts, loaded = week_export.merge_contacts_from_run_ids(run_ids, repo=args.repo)
    if not loaded:
        raise SystemExit("Nie udalo sie pobrac zadnego artefaktu pi.")
    rows, cache = week_export.export_merged_contacts(contacts, label=args.week_label)
    week_export.write_excel(rows, cache, logger, output=output)

    with_email = sum(1 for r in rows if (r.get("email_target") or "").strip())
    print(f"Excel lokalny: {output} ({len(rows)} firm, {with_email} z e-mailem)")

    if args.dry_run:
        return 0

    creds, use_oauth = gdrive._load_credentials()
    service, MediaFileUpload = gdrive._drive_service(creds)
    folder_id = gdrive._resolve_upload_folder(service, args.folder_id, use_oauth=use_oauth)

    old_files = _list_kontakte_xlsx(service, folder_id)
    if old_files:
        print(f"Usuwam {len(old_files)} starych plikow Excel ({_KONTAKTE_PREFIX}*) z Drive:")
        _delete_drive_files(service, old_files)
    else:
        print("Brak starych plikow Excel do usuniecia.")

    print(f"Upload: {excel_name}")
    gdrive._upload_file(service, MediaFileUpload, output, folder_id, version_xlsx=False)
    print(
        f"Gotowe: 1 plik na Drive ({len(rows)} firm).\n"
        f"https://drive.google.com/drive/folders/{folder_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
