# -*- coding: utf-8 -*-
"""
Zbiera Excel + cache JSON z Drive i z artefaktow GitHub, robi jeden plik zbiorczy:
append na kazdym arkuszu, unia kolumn, naglowki tylko po polsku.

  python scripts/merge_drive_excel_pl.py --campaign ua
  python scripts/merge_drive_excel_pl.py --local-dir Wyniki --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
for _p in (ROOT, SCRIPTS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from campaign_data_paths import GOOGLE_DRIVE_GU_FOLDER_ID  # noqa: E402
from excel_from_json_validate import excel_row_from_json  # noqa: E402
import gdrive_upload_wyniki as gdrive  # noqa: E402
from recover_pi_cache_contacts import recover_contacts_from_cache_file  # noqa: E402
from ua_excel_pl import (  # noqa: E402
    SHEET_INFO,
    SHEET_KONTAKTY,
    SHEET_OBWODY,
    append_sheet_rows,
    merge_workbooks,
    normalize_record,
    write_merged_workbook,
)

OUTPUT_NAME = "ua_materialy_zbiorczy.xlsx"
GH_ARTIFACT_NAMES = (
    "ua-materialy-wyniki-thu",
    "ua-materialy-wyniki-pi",
    "ua-materialy-wyniki-mon",
    "ua-materialy-wyniki-tue",
    "ua-materialy-wyniki-fri",
    "ua-materialy-wyniki-reminders",
)


def _default_folder_id(campaign: str) -> str:
    explicit = gdrive._normalize_folder_id(os.environ.get("GDRIVE_FOLDER_ID") or "")
    if explicit:
        return explicit
    if campaign == "ua":
        return gdrive._normalize_folder_id(os.environ.get("GDRIVE_FOLDER_ID_UA") or "")
    return gdrive._normalize_folder_id(
        os.environ.get("GDRIVE_FOLDER_ID") or GOOGLE_DRIVE_GU_FOLDER_ID
    )


def _unique_dest(folder: Path, name: str) -> Path:
    dest = folder / name
    if not dest.exists():
        return dest
    stem, suffix = dest.stem, dest.suffix
    n = 2
    while True:
        cand = folder / f"{stem}_{n}{suffix}"
        if not cand.exists():
            return cand
        n += 1


def _kontakty_from_cache(path: Path) -> list[dict[str, str]]:
    contacts = recover_contacts_from_cache_file(path)
    rows: list[dict[str, str]] = []
    for url, info in (contacts or {}).items():
        if not isinstance(info, dict):
            continue
        website = (
            (url or "").strip()
            or str(info.get("official_website") or "").strip()
            or str(info.get("email_target") or "").strip()
            or str(info.get("company_name_clean") or info.get("company_name") or "").strip()
        )
        if not website:
            continue
        rows.append(normalize_record(excel_row_from_json(url or website, info)))
    print(f"  {path.name}: cache contacts={len(contacts)} -> Kontakty={len(rows)}")
    return rows


def _append_cache_into(sheets: dict, cache_paths: list[Path]) -> None:
    for path in cache_paths:
        rows = _kontakty_from_cache(path)
        sheets[SHEET_KONTAKTY] = append_sheet_rows(
            sheets.get(SHEET_KONTAKTY) or [], rows, sheet=SHEET_KONTAKTY
        )
        obwody = [
            {
                "Nazwa firmy": r.get("Nazwa firmy", ""),
                "Obwód": r.get("Obwód", ""),
                "Adres": r.get("Adres", ""),
                "Strona www": r.get("Strona www", ""),
                "URL": r.get("URL", ""),
            }
            for r in rows
        ]
        sheets[SHEET_OBWODY] = append_sheet_rows(
            sheets.get(SHEET_OBWODY) or [], obwody, sheet=SHEET_OBWODY
        )


def _latest_github_artifacts(repo: str) -> list[dict]:
    proc = subprocess.run(
        [
            "gh",
            "api",
            "--paginate",
            f"repos/{repo}/actions/artifacts?per_page=100",
            "--jq",
            ".artifacts[] | select(.expired==false) | {name,id,created_at,run_id:.workflow_run.id}",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(f"GitHub artifacts: pominieto ({proc.stderr.strip()[:200]})")
        return []
    by_name: dict[str, dict] = {}
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        name = item.get("name") or ""
        if name not in GH_ARTIFACT_NAMES:
            continue
        prev = by_name.get(name)
        if prev is None or (item.get("created_at") or "") > (prev.get("created_at") or ""):
            by_name[name] = item
    ordered = [by_name[n] for n in GH_ARTIFACT_NAMES if n in by_name]
    return ordered


def _download_github_artifacts(repo: str, dest: Path) -> tuple[list[Path], list[Path]]:
    artifacts = _latest_github_artifacts(repo)
    xlsx: list[Path] = []
    caches: list[Path] = []
    if not artifacts:
        return xlsx, caches
    print(f"Pobieram {len(artifacts)} artefaktow GitHub:")
    for meta in artifacts:
        name = meta["name"]
        run_id = meta.get("run_id")
        folder = dest / name
        folder.mkdir(parents=True, exist_ok=True)
        print(f"  {name} (run {run_id})")
        proc = subprocess.run(
            [
                "gh",
                "run",
                "download",
                str(run_id),
                "-R",
                repo,
                "-n",
                name,
                "-D",
                str(folder),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            print(f"    pominieto: {(proc.stderr or proc.stdout)[:240]}")
            continue
        for path in folder.rglob("*"):
            if not path.is_file():
                continue
            low = path.name.lower()
            if low == OUTPUT_NAME.lower():
                continue
            if path.suffix.lower() == ".xlsx":
                xlsx.append(path)
            elif low.endswith("cache.json") or low.endswith("_cache.json"):
                caches.append(path)
    return xlsx, caches


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Jeden zbiorczy Excel z Drive + GitHub (kolumny po polsku, append)"
    )
    parser.add_argument("--campaign", choices=("ua", "gu"), default="ua")
    parser.add_argument("--folder-id", default=None)
    parser.add_argument(
        "--local-dir",
        type=Path,
        default=None,
        help="Zamiast Drive: scal .xlsx/.json z katalogu lokalnego",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=f"Lokalna sciezka zapisu (domyslnie Wyniki/{OUTPUT_NAME})",
    )
    parser.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY")
        or "Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina",
    )
    parser.add_argument(
        "--skip-github",
        action="store_true",
        help="Nie pobieraj artefaktow GitHub",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Tylko zapis lokalny, bez uploadu na Drive",
    )
    args = parser.parse_args()

    output = args.output or (ROOT / "Wyniki" / OUTPUT_NAME)
    output.parent.mkdir(parents=True, exist_ok=True)

    xlsx_paths: list[Path] = []
    cache_paths: list[Path] = []

    if args.local_dir:
        xlsx_paths = sorted(
            p for p in args.local_dir.glob("*.xlsx") if p.name != OUTPUT_NAME
        )
        cache_paths = sorted(args.local_dir.glob("*cache.json"))
        print(f"Lokalnie: {len(xlsx_paths)} xlsx, {len(cache_paths)} cache")
        sheets = merge_workbooks(xlsx_paths) if xlsx_paths else {
            SHEET_INFO: [], SHEET_KONTAKTY: [], SHEET_OBWODY: []
        }
        _append_cache_into(sheets, cache_paths)
        write_merged_workbook(output, sheets)
        for name, rows in sheets.items():
            print(f"  arkusz {name}: {len(rows)} wierszy")
        print(f"Zapisano: {output}")
        return 0

    creds, use_oauth = gdrive._load_credentials()
    service, MediaFileUpload = gdrive._drive_service(creds)
    folder_id = args.folder_id or _default_folder_id(args.campaign)
    folder_id, corpora = gdrive._resolve_upload_folder(
        service, folder_id, use_oauth=use_oauth
    )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        drive_dir = tmp_dir / "drive"
        gh_dir = tmp_dir / "github"
        drive_dir.mkdir()
        gh_dir.mkdir()

        remote_xlsx = gdrive.list_xlsx_in_folder(service, folder_id, corpora=corpora)
        remote_xlsx = [f for f in remote_xlsx if (f.get("name") or "") != OUTPUT_NAME]
        remote_json = gdrive.list_json_in_folder(service, folder_id, corpora=corpora)
        remote_sheets = gdrive.list_google_sheets_in_folder(service, folder_id, corpora=corpora)

        print(
            f"Drive: {len(remote_xlsx)} xlsx, {len(remote_json)} cache, "
            f"{len(remote_sheets)} Google Sheets"
        )
        for meta in remote_xlsx:
            name = meta.get("name") or f"{meta.get('id')}.xlsx"
            dest = _unique_dest(drive_dir, name)
            print(f"  xlsx {name}")
            gdrive.download_drive_file(service, meta["id"], dest)
            xlsx_paths.append(dest)
        for meta in remote_sheets:
            name = (meta.get("name") or meta["id"]) + ".xlsx"
            dest = _unique_dest(drive_dir, name)
            print(f"  gsheet {meta.get('name')}")
            gdrive.download_drive_file(
                service,
                meta["id"],
                dest,
                mime_type=meta.get("mimeType") or "",
            )
            xlsx_paths.append(dest)
        for meta in remote_json:
            name = meta.get("name") or f"{meta.get('id')}.json"
            dest = _unique_dest(drive_dir, name)
            print(f"  json {name}")
            gdrive.download_drive_file(service, meta["id"], dest)
            cache_paths.append(dest)

        if not args.skip_github:
            gh_xlsx, gh_cache = _download_github_artifacts(args.repo, gh_dir)
            xlsx_paths.extend(gh_xlsx)
            cache_paths.extend(gh_cache)

        if not xlsx_paths and not cache_paths:
            raise SystemExit("Brak Excel/cache do scalenia (Drive + GitHub).")

        print(f"Scalam {len(xlsx_paths)} Excel + {len(cache_paths)} cache:")
        sheets = merge_workbooks(xlsx_paths) if xlsx_paths else {
            SHEET_INFO: [], SHEET_KONTAKTY: [], SHEET_OBWODY: []
        }
        _append_cache_into(sheets, cache_paths)
        write_merged_workbook(output, sheets)
        for name, rows in sheets.items():
            print(f"  arkusz {name}: {len(rows)} wierszy")

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
