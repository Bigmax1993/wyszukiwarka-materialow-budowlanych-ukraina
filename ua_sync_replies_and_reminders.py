# -*- coding: utf-8 -*-
"""
UA: odczyt odpowiedzi Gmail (IMAP) + przypomnienia do firm bez odpowiedzi.

Harmonogram: co 3 dni (GitHub Actions lub Task Scheduler).
Przypomnienie 1: min. 3 dni po pierwszym zapytaniu; przypomnienie 2: min. 3 dni po pierwszym przypomnieniu.

Domyślnie TRYB PODGLĄDU (bez wysyłki). Aby wysłać maile:
  python ua_sync_replies_and_reminders.py --send

Przykłady:
  python ua_sync_replies_and_reminders.py
  python ua_sync_replies_and_reminders.py --send
  python ua_sync_replies_and_reminders.py --send --min-days 3 --max-send 50
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
LIBS_DIR = REPO_ROOT / "libs"
if str(LIBS_DIR) not in sys.path:
    sys.path.insert(0, str(LIBS_DIR))

from campaign_data_paths import campaign_output_paths  # noqa: E402
from polish_text import setup_module_logging  # noqa: E402
from scraper_email_replies import (  # noqa: E402
    DEFAULT_IMAP_FULL_SCAN_DAYS,
    MAX_REMINDERS_PER_CONTACT,
    UA_REMINDER_INTERVAL_DAYS,
    UA_REMINDER_INTERVAL_HOURS,
    ReplySyncConfig,
    backfill_email_sent_metadata,
    backfill_reminder_suppression_for_replies,
    build_reminder_email_for_preset,
    contact_has_any_reply,
    email_domain,
    fetch_imap_messages,
    get_pending_reminder_number,
    iter_reminder_candidates,
    load_cache,
    mark_reminder_sent,
    preset_to_config,
    save_cache,
    send_email_gmail,
    sleep_between_reminder_sends,
    suppress_reminders_for_replied_contact,
    sync_replies_to_cache,
    verify_contact_reply_from_imap,
    write_excel_with_reply_styles,
)

UA_CAMPAIGN_ID = "ua_materialy"
UA_LANG = "uk"
DAILY_EMAIL_LIMIT = 300
EMAIL_PER_DOMAIN_DAILY_LIMIT = 2
DEFAULT_MAX_SEND_PER_RUN = 100


def _paths() -> dict[str, Path]:
    paths = campaign_output_paths(REPO_ROOT, "ua_materialy")
    return paths


def ua_preset() -> dict:
    paths = _paths()
    return {
        "cache": paths["cache_file"],
        "xlsx": paths["output_file"],
        "lang": UA_LANG,
        "campaign_id": UA_CAMPAIGN_ID,
        "sheets": ("Kontakte", "Wojewodztwa"),
        "main_sheets": ("Kontakte",),
    }


def setup_logging() -> logging.Logger:
    return setup_module_logging("ua_sync_replies_and_reminders")


def rebuild_sheets_from_xlsx(
    xlsx: Path, sheet_names: tuple[str, ...], logger: logging.Logger
) -> dict[str, list[dict]]:
    import pandas as pd  # pyright: ignore[reportMissingImports]

    sheets: dict[str, list[dict]] = {}
    if not xlsx.exists():
        logger.warning("Brak Excel: %s", xlsx)
        for name in sheet_names:
            sheets[name] = []
        return sheets
    for name in sheet_names:
        try:
            df = pd.read_excel(xlsx, sheet_name=name)
            sheets[name] = df.fillna("").to_dict(orient="records")
        except Exception as exc:
            logger.warning("Arkusz '%s' pominięty: %s", name, exc)
            sheets[name] = []
    return sheets


def refresh_excel(
    preset: dict, cache: dict, config: ReplySyncConfig, logger: logging.Logger
) -> None:
    xlsx = Path(preset["xlsx"])
    sheet_names = tuple(preset.get("sheets", ("Kontakte",)))
    sheets = rebuild_sheets_from_xlsx(xlsx, sheet_names, logger)
    if sheets:
        write_excel_with_reply_styles(xlsx, sheets, cache, config, logger)


def get_remaining_daily_email_limit(cache: dict) -> tuple[str, int, int]:
    today = date.today().isoformat()
    daily = cache.setdefault("email_daily", {})
    sent_today = int(daily.get(today, 0))
    remaining = max(0, DAILY_EMAIL_LIMIT - sent_today)
    return today, sent_today, remaining


def increase_daily_email_counter(cache: dict, increment: int = 1) -> None:
    today = date.today().isoformat()
    daily = cache.setdefault("email_daily", {})
    daily[today] = int(daily.get(today, 0)) + int(increment)


def get_domain_remaining_daily_limit(cache: dict, domain: str) -> tuple[str, int, int]:
    today = date.today().isoformat()
    domain_daily = cache.setdefault("email_domain_daily", {}).setdefault(today, {})
    sent_for_domain = int(domain_daily.get(domain, 0))
    remaining = max(0, EMAIL_PER_DOMAIN_DAILY_LIMIT - sent_for_domain)
    return today, sent_for_domain, remaining


def increase_domain_daily_counter(cache: dict, domain: str, increment: int = 1) -> None:
    if not domain:
        return
    today = date.today().isoformat()
    domain_daily = cache.setdefault("email_domain_daily", {}).setdefault(today, {})
    domain_daily[domain] = int(domain_daily.get(domain, 0)) + int(increment)


def can_send_reminder(cache: dict, email_target: str) -> tuple[bool, str]:
    _today, _sent, remaining = get_remaining_daily_email_limit(cache)
    if remaining <= 0:
        return False, "daily_limit"
    dom = email_domain(email_target)
    if dom:
        _t, _ds, dom_remaining = get_domain_remaining_daily_limit(cache, dom)
        if dom_remaining <= 0:
            return False, f"domain_limit:{dom}"
    return True, ""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="UA: skan IMAP + przypomnienia (co 3 dni po braku odpowiedzi)"
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Faktycznie wyślij przypomnienia (bez tego: tylko podgląd)",
    )
    parser.add_argument(
        "--min-days",
        type=float,
        default=UA_REMINDER_INTERVAL_DAYS,
        help="Min. dni od wysyłki / poprzedniego przypomnienia",
    )
    parser.add_argument(
        "--imap-days",
        type=int,
        default=DEFAULT_IMAP_FULL_SCAN_DAYS,
        help="Ile dni wstecz skanować INBOX",
    )
    parser.add_argument(
        "--max-send",
        type=int,
        default=DEFAULT_MAX_SEND_PER_RUN,
        help="Maks. przypomnień na jedno uruchomienie",
    )
    parser.add_argument(
        "--skip-scan",
        action="store_true",
        help="Pomiń IMAP (tylko podgląd cache; przy --send wymagany jest skan)",
    )
    args = parser.parse_args()
    logger = setup_logging()

    if args.send and args.skip_scan:
        parser.error("Wysyłka przypomnień wymaga skanu IMAP (usuń --skip-scan).")

    min_hours = float(args.min_days) * 24.0
    preset = ua_preset()
    cache_path = Path(preset["cache"])
    if not cache_path.exists():
        logger.error("Brak cache: %s", cache_path)
        return 1

    os.environ.setdefault("KANBUD_PROJECT_ROOT", str(LIBS_DIR))
    cache = load_cache(cache_path)
    config = preset_to_config(preset, min_hours, args.imap_days)
    backfill_email_sent_metadata(cache, logger)
    backfill_reminder_suppression_for_replies(cache, logger)

    logger.info(
        "Tryb: %s | min. %s dni (%.0f h) | max przypomnień/kontakt: %s",
        "WYSYŁKA" if args.send else "PODGLĄD (dodaj --send)",
        args.min_days,
        min_hours,
        MAX_REMINDERS_PER_CONTACT,
    )

    messages: list = []
    if not args.skip_scan:
        since = datetime.now() - timedelta(days=args.imap_days)
        logger.info("Skan INBOX od %s (%s dni)...", since.date(), args.imap_days)
        try:
            messages = fetch_imap_messages(logger, since)
            logger.info("Pobrano %s wiadomości ze skrzynki.", len(messages))
        except Exception as exc:
            logger.error("Skan IMAP nieudany: %s", exc)
            return 1

        updated = sync_replies_to_cache(
            cache,
            config,
            logger,
            full_inbox_scan=True,
            prefetched_messages=messages,
        )
        logger.info("Zaktualizowano z maili: %s kontakt(ów)", updated)
        backfill_reminder_suppression_for_replies(cache, logger)

    candidates = iter_reminder_candidates(
        cache,
        min_hours,
        second_after_hours=min_hours,
        messages=messages if messages else None,
        config=config if messages else None,
        logger=logger if messages else None,
    )
    logger.info("Kandydaci do przypomnienia: %s", len(candidates))

    sent_count = 0
    for place_url, contact, target in candidates:
        company = (
            contact.get("company_name_clean")
            or contact.get("company_name")
            or "?"
        )
        rem_num = get_pending_reminder_number(
            contact,
            first_after_hours=min_hours,
            second_after_hours=min_hours,
        )
        if not rem_num:
            continue
        if contact_has_any_reply(contact):
            suppress_reminders_for_replied_contact(contact)
            continue
        if messages:
            if verify_contact_reply_from_imap(
                contact, config, messages, logger, cache=cache
            ):
                suppress_reminders_for_replied_contact(contact)
                logger.info("  pominięto %s — wykryto odpowiedź w skrzynce", target)
                continue
        logger.info("  → %s (%s) — przypomnienie %s/%s", target, company, rem_num, MAX_REMINDERS_PER_CONTACT)

        if not args.send:
            continue
        if sent_count >= args.max_send:
            logger.info("Osiągnięto limit --max-send=%s — reszta w następnym uruchomieniu.", args.max_send)
            break

        ok_send, reason = can_send_reminder(cache, target)
        if not ok_send:
            logger.info("Pominięto %s (%s)", target, reason)
            continue

        subject, body = build_reminder_email_for_preset(
            contact, preset, reminder_number=rem_num
        )
        ok, info = send_email_gmail(
            target,
            subject,
            body,
            logger,
            mail_type=f"przypomnienie UA {rem_num}/{MAX_REMINDERS_PER_CONTACT}",
            campaign=UA_CAMPAIGN_ID,
        )
        if ok:
            mark_reminder_sent(contact, rem_num)
            increase_daily_email_counter(cache)
            increase_domain_daily_counter(cache, email_domain(target))
            sent_count += 1
            sleep_between_reminder_sends(logger, target)
        else:
            contact["reminder_status"] = f"error: {info}"

    save_cache(cache_path, cache)
    try:
        refresh_excel(preset, cache, config, logger)
    except Exception as exc:
        logger.warning("Excel: %s", exc)

    logger.info("--- Podsumowanie ---")
    logger.info("Kandydaci: %s", len(candidates))
    if args.send:
        logger.info("Wysłane przypomnienia: %s", sent_count)
        _today, sent_today, remaining = get_remaining_daily_email_limit(cache)
        logger.info("Limit dzienny: wysłano dziś %s, pozostało %s", sent_today, remaining)
    else:
        logger.info("Aby wysłać maile, uruchom ponownie z flagą: --send")
    return 0


if __name__ == "__main__":
    sys.exit(main())
