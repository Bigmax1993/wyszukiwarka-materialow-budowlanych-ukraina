# -*- coding: utf-8 -*-
"""
Zbiera wszystkie Excel z Drive i z artefaktow GitHub, robi jeden plik zbiorczy:
append na kazdym arkuszu, unia kolumn, naglowki tylko po polsku.

Wiersze firm: tylko z Exceli. Puste kolumny mail/odpowiedz/cena uzupelniane
z cache JSON oraz datami z wyslane/*.eml (bez dopisywania odrzuconych firm).

  python scripts/merge_drive_excel_pl.py --campaign ua
  python scripts/merge_drive_excel_pl.py --local-dir Wyniki --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
LIBS = ROOT / "libs"
for _p in (ROOT, SCRIPTS, LIBS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from campaign_data_paths import GOOGLE_DRIVE_GU_FOLDER_ID  # noqa: E402
from excel_from_json_validate import (  # noqa: E402
    excel_row_from_json,
    first_email_from_contact,
    first_phone_from_contact,
    _s,
)
import gdrive_upload_wyniki as gdrive  # noqa: E402
from recover_pi_cache_contacts import recover_contacts_from_cache_file  # noqa: E402
from scraper_email_replies import export_columns_from_contact  # noqa: E402
from ua_excel_pl import (  # noqa: E402
    SHEET_INFO,
    SHEET_KONTAKTY,
    SHEET_OBWODY,
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

_WYSLANE_NAME_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})_(?P<time>\d{6})_(?P<local>.+)_at_(?P<domain>[^_]+)_"
)
_SENT_STATUSES = frozenset(
    {
        "sent",
        "reminder_sent",
        "reminders_complete",
        "replied",
    }
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


def _collect_cache_json(root: Path) -> list[Path]:
    out: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        low = path.name.lower()
        if low.endswith("cache.json") or low.endswith("_cache.json"):
            out.append(path)
    return out


def _collect_wyslane_eml(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.eml") if p.is_file()]


def _slim_cache_file(path: Path) -> Path:
    """Zostaw w pliku tylko contacts (bez website_crawl — setki MB)."""
    contacts = recover_contacts_from_cache_file(path)
    slim = path.with_name(path.stem + "_contacts_only.json")
    slim.write_text(
        json.dumps({"contacts": contacts}, ensure_ascii=False),
        encoding="utf-8",
    )
    try:
        path.unlink()
    except OSError:
        pass
    return slim


def _prune_heavy_non_excel(folder: Path) -> list[Path]:
    """Zostawia xlsx/eml + odchudzony cache contacts; reszte usuwa."""
    slim_caches: list[Path] = []
    for path in list(folder.rglob("*")):
        if not path.is_file():
            continue
        low = path.name.lower()
        if path.suffix.lower() in {".xlsx", ".eml"}:
            continue
        if low.endswith("cache.json") or low.endswith("_cache.json"):
            try:
                slim_caches.append(_slim_cache_file(path))
            except Exception as exc:
                print(f"    cache slim fail {path.name}: {exc}")
            continue
        try:
            path.unlink()
        except OSError:
            pass
    return slim_caches


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


def _download_github_sources(
    repo: str, dest: Path
) -> tuple[list[Path], list[Path], list[Path]]:
    artifacts = _latest_github_artifacts(repo)
    xlsx: list[Path] = []
    caches: list[Path] = []
    emls: list[Path] = []
    if not artifacts:
        return xlsx, caches, emls
    print(f"Pobieram {len(artifacts)} artefaktow GitHub (xlsx + cache + wyslane):")
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
        slim = _prune_heavy_non_excel(folder)
        found_x = _collect_xlsx(folder)
        found_e = _collect_wyslane_eml(folder)
        print(f"    Excel={len(found_x)} cache={len(slim)} eml={len(found_e)}")
        xlsx.extend(found_x)
        caches.extend(slim)
        emls.extend(found_e)
    return xlsx, caches, emls


def _email_from_wyslane_name(name: str) -> tuple[str, str]:
    """Zwraca (email, 'YYYY-MM-DD HH:MM:SS') albo ('', '')."""
    match = _WYSLANE_NAME_RE.match(name)
    if not match:
        return "", ""
    local = match.group("local").replace("_", ".")
    domain = match.group("domain")
    raw_email = f"{local}@{domain}".strip().lower()
    date = match.group("date")
    time = match.group("time")
    stamp = f"{date} {time[0:2]}:{time[2:4]}:{time[4:6]}"
    if "@" not in raw_email or raw_email.startswith("@") or raw_email.endswith("@"):
        return "", ""
    return raw_email, stamp


def sent_times_from_wyslane(eml_paths: list[Path]) -> dict[str, str]:
    """email -> najwczesniejsza data wysylki z nazwy .eml."""
    out: dict[str, str] = {}
    for path in eml_paths:
        email, stamp = _email_from_wyslane_name(path.name)
        if not email or not stamp:
            continue
        prev = out.get(email)
        if prev is None or stamp < prev:
            out[email] = stamp
    return out


def _merge_contacts_maps(paths: list[Path]) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    for path in paths:
        contacts = recover_contacts_from_cache_file(path)
        print(f"  cache {path.name}: contacts={len(contacts)}")
        for url, info in (contacts or {}).items():
            if not isinstance(info, dict):
                continue
            key = (url or "").strip() or _s(info.get("official_website"))
            if not key:
                continue
            prev = merged.get(key)
            if prev is None:
                merged[key] = dict(info)
                continue
            for k, v in info.items():
                if v in (None, "", [], {}):
                    continue
                cur = prev.get(k)
                if cur in (None, "", [], {}):
                    prev[k] = v
                elif isinstance(v, str) and isinstance(cur, str) and len(v) > len(cur):
                    prev[k] = v
    return merged


def _index_contacts_by_email(contacts: dict[str, dict]) -> dict[str, dict]:
    by_email: dict[str, dict] = {}
    for url, info in contacts.items():
        if not isinstance(info, dict):
            continue
        email = first_email_from_contact(info).lower()
        if email and email not in by_email:
            by_email[email] = info
        # also index by URL for lookup
        _ = url
    return by_email


def _fill_empty(row: dict[str, str], patch: dict[str, str]) -> int:
    n = 0
    for key, val in patch.items():
        cell = str(val or "").strip()
        if not cell:
            continue
        if str(row.get(key) or "").strip():
            continue
        row[key] = cell
        n += 1
    return n


def enrich_kontakty_rows(
    rows: list[dict[str, str]],
    *,
    contacts: dict[str, dict],
    sent_by_email: dict[str, str],
) -> tuple[list[dict[str, str]], dict[str, int]]:
    """Uzupelnia puste pola istniejacych wierszy Excel (bez nowych firm)."""
    by_email = _index_contacts_by_email(contacts)
    stats = {
        "cache_fields": 0,
        "status_maila": 0,
        "wyslano_eml": 0,
        "rows_touched": 0,
    }
    out: list[dict[str, str]] = []
    for raw in rows:
        row = normalize_record(dict(raw))
        before = dict(row)
        email = _s(row.get("E-mail")).lower()
        url = _s(row.get("URL")) or _s(row.get("Strona www"))
        info = None
        if url and url in contacts:
            info = contacts[url]
        if info is None and email:
            info = by_email.get(email)
        if info is None and url:
            url_l = url.rstrip("/").lower()
            for key, val in contacts.items():
                if _s(key).rstrip("/").lower() == url_l:
                    info = val
                    break

        if isinstance(info, dict):
            # podstawowe pola kontaktowe z JSON gdy puste w Excelu
            basic = normalize_record(excel_row_from_json(url or email, info))
            stats["cache_fields"] += _fill_empty(row, basic)
            mail_cols = export_columns_from_contact(info, lang="uk")
            stats["cache_fields"] += _fill_empty(row, mail_cols)

        status = _s(row.get("Status"))
        if status and not _s(row.get("Status maila")):
            row["Status maila"] = status
            stats["status_maila"] += 1

        if email and not _s(row.get("Wysłano")):
            stamp = sent_by_email.get(email)
            if stamp:
                row["Wysłano"] = stamp
                stats["wyslano_eml"] += 1
                if not _s(row.get("Status maila")) and status.lower() in _SENT_STATUSES:
                    row["Status maila"] = status
                elif not _s(row.get("Status maila")):
                    row["Status maila"] = "sent"

        if row != before:
            stats["rows_touched"] += 1
        out.append(row)
    return out, stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Jeden zbiorczy Excel z Drive + GitHub (wiersze Excel + uzupelnienie maili)"
    )
    parser.add_argument("--campaign", choices=("ua", "gu"), default="ua")
    parser.add_argument("--folder-id", default=None)
    parser.add_argument(
        "--local-dir",
        type=Path,
        default=None,
        help="Zamiast Drive: scal .xlsx/.json/.eml z katalogu lokalnego",
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
    eml_paths: list[Path] = []

    if args.local_dir:
        xlsx_paths = sorted(
            p for p in args.local_dir.rglob("*.xlsx") if p.name != OUTPUT_NAME
        )
        cache_paths = sorted(_collect_cache_json(args.local_dir))
        eml_paths = sorted(_collect_wyslane_eml(args.local_dir))
        print(
            f"Lokalnie: {len(xlsx_paths)} xlsx, {len(cache_paths)} cache, "
            f"{len(eml_paths)} eml"
        )
        if not xlsx_paths:
            raise SystemExit("Brak plikow Excel do scalenia.")
        sheets = merge_workbooks(xlsx_paths)
        contacts = _merge_contacts_maps(cache_paths) if cache_paths else {}
        sent_map = sent_times_from_wyslane(eml_paths)
        sheets[SHEET_KONTAKTY], stats = enrich_kontakty_rows(
            sheets.get(SHEET_KONTAKTY) or [],
            contacts=contacts,
            sent_by_email=sent_map,
        )
        print(f"Uzupelniono Kontakty: {stats}")
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
            gh_xlsx, gh_cache, gh_eml = _download_github_sources(args.repo, gh_dir)
            xlsx_paths.extend(gh_xlsx)
            cache_paths.extend(gh_cache)
            eml_paths.extend(gh_eml)

        if not xlsx_paths:
            raise SystemExit("Brak plikow Excel do scalenia (Drive + GitHub).")

        print(f"Scalam {len(xlsx_paths)} Excel:")
        sheets = merge_workbooks(xlsx_paths)
        contacts = _merge_contacts_maps(cache_paths) if cache_paths else {}
        sent_map = sent_times_from_wyslane(eml_paths)
        print(f"Wyslane eml -> {len(sent_map)} adresow e-mail z data")
        sheets[SHEET_KONTAKTY], stats = enrich_kontakty_rows(
            sheets.get(SHEET_KONTAKTY) or [],
            contacts=contacts,
            sent_by_email=sent_map,
        )
        print(f"Uzupelniono Kontakty: {stats}")
        write_merged_workbook(output, sheets)
        for name, rows in sheets.items():
            print(f"  arkusz {name}: {len(rows)} wierszy")
            if name == SHEET_KONTAKTY:
                for col in ("Status maila", "Wysłano", "Odpowiedź", "E-mail", "Cena"):
                    filled = sum(1 for r in rows if str(r.get(col) or "").strip())
                    print(f"    {col}: {filled}/{len(rows)}")

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
