# -*- coding: utf-8 -*-
"""
Upload folderu Wyniki/ (+ opcjonalnie wyslane/) do Google Drive.

Konto usługowe nie ma własnej przestrzeni dyskowej — pliki muszą trafić na
Shared Drive (dysk zespołowy) albo upload w imieniu użytkownika (delegacja DWD).

Zmienne:
  GDRIVE_SERVICE_ACCOUNT_JSON / GDRIVE_SERVICE_ACCOUNT_FILE
  GDRIVE_FOLDER_ID — docelowy folder (domyślnie GU Bauunternehmen)
  GDRIVE_SHARED_DRIVE_ID — opcjonalnie ID dysku współdzielonego (auto-wykrywanie, jeśli puste)
  GDRIVE_IMPERSONATE_EMAIL — opcjonalnie e-mail użytkownika Workspace (domain-wide delegation)
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from campaign_data_paths import (  # noqa: E402
    GOOGLE_DRIVE_GU_FOLDER_ID,
    resolve_data_root,
    wyniki_dir,
    wyslane_dir,
)

# Pełny dostęp do Drive (wymagany dla Shared Drive i nadpisywania plików).
SCOPES = ("https://www.googleapis.com/auth/drive",)

_DRIVE_OPTS = {
    "supportsAllDrives": True,
    "includeItemsFromAllDrives": True,
    "supportsTeamDrives": True,
}

_GU_FOLDER_NAME = "GU Bauunternehmen Wyniki"


def _load_credentials():
    try:
        from google.oauth2 import service_account
    except ImportError as e:
        raise SystemExit(
            "Zainstaluj: pip install google-api-python-client google-auth\n" + str(e)
        ) from e

    raw = (os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON") or "").strip()
    path = (os.environ.get("GDRIVE_SERVICE_ACCOUNT_FILE") or "").strip()
    if raw:
        if raw.startswith("AIza"):
            raise SystemExit(
                "GDRIVE_SERVICE_ACCOUNT_JSON wyglada na klucz API (AIza...). "
                "Wklej caly plik JSON z Konta uslugi -> Klucze (type=service_account)."
            )
        try:
            info = json.loads(raw)
        except json.JSONDecodeError as e:
            raise SystemExit(
                f"GDRIVE_SERVICE_ACCOUNT_JSON nie jest poprawnym JSON: {e}. "
                "W GitHub Secrets wklej cala tresc pobranego pliku .json."
            ) from e
        if info.get("type") != "service_account" or not info.get("client_email"):
            raise SystemExit(
                "JSON musi byc kluczem konta uslugowego (type=service_account, client_email)."
            )
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    elif path and Path(path).is_file():
        creds = service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
    else:
        raise SystemExit(
            "Ustaw GDRIVE_SERVICE_ACCOUNT_JSON (treść) lub GDRIVE_SERVICE_ACCOUNT_FILE (ścieżka)."
        )

    impersonate = (os.environ.get("GDRIVE_IMPERSONATE_EMAIL") or "").strip()
    if impersonate:
        creds = creds.with_subject(impersonate)
        print(f"Delegacja DWD: upload w imieniu {impersonate}")
    return creds


def _drive_service(creds):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    return service, MediaFileUpload


def _folder_metadata(service, folder_id: str) -> dict:
    return (
        service.files()
        .get(
            fileId=folder_id,
            fields="id,name,driveId,mimeType,parents",
            **_DRIVE_OPTS,
        )
        .execute()
    )


def _list_shared_drives(service) -> list[dict]:
    drives: list[dict] = []
    page_token = None
    while True:
        res = (
            service.drives()
            .list(pageSize=100, pageToken=page_token, fields="nextPageToken,drives(id,name)")
            .execute()
        )
        drives.extend(res.get("drives") or [])
        page_token = res.get("nextPageToken")
        if not page_token:
            break
    return drives


def _find_folder_in_parent(service, parent_id: str, name: str) -> str | None:
    safe_name = name.replace("'", "\\'")
    q = (
        f"'{parent_id}' in parents and name = '{safe_name}' "
        f"and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    )
    res = (
        service.files()
        .list(q=q, fields="files(id)", pageSize=1, corpora="allDrives", **_DRIVE_OPTS)
        .execute()
    )
    files = res.get("files") or []
    return files[0]["id"] if files else None


def _create_folder(service, parent_id: str, name: str, *, drive_id: str | None = None) -> str:
    meta: dict = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    if drive_id:
        meta["driveId"] = drive_id
    created = service.files().create(body=meta, fields="id", **_DRIVE_OPTS).execute()
    return created["id"]


def _resolve_shared_drive_upload_folder(service, preferred_folder_id: str) -> tuple[str, str]:
    """
    Zwraca (folder_id, shared_drive_id) do uploadu na Shared Drive.
    """
    configured_drive = (os.environ.get("GDRIVE_SHARED_DRIVE_ID") or "").strip()
    drives = _list_shared_drives(service)
    if configured_drive:
        drive_ids = {d["id"] for d in drives}
        if configured_drive not in drive_ids and drives:
            print(
                f"Uwaga: GDRIVE_SHARED_DRIVE_ID={configured_drive} niedostepny; "
                f"uzywam {drives[0]['name']}"
            )
            shared_drive_id = drives[0]["id"]
        elif configured_drive in drive_ids or not drives:
            shared_drive_id = configured_drive
        else:
            raise SystemExit(
                "Brak dostepnych Shared Drives dla konta uslugowego. "
                "Dodaj je jako czlonka dysku wspoldzielonego (Content manager)."
            )
    elif drives:
        shared_drive_id = drives[0]["id"]
        print(f"Shared Drive: {drives[0].get('name', shared_drive_id)}")
    else:
        raise SystemExit(
            "Konto uslugowe nie widzi zadnego Shared Drive. "
            "Utworz dysk wspoldzielony w Google Workspace, dodaj tam "
            "e-mail konta uslugowego (Edytor / Content manager), "
            "opcjonalnie ustaw secret GDRIVE_SHARED_DRIVE_ID."
        )

    try:
        meta = _folder_metadata(service, preferred_folder_id)
        if meta.get("driveId"):
            print(f"Folder docelowy jest na Shared Drive: {meta.get('name', preferred_folder_id)}")
            return preferred_folder_id, meta["driveId"]
    except Exception:
        pass

    existing = _find_folder_in_parent(service, shared_drive_id, _GU_FOLDER_NAME)
    if existing:
        print(f"Uzywam folderu na Shared Drive: {_GU_FOLDER_NAME} ({existing})")
        return existing, shared_drive_id

    created = _create_folder(
        service, shared_drive_id, _GU_FOLDER_NAME, drive_id=shared_drive_id
    )
    print(f"Utworzono folder na Shared Drive: {_GU_FOLDER_NAME} ({created})")
    return created, shared_drive_id


def _resolve_upload_folder(service, folder_id: str) -> str:
    """Ustal folder, do którego można uploadować (Shared Drive lub impersonacja)."""
    try:
        meta = _folder_metadata(service, folder_id)
        if meta.get("driveId"):
            print(f"Upload na Shared Drive (folder: {meta.get('name', folder_id)})")
            return folder_id
    except Exception as exc:
        print(f"Nie mozna odczytac folderu {folder_id}: {exc}")

    if (os.environ.get("GDRIVE_IMPERSONATE_EMAIL") or "").strip():
        print(f"Upload przez delegacje do folderu {folder_id}")
        return folder_id

    print(
        "Folder jest na 'Moim dysku' — konto uslugowe nie moze tam zapisywac plikow. "
        "Przelaczam na Shared Drive..."
    )
    upload_id, _drive = _resolve_shared_drive_upload_folder(service, folder_id)
    return upload_id


def _find_or_create_folder(service, parent_id: str, name: str) -> str:
    existing = _find_folder_in_parent(service, parent_id, name)
    if existing:
        return existing
    return _create_folder(service, parent_id, name)


def _upload_file(service, MediaFileUpload, local: Path, parent_id: str) -> str:
    mime, _ = mimetypes.guess_type(str(local))
    media = MediaFileUpload(str(local), mimetype=mime or "application/octet-stream", resumable=True)
    safe_name = local.name.replace("'", "\\'")
    q = f"'{parent_id}' in parents and name = '{safe_name}' and trashed = false"
    existing = (
        service.files()
        .list(q=q, fields="files(id)", pageSize=1, corpora="allDrives", **_DRIVE_OPTS)
        .execute()
        .get("files")
        or []
    )
    body = {"name": local.name, "parents": [parent_id]}
    if existing:
        fid = existing[0]["id"]
        service.files().update(fileId=fid, media_body=media, **_DRIVE_OPTS).execute()
        return fid
    created = service.files().create(body=body, media_body=media, fields="id", **_DRIVE_OPTS).execute()
    return created["id"]


def upload_files_flat(service, MediaFileUpload, local_dir: Path, drive_parent_id: str) -> int:
    if not local_dir.is_dir():
        return 0
    count = 0
    for p in sorted(local_dir.iterdir()):
        if p.is_file():
            _upload_file(service, MediaFileUpload, p, drive_parent_id)
            print(f"  OK {p.name}")
            count += 1
    return count


def upload_folder_named(
    service, MediaFileUpload, local_dir: Path, drive_parent_id: str, drive_name: str
) -> int:
    if not local_dir.is_dir():
        return 0
    sub_id = _find_or_create_folder(service, drive_parent_id, drive_name)
    count = 0
    for p in sorted(local_dir.iterdir()):
        if p.is_file():
            _upload_file(service, MediaFileUpload, p, sub_id)
            print(f"  OK {drive_name}/{p.name}")
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload Wyniki do Google Drive")
    parser.add_argument(
        "--campaign-dir",
        type=Path,
        default=ROOT,
        help="Katalog kampanii (do resolve_data_root)",
    )
    parser.add_argument(
        "--folder-id",
        default=os.environ.get("GDRIVE_FOLDER_ID", GOOGLE_DRIVE_GU_FOLDER_ID),
    )
    args = parser.parse_args()

    creds = _load_credentials()
    service, MediaFileUpload = _drive_service(creds)
    data_root = resolve_data_root(args.campaign_dir)
    upload_folder_id = _resolve_upload_folder(service, args.folder_id)

    total = 0
    w = wyniki_dir(data_root)
    if w.is_dir():
        print(f"Upload plikow z {w} -> Drive {upload_folder_id}")
        total += upload_files_flat(service, MediaFileUpload, w, upload_folder_id)
    s = wyslane_dir(data_root)
    if s.is_dir():
        print(f"Upload {s} -> Drive/wyslane/")
        total += upload_folder_named(service, MediaFileUpload, s, upload_folder_id, "wyslane")

    if total == 0:
        print(
            "Brak plikow do wyslania (puste Wyniki/). "
            "Uruchom najpierw pipeline discovery/backfill/send."
        )
        return 1

    print(
        f"Zakonczono. Plikow: {total}. Folder: "
        f"https://drive.google.com/drive/folders/{upload_folder_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
