# -*- coding: utf-8 -*-
"""
Usuwa z folderu Drive UA wszystko oprócz:
  - ua_materialy_zbiorczy.xlsx
  - plików .json
  - plików .log
(foldery zostawia).

  python scripts/cleanup_drive_ua_keep_zbiorczy.py --campaign ua
  python scripts/cleanup_drive_ua_keep_zbiorczy.py --dry-run
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
import gdrive_upload_wyniki as gdrive  # noqa: E402

KEEP_ZBIORCZY = "ua_materialy_zbiorczy.xlsx"
FOLDER_MIME = "application/vnd.google-apps.folder"


def _default_folder_id(campaign: str) -> str:
    explicit = gdrive._normalize_folder_id(os.environ.get("GDRIVE_FOLDER_ID") or "")
    if explicit:
        return explicit
    if campaign == "ua":
        return gdrive._normalize_folder_id(os.environ.get("GDRIVE_FOLDER_ID_UA") or "")
    return gdrive._normalize_folder_id(
        os.environ.get("GDRIVE_FOLDER_ID") or GOOGLE_DRIVE_GU_FOLDER_ID
    )


def _should_keep(name: str, mime: str) -> bool:
    if mime == FOLDER_MIME:
        return True
    low = (name or "").strip().lower()
    if low == KEEP_ZBIORCZY.lower():
        return True
    if low.endswith(".json"):
        return True
    if low.endswith(".log"):
        return True
    return False


def list_all_in_folder(service, folder_id: str, *, corpora: str) -> list[dict]:
    files: list[dict] = []
    page_token = None
    while True:
        res = (
            service.files()
            .list(
                q=f"'{folder_id}' in parents and trashed = false",
                fields="nextPageToken, files(id,name,mimeType,size)",
                pageSize=100,
                pageToken=page_token,
                corpora=corpora,
                **gdrive._LIST_OPTS,
            )
            .execute()
        )
        files.extend(res.get("files") or [])
        page_token = res.get("nextPageToken")
        if not page_token:
            break
    files.sort(key=lambda f: (f.get("name") or "").lower())
    return files


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Drive UA: zostaw zbiorczy + json + log, reszte usun"
    )
    parser.add_argument("--campaign", choices=("ua", "gu"), default="ua")
    parser.add_argument("--folder-id", default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Tylko wypisz, bez usuwania",
    )
    args = parser.parse_args()

    creds, use_oauth = gdrive._load_credentials()
    service, _Media = gdrive._drive_service(creds)
    folder_id = args.folder_id or _default_folder_id(args.campaign)
    folder_id, corpora = gdrive._resolve_upload_folder(
        service, folder_id, use_oauth=use_oauth
    )

    files = list_all_in_folder(service, folder_id, corpora=corpora)
    keep = [f for f in files if _should_keep(f.get("name") or "", f.get("mimeType") or "")]
    drop = [f for f in files if f not in keep]

    print(f"Folder: {folder_id}")
    print(f"Plikow: {len(files)} (zostaw {len(keep)}, usun {len(drop)})")
    print("ZOSTAW:")
    for f in keep:
        print(f"  {f.get('name')} ({f.get('mimeType')})")
    print("USUN:")
    for f in drop:
        print(f"  {f.get('name')} ({f.get('mimeType')})")

    if args.dry_run:
        print("Dry-run — nic nie usunieto.")
        return 0

    for f in drop:
        fid = f["id"]
        name = f.get("name")
        service.files().update(
            fileId=fid,
            body={"trashed": True},
            **gdrive._DRIVE_API_OPTS,
        ).execute()
        print(f"  trashed: {name}")

    print(f"Gotowe. Usunieto {len(drop)} plikow (kosz Drive).")
    print(f"https://drive.google.com/drive/folders/{folder_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
