# -*- coding: utf-8 -*-
"""
Zbiera wszystkie Excel z folderu Drive UA, robi jeden plik zbiorczy:
append na kazdym arkuszu, unia kolumn, naglowki tylko po polsku.

  python scripts/merge_drive_excel_pl.py --campaign ua
  python scripts/merge_drive_excel_pl.py --local-dir Wyniki --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
for _p in (ROOT, SCRIPTS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from campaign_data_paths import GOOGLE_DRIVE_GU_FOLDER_ID  # noqa: E402
import gdrive_upload_wyniki as gdrive  # noqa: E402
from ua_excel_pl import merge_workbooks, write_merged_workbook  # noqa: E402

OUTPUT_NAME = "ua_materialy_zbiorczy.xlsx"


def _default_folder_id(campaign: str) -> str:
    explicit = gdrive._normalize_folder_id(os.environ.get("GDRIVE_FOLDER_ID") or "")
    if explicit:
        return explicit
    if campaign == "ua":
        return gdrive._normalize_folder_id(os.environ.get("GDRIVE_FOLDER_ID_UA") or "")
    return gdrive._normalize_folder_id(
        os.environ.get("GDRIVE_FOLDER_ID") or GOOGLE_DRIVE_GU_FOLDER_ID
    )


def _merge_local_xlsx(paths: list[Path], output: Path) -> dict:
    xlsx = [p for p in paths if p.suffix.lower() == ".xlsx" and p.name != OUTPUT_NAME]
    xlsx.sort(key=lambda p: (p.stat().st_mtime, p.name))
    if not xlsx:
        raise SystemExit("Brak plikow .xlsx do scalenia.")
    print(f"Scalam {len(xlsx)} plikow:")
    for p in xlsx:
        print(f"  {p.name}")
    sheets = merge_workbooks(xlsx)
    write_merged_workbook(output, sheets)
    for name, rows in sheets.items():
        print(f"  arkusz {name}: {len(rows)} wierszy")
    return sheets


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Jeden zbiorczy Excel z Drive (kolumny po polsku, append)"
    )
    parser.add_argument("--campaign", choices=("ua", "gu"), default="ua")
    parser.add_argument("--folder-id", default=None)
    parser.add_argument(
        "--local-dir",
        type=Path,
        default=None,
        help="Zamiast Drive: scal .xlsx z katalogu lokalnego",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=f"Lokalna sciezka zapisu (domyslnie Wyniki/{OUTPUT_NAME})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Tylko zapis lokalny, bez uploadu na Drive",
    )
    args = parser.parse_args()

    output = args.output or (ROOT / "Wyniki" / OUTPUT_NAME)
    output.parent.mkdir(parents=True, exist_ok=True)

    if args.local_dir:
        paths = sorted(args.local_dir.glob("*.xlsx"))
        _merge_local_xlsx(paths, output)
        print(f"Zapisano: {output}")
        return 0

    creds, use_oauth = gdrive._load_credentials()
    service, MediaFileUpload = gdrive._drive_service(creds)
    folder_id = args.folder_id or _default_folder_id(args.campaign)
    folder_id, corpora = gdrive._resolve_upload_folder(
        service, folder_id, use_oauth=use_oauth
    )

    remote = gdrive.list_xlsx_in_folder(service, folder_id, corpora=corpora)
    remote = [f for f in remote if (f.get("name") or "") != OUTPUT_NAME]
    if not remote:
        raise SystemExit("Brak plikow Excel na Drive do scalenia.")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        local_paths: list[Path] = []
        print(f"Pobieram {len(remote)} Excel z Drive:")
        for meta in remote:
            name = meta.get("name") or f"{meta.get('id')}.xlsx"
            dest = tmp_dir / name
            print(f"  {name}")
            gdrive.download_drive_file(service, meta["id"], dest)
            local_paths.append(dest)
        _merge_local_xlsx(local_paths, output)

    print(f"Lokalnie: {output}")
    if args.dry_run:
        return 0

    gdrive._upload_file(
        service,
        MediaFileUpload,
        output,
        folder_id,
        version_xlsx=False,
        corpora=corpora,
    )
    print(
        f"Upload: {OUTPUT_NAME} (nadpisuje ten sam plik, bez daty).\n"
        f"https://drive.google.com/drive/folders/{folder_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
