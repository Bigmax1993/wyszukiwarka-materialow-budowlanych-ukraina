# -*- coding: utf-8 -*-
"""
Stały załącznik PPTX do maili MFG (DE Ost + GU bundesweit).

Źródło (Google Slides):
  https://docs.google.com/presentation/d/1kBnp5x0pdgXZSPzVte9e92IUgn2A5gSe/edit

Kolejność szukania pliku:
  1. MFG_EMAIL_ATTACHMENT_PATH (env)
  2. Lokalny cache w Wyniki/ (po eksporcie z Drive API)
  3. C:\\Users\\kanbu\\Documents\\Prezentacja\\MFG_Moderner Fliesenboden.pptx
  4. Pobranie z Google Drive API (Slides → PPTX), jeśli GDRIVE_SERVICE_ACCOUNT_JSON
"""
from __future__ import annotations

import io
import logging
import os
from pathlib import Path

GOOGLE_SLIDES_PRESENTATION_ID = "1kBnp5x0pdgXZSPzVte9e92IUgn2A5gSe"
GOOGLE_SLIDES_URL = (
    "https://docs.google.com/presentation/d/"
    f"{GOOGLE_SLIDES_PRESENTATION_ID}/edit"
)

ATTACHMENT_FILENAME = "MFG_Referenzliste_Einzelhandel.pptx"
LEGACY_ATTACHMENT_PATH = Path(
    r"C:\Users\kanbu\Documents\Prezentacja\MFG_Moderner Fliesenboden.pptx"
)

# Ten sam scope co przy gdrive_oauth_setup.py (refresh token na GHA).
DRIVE_READONLY_SCOPES = ("https://www.googleapis.com/auth/drive",)
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
GOOGLE_SLIDES_MIME = "application/vnd.google-apps.presentation"


def _env_attachment_path() -> Path | None:
    raw = (os.environ.get("MFG_EMAIL_ATTACHMENT_PATH") or "").strip()
    if not raw:
        return None
    p = Path(raw).expanduser()
    return p if p.is_file() else None


def _cache_attachment_path(campaign_dir: Path) -> Path:
    from campaign_data_paths import resolve_data_root, wyniki_dir

    root = resolve_data_root(campaign_dir)
    return wyniki_dir(root) / ATTACHMENT_FILENAME


def _load_drive_readonly_credentials():
    """OAuth (GHA) lub konto usługowe — do eksportu Slides → PPTX."""
    refresh = (os.environ.get("GDRIVE_OAUTH_REFRESH_TOKEN") or "").strip()
    client_id = (os.environ.get("GDRIVE_OAUTH_CLIENT_ID") or "").strip()
    client_secret = (os.environ.get("GDRIVE_OAUTH_CLIENT_SECRET") or "").strip()
    if refresh and client_id and client_secret:
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
        except ImportError:
            return None
        creds = Credentials(
            token=None,
            refresh_token=refresh,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=list(DRIVE_READONLY_SCOPES),
        )
        creds.refresh(Request())
        return creds

    import json

    try:
        from google.oauth2 import service_account
    except ImportError:
        return None

    raw = (os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON") or "").strip()
    path = (os.environ.get("GDRIVE_SERVICE_ACCOUNT_FILE") or "").strip()
    if raw:
        info = json.loads(raw)
        return service_account.Credentials.from_service_account_info(
            info, scopes=DRIVE_READONLY_SCOPES
        )
    if path and Path(path).is_file():
        return service_account.Credentials.from_service_account_file(
            path, scopes=DRIVE_READONLY_SCOPES
        )
    return None


def _drive_download_to_buffer(service, file_id: str, mime_type: str) -> io.BytesIO:
    from googleapiclient.http import MediaIoBaseDownload

    if mime_type == GOOGLE_SLIDES_MIME:
        request = service.files().export_media(fileId=file_id, mimeType=PPTX_MIME)
    else:
        request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _status, done = downloader.next_chunk()
    buffer.seek(0)
    return buffer


def _download_slides_pptx(dest: Path, logger: logging.Logger | None = None) -> bool:
    """Pobierz PPTX z Drive: natywny Slides (export) lub wrzucony plik (get_media)."""
    try:
        from googleapiclient.discovery import build
    except ImportError:
        if logger:
            logger.warning("Brak google-api-python-client — nie pobrano PPTX ze Slides.")
        return False

    creds = _load_drive_readonly_credentials()
    if creds is None:
        return False

    dest.parent.mkdir(parents=True, exist_ok=True)
    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    file_id = GOOGLE_SLIDES_PRESENTATION_ID
    try:
        meta = (
            service.files()
            .get(fileId=file_id, fields="mimeType,name")
            .execute()
        )
        mime_type = str(meta.get("mimeType") or "")
        if logger:
            logger.info(
                "Drive: %s (mime=%s)",
                meta.get("name") or file_id,
                mime_type,
            )
        buffer = _drive_download_to_buffer(service, file_id, mime_type)
    except Exception as exc:
        if logger:
            logger.error(
                "Pobranie PPTX %s nieudane (%s). Udostępnij plik kontu OAuth "
                "lub konto usługi z GDRIVE_SERVICE_ACCOUNT_JSON.",
                file_id,
                exc,
            )
        return False
    dest.write_bytes(buffer.getvalue())
    if logger:
        logger.info(
            "Pobrano załącznik ze Slides → %s (%.1f MB)",
            dest,
            dest.stat().st_size / (1024 * 1024),
        )
    return dest.is_file() and dest.stat().st_size > 1000


def resolve_mfg_email_attachment(campaign_dir: Path) -> Path | None:
    """Zwraca ścieżkę do PPTX lub None."""
    env_p = _env_attachment_path()
    if env_p:
        return env_p
    cache_p = _cache_attachment_path(campaign_dir)
    if cache_p.is_file():
        return cache_p
    if LEGACY_ATTACHMENT_PATH.is_file():
        return LEGACY_ATTACHMENT_PATH
    return None


def ensure_mfg_email_attachment(
    campaign_dir: Path,
    logger: logging.Logger | None = None,
) -> Path | None:
    """
    Gwarantuje lokalny PPTX — pobiera ze Slides, jeśli trzeba.
    Zwraca Path lub None (wysyłka powinna się wtedy nie udać).
    """
    existing = resolve_mfg_email_attachment(campaign_dir)
    if existing:
        return existing

    cache_p = _cache_attachment_path(campaign_dir)
    if _download_slides_pptx(cache_p, logger):
        return cache_p

    if logger:
        logger.error(
            "Brak załącznika PPTX. Udostępnij Slides %s kontu usługi Google "
            "lub ustaw MFG_EMAIL_ATTACHMENT_PATH / umieść plik w %s",
            GOOGLE_SLIDES_URL,
            LEGACY_ATTACHMENT_PATH,
        )
    return None
