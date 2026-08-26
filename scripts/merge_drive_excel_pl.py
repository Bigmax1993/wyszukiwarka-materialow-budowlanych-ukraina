# -*- coding: utf-8 -*-
"""
Zbiera wszystkie Excel z Drive i z artefaktow GitHub, robi jeden plik zbiorczy:
append na kazdym arkuszu, unia kolumn, naglowki tylko po polsku.

Tylko wiersze z Exceli. Kolumny mail/odpowiedz/cena sa WYRZUCANE
(ZBIORCZY_FORBIDDEN_COLUMNS w ua_excel_pl) — nigdy nie trafiaja do zbiorczego.

  python scripts/merge_drive_excel_pl.py --campaign ua
  python scripts/merge_drive_excel_pl.py --local-dir Wyniki --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
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
import gdrive_upload_wyniki as gdrive  # noqa: E402
from ua_excel_pl import (  # noqa: E402
    SHEET_INFO,
    SHEET_KONTAKTY,
    SHEET_OBWODY,
    ZBIORCZY_FORBIDDEN_COLUMNS,
    merge_workbooks,
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


def _collect_xlsx(root: Path) -> list[Path]:
    out: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() != ".xlsx":
            continue
        if path.name.lower() == OUTPUT_NAME.lower():
            continue
        out.append(path)
    return out


def _prune_non_xlsx(folder: Path) -> None:
    for path in list(folder.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() == ".xlsx":
            continue
        try:
            path.unlink()
        except OSError:
            pass


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
    return [by_name[n] for n in GH_ARTIFACT_NAMES if n in by_name]


def _download_github_xlsx(repo: str, dest: Path) -> list[Path]:
    artifacts = _latest_github_artifacts(repo)
    xlsx: list[Path] = []
    if not artifacts:
        return xlsx
    print(f"Pobieram {len(artifacts)} artefaktow GitHub (tylko .xlsx):")
    for meta in artifacts:
        name = meta["name"]
        run_id = meta.get("run_id")
        folder = dest / name
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
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
        _prune_non_xlsx(folder)
        found = _collect_xlsx(folder)
        print(f"    Excel: {len(found)}")
        xlsx.extend(found)
    return xlsx


def _print_sheet_summary(sheets: dict) -> None:
    for name, rows in sheets.items():
        print(f"  arkusz {name}: {len(rows)} wierszy")
        if name == SHEET_KONTAKTY and rows:
            cols = list(rows[0].keys())
            forbidden = [c for c in cols if c in ZBIORCZY_FORBIDDEN_COLUMNS]
            if forbidden:
                raise SystemExit(f"Zbiorczy zawiera zakazane kolumny: {forbidden}")
            print(f"    kolumny: {cols}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Jeden zbiorczy Excel z Drive + GitHub (bez kolumn mail/cena)"
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

    if args.local_dir:
        xlsx_paths = sorted(
            p for p in args.local_dir.rglob("*.xlsx") if p.name != OUTPUT_NAME
        )
        print(f"Lokalnie: {len(xlsx_paths)} xlsx")
        if not xlsx_paths:
            raise SystemExit("Brak plikow Excel do scalenia.")
        sheets = merge_workbooks(xlsx_paths)
        write_merged_workbook(output, sheets)
        _print_sheet_summary(sheets)
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
        remote_sheets = gdrive.list_google_sheets_in_folder(service, folder_id, corpora=corpora)

        print(f"Drive: {len(remote_xlsx)} xlsx, {len(remote_sheets)} Google Sheets")
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

        if not args.skip_github:
            xlsx_paths.extend(_download_github_xlsx(args.repo, gh_dir))

        if not xlsx_paths:
            raise SystemExit("Brak plikow Excel do scalenia (Drive + GitHub).")

        print(f"Scalam {len(xlsx_paths)} Excel (bez kolumn mail/cena):")
        sheets = merge_workbooks(xlsx_paths)
        write_merged_workbook(output, sheets)
        _print_sheet_summary(sheets)

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
