# -*- coding: utf-8 -*-
"""
Backfill: dopisz kopie .eml z folderu wyslane/ do etykiety Gmail „wyslane” (IMAP APPEND).

Użycie lokalnie (MAIL_USER, MAIL_PASSWORD w .env):
  python scripts/backfill_wyslane_imap.py
  python scripts/backfill_wyslane_imap.py --wyslane-dir ./wyslane --dry-run

GitHub Actions: workflow „PL backfill wyslane IMAP”.
"""
from __future__ import annotations

import argparse
import email
import imaplib
import logging
import sys
import time
from email.message import Message
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIBS = ROOT / "libs"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(LIBS) not in sys.path:
    sys.path.insert(0, str(LIBS))

from campaign_data_paths import resolve_data_root, wyslane_dir  # noqa: E402
from mail_transport import (  # noqa: E402
    _imap_mailbox_names,
    _imap_port,
    _resolve_named_mailbox,
    _try_create_named_mailbox,
    get_imap_archive_folder,
    get_imap_host,
    get_mail_password,
    get_mail_user,
)


def setup_logging(verbose: bool) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger("backfill_wyslane_imap")


def iter_eml_files(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    files = sorted(folder.glob("*.eml"))
    nested = sorted(folder.glob("**/*.eml"))
    seen: set[Path] = set()
    out: list[Path] = []
    for p in files + nested:
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        out.append(p)
    return sorted(out, key=lambda p: p.name)


def load_eml(path: Path) -> Message:
    raw = path.read_bytes()
    return email.message_from_bytes(raw)


def message_id(msg: Message) -> str:
    mid = (msg.get("Message-ID") or msg.get("Message-Id") or "").strip()
    return mid.strip("<>")


def internal_date_from_message(msg: Message) -> time.struct_time:
    raw = msg.get("Date")
    if raw:
        try:
            dt = parsedate_to_datetime(raw)
            return time.localtime(dt.timestamp())
        except (TypeError, ValueError, OSError):
            pass
    return time.localtime()


def resolve_wyslane_mailbox(
    mail: imaplib.IMAP4_SSL, folder_hint: str, logger: logging.Logger
) -> str | None:
    mailbox = _resolve_named_mailbox(mail, folder_hint, logger)
    if mailbox:
        return mailbox
    return _try_create_named_mailbox(mail, folder_hint)


def message_exists_in_mailbox(
    mail: imaplib.IMAP4_SSL, mailbox: str, msg_id: str
) -> bool:
    if not msg_id:
        return False
    try:
        mail.select(f'"{mailbox}"' if " " in mailbox else mailbox, readonly=True)
        typ, data = mail.search(None, "HEADER", "Message-ID", f"<{msg_id}>")
        if typ != "OK" or not data or not data[0]:
            return False
        return bool(data[0].split())
    except Exception:
        return False


def append_eml_to_mailbox(
    mail: imaplib.IMAP4_SSL,
    mailbox: str,
    path: Path,
    msg: Message,
    logger: logging.Logger,
    *,
    dry_run: bool,
) -> bool:
    mid = message_id(msg)
    if mid and message_exists_in_mailbox(mail, mailbox, mid):
        logger.info("Pominięto (już w %s): %s", mailbox, path.name)
        return True
    if dry_run:
        logger.info("[dry-run] Dopisałbym: %s → %s", path.name, mailbox)
        return True
    payload = path.read_bytes()
    typ, data = mail.append(
        mailbox,
        "\\Seen",
        imaplib.Time2Internaldate(time.mktime(internal_date_from_message(msg))),
        payload,
    )
    if typ != "OK":
        logger.warning("APPEND nieudany %s: %s %s", path.name, typ, data)
        return False
    logger.info("Dopisano do %s: %s", mailbox, path.name)
    return True


def backfill_folder(
    wyslane_path: Path,
    logger: logging.Logger,
    *,
    dry_run: bool = False,
    folder_hint: str | None = None,
) -> tuple[int, int, int]:
    username = get_mail_user()
    password = get_mail_password()
    if not (username and password):
        raise SystemExit("Brak MAIL_USER / MAIL_PASSWORD")

    hint = (folder_hint or get_imap_archive_folder() or "wyslane").strip()
    if not hint:
        raise SystemExit("Brak MAIL_IMAP_ARCHIVE_FOLDER")

    eml_files = iter_eml_files(wyslane_path)
    if not eml_files:
        logger.warning("Brak plików .eml w %s", wyslane_path)
        return 0, 0, 0

    host = get_imap_host()
    logger.info(
        "Backfill %s plików → IMAP %s / folder „%s” (konto %s)",
        len(eml_files),
        host,
        hint,
        username,
    )

    mail = imaplib.IMAP4_SSL(host, _imap_port())
    try:
        mail.login(username, password)
        names = _imap_mailbox_names(mail)
        logger.debug("Foldery IMAP: %s", ", ".join(names[:25]))
        mailbox = resolve_wyslane_mailbox(mail, hint, logger)
        if not mailbox:
            raise SystemExit(
                f"Nie znaleziono ani nie utworzono folderu „{hint}”. "
                f"Dostępne: {', '.join(names[:15])}"
            )
        logger.info("Folder docelowy: %s", mailbox)

        ok = skip = fail = 0
        for path in eml_files:
            try:
                msg = load_eml(path)
            except Exception as exc:
                logger.warning("Nie czytam %s: %s", path.name, exc)
                fail += 1
                continue
            mid = message_id(msg)
            if mid and message_exists_in_mailbox(mail, mailbox, mid):
                logger.info("Pominięto (już w %s): %s", mailbox, path.name)
                skip += 1
                continue
            if append_eml_to_mailbox(
                mail, mailbox, path, msg, logger, dry_run=dry_run
            ):
                ok += 1
            else:
                fail += 1
        return ok, skip, fail
    finally:
        try:
            mail.logout()
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dopisz kopie .eml z wyslane/ do etykiety Gmail „wyslane” (IMAP)"
    )
    parser.add_argument(
        "--wyslane-dir",
        type=Path,
        default=None,
        help="Katalog z plikami .eml (domyślnie: wyslane/ w data root)",
    )
    parser.add_argument(
        "--imap-folder",
        default="",
        help="Nazwa folderu IMAP (domyślnie: MAIL_IMAP_ARCHIVE_FOLDER lub wyslane)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Tylko lista plików, bez IMAP APPEND",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logger = setup_logging(args.verbose)

    data_root = resolve_data_root(ROOT)
    folder = args.wyslane_dir or wyslane_dir(data_root)
    folder = folder.resolve()

    ok, skip, fail = backfill_folder(
        folder,
        logger,
        dry_run=args.dry_run,
        folder_hint=args.imap_folder or None,
    )
    logger.info("--- Podsumowanie ---")
    logger.info("Dopisano: %s | Pominięto (duplikat): %s | Błędy: %s", ok, skip, fail)
    if fail and not args.dry_run:
        return 1
    if ok == 0 and skip == 0 and not args.dry_run:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
