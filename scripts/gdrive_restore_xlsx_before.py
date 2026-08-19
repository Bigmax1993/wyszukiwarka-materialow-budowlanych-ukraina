# -*- coding: utf-8 -*-
"""Przywroc pliki Excel (*_kontakte.xlsx) na Google Drive do wersji sprzed podanej daty."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.gdrive_upload_wyniki import (  # noqa: E402
    _DRIVE_API_OPTS,
    _LIST_OPTS,
    _default_folder_id,
    _drive_service,
    _load_credentials,
    _resolve_upload_folder,
    _upload_file,
)


def _cutoff_dt(day: str, tz_name: str) -> datetime:
    tz = ZoneInfo(tz_name)
    return datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=tz)


def _parse_drive_time(raw: str) -> datetime:
    text = (raw or "").replace("Z", "+00:00")
    return datetime.fromisoformat(text)


def _list_folder_files(service, folder_id: str) -> list[dict]:
    out: list[dict] = []
    token = None
    q = f"'{folder_id}' in parents and trashed = false"
    while True:
        res = (
            service.files()
            .list(
                q=q,
                fields="nextPageToken,files(id,name,mimeType,modifiedTime,createdTime,size)",
                pageSize=1000,
                pageToken=token,
                corpora="allDrives",
                **_LIST_OPTS,
            )
            .execute()
        )
        out.extend(res.get("files") or [])
        token = res.get("nextPageToken")
        if not token:
            break
    return out


def _list_revisions(service, file_id: str) -> list[dict]:
    out: list[dict] = []
    token = None
    while True:
        res = (
            service.revisions()
            .list(
                fileId=file_id,
                pageSize=1000,
                pageToken=token,
                fields="nextPageToken,revisions(id,modifiedTime,size,keepForever)",
            )
            .execute()
        )
        out.extend(res.get("revisions") or [])
        token = res.get("nextPageToken")
        if not token:
            break
    return out


def _download_revision(service, file_id: str, revision_id: str, dest: Path) -> None:
    from googleapiclient.http import MediaIoBaseDownload

    dest.parent.mkdir(parents=True, exist_ok=True)
    request = service.revisions().get_media(fileId=file_id, revisionId=revision_id)
    with open(dest, "wb") as handle:
        downloader = MediaIoBaseDownload(handle, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def _download_file(service, file_id: str, dest: Path) -> None:
    from googleapiclient.http import MediaIoBaseDownload

    dest.parent.mkdir(parents=True, exist_ok=True)
    request = service.files().get_media(fileId=file_id, **_DRIVE_API_OPTS)
    with open(dest, "wb") as handle:
        downloader = MediaIoBaseDownload(handle, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def _xlsx_row_count(path: Path) -> str:
    try:
        import pandas as pd

        try:
            df = pd.read_excel(path, sheet_name="Kontakte")
        except Exception:
            df = pd.read_excel(path)
        return str(len(df))
    except Exception as exc:
        return f"? ({exc})"


def _is_kontakte_xlsx(name: str) -> bool:
    lower = name.lower()
    return lower.endswith(".xlsx") and "kontakte" in lower


def _canonical_name(campaign: str) -> str:
    if campaign == "pl":
        return "pl_materialy_kontakte.xlsx"
    if campaign == "ua":
        return "ua_materialy_kontakte.xlsx"
    return "de_gu_bauunternehmen_kontakte.xlsx"


def _artifact_xlsx_before(cutoff: datetime, campaign: str, dest: Path) -> Path | None:
    """Pobierz Excel z najnowszego artefaktu GitHub utworzonego przed cutoff."""
    repo = (os.environ.get("GITHUB_REPOSITORY") or "").strip()
    token = (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or "").strip()
    if not repo or not token:
        print("Brak GITHUB_REPOSITORY/GH_TOKEN — pomijam fallback artefaktow")
        return None
    prefix = "pl-materialy-wyniki-" if campaign == "pl" else "ua-materialy-wyniki-"
    proc = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{repo}/actions/artifacts",
            "--paginate",
            "--jq",
            ".artifacts[]",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    artifacts = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            artifacts.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if proc.returncode != 0 and not artifacts:
        print(f"gh api artifacts: {proc.stderr[-400:]}")
        return None

    candidates = []
    for art in artifacts:
        name = str(art.get("name") or "")
        if not name.startswith(prefix) or art.get("expired"):
            continue
        try:
            created = _parse_drive_time(art.get("created_at") or "")
        except ValueError:
            continue
        if created < cutoff:
            candidates.append((created, art))
    if not candidates:
        print("Brak nieprzeterminowanych artefaktow GitHub sprzed cutoff")
        return None
    created, art = max(candidates, key=lambda x: x[0])
    run_id = ((art.get("workflow_run") or {}).get("id"))
    name = art.get("name")
    print(f"Fallback artefakt: {name} created={created.isoformat()} run={run_id}")
    if not run_id:
        return None
    tmp = Path(tempfile.mkdtemp(prefix="gha-art-"))
    dl = subprocess.run(
        [
            "gh",
            "run",
            "download",
            str(run_id),
            "-R",
            repo,
            "-n",
            str(name),
            "-D",
            str(tmp),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if dl.returncode != 0:
        print(f"Nie pobrano artefaktu: {dl.stderr[-400:]}")
        return None
    matches = list(tmp.rglob("*kontakte.xlsx"))
    if not matches:
        print(f"W artefakcie {name} brak *kontakte.xlsx")
        return None
    chosen = max(matches, key=lambda p: p.stat().st_size)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(chosen.read_bytes())
    return dest


def restore_campaign(campaign: str, cutoff: datetime, *, dry_run: bool) -> int:
    folder_id = _default_folder_id(campaign).strip()
    if not folder_id:
        print(f"SKIP {campaign}: brak GDRIVE_FOLDER_ID")
        return 0
    creds, use_oauth = _load_credentials()
    service, MediaFileUpload = _drive_service(creds)
    upload_folder_id = _resolve_upload_folder(service, folder_id, use_oauth=use_oauth)
    print(f"=== {campaign} folder={upload_folder_id} cutoff={cutoff.isoformat()} ===")
    files = _list_folder_files(service, upload_folder_id)
    xlsx_files = [f for f in files if _is_kontakte_xlsx(f.get("name") or "")]
    if not xlsx_files:
        xlsx_files = [f for f in files if (f.get("name") or "").lower().endswith(".xlsx")]
    if not xlsx_files:
        print("Brak plikow Excel w folderze Drive")
        return 1

    for item in sorted(xlsx_files, key=lambda x: x.get("name") or ""):
        print(
            f"  {item.get('name')} modified={item.get('modifiedTime')} "
            f"size={item.get('size')} id={item.get('id')}"
        )

    canonical = _canonical_name(campaign)
    target = next((f for f in xlsx_files if f.get("name") == canonical), None)
    source_bytes: Path | None = None
    source_label = ""

    if target:
        revisions = _list_revisions(service, target["id"])
        print(f"Rewizje {canonical}: {len(revisions)}")
        before = []
        for rev in revisions:
            try:
                when = _parse_drive_time(rev.get("modifiedTime") or "")
            except ValueError:
                continue
            if when < cutoff:
                before.append((when, rev))
            print(f"    rev {rev.get('id')} {rev.get('modifiedTime')} size={rev.get('size')}")
        if before:
            when, rev = max(before, key=lambda x: x[0])
            source_label = f"rewizja {rev.get('id')} z {when.isoformat()}"
            tmp = Path("Wyniki") / f"_restore_{canonical}"
            if not dry_run:
                _download_revision(service, target["id"], rev["id"], tmp)
                source_bytes = tmp

    if source_bytes is None:
        dated = []
        for item in xlsx_files:
            try:
                when = _parse_drive_time(item.get("modifiedTime") or "")
            except ValueError:
                continue
            if when < cutoff:
                dated.append((when, item))
        if dated:
            when, item = max(dated, key=lambda x: x[0])
            source_label = f"plik {item.get('name')} z {when.isoformat()}"
            tmp = Path("Wyniki") / f"_restore_{canonical}"
            if not dry_run:
                _download_file(service, item["id"], tmp)
                source_bytes = tmp

    if source_bytes is None:
        tmp = Path("Wyniki") / f"_restore_{canonical}"
        art = _artifact_xlsx_before(cutoff, campaign, tmp)
        if art is not None:
            source_bytes = art
            source_label = f"artefakt GitHub sprzed {cutoff.date().isoformat()}"

    if source_bytes is None and dry_run:
        print("DRY-RUN: brak zrodla sprzed cutoff (rewizja albo starszy plik)")
        return 1
    if source_bytes is None:
        print("FAIL: brak rewizji i brak starszego Excela sprzed 19.08 na Drive")
        return 1

    print(f"Zrodlo: {source_label}")
    if dry_run:
        print("DRY-RUN: pomijam zapis na Drive")
        return 0

    dest = Path("Wyniki") / canonical
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(source_bytes.read_bytes())
    rows = _xlsx_row_count(dest)
    print(f"Lokalnie {canonical}: {rows} wierszy")
    uploaded = _upload_file(service, MediaFileUpload, dest, upload_folder_id, version_xlsx=False)
    print(
        f"PRZYWROCONO {canonical} -> Drive id={uploaded} wierszy={rows} "
        f"https://drive.google.com/drive/folders/{upload_folder_id}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", choices=("pl", "ua", "gu"), default="pl")
    parser.add_argument("--before", default="2026-08-19", help="YYYY-MM-DD (Europe/Warsaw, wylacznie)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    tz = "Europe/Warsaw"
    cutoff = _cutoff_dt(args.before, tz)
    return restore_campaign(args.campaign, cutoff, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
