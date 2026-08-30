# -*- coding: utf-8 -*-
"""
Przenies status wysylek (sent, suppression, dzienne liczniki) z poprzedniego cache
do scalonego cache tygodnia — unika podwojnych maili do tych samych firm.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import de_gu_bauunternehmen_scraper as scraper  # noqa: E402


def _norm_name(name: str) -> str:
    s = (name or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _company_key(info: dict) -> str:
    name = (
        info.get("company_name_clean")
        or info.get("company_name")
        or info.get("company_name_raw")
        or ""
    )
    return _norm_name(name)[:80]


def _domain_from_info(info: dict, place_url: str = "") -> str:
    url = (place_url or info.get("official_website") or "").strip().lower()
    if not url:
        return ""
    host = re.sub(r"^https?://", "", url).split("/")[0]
    if host.startswith("www."):
        host = host[4:]
    if host in ("northdata.de", "www.northdata.de"):
        return ""
    return host


def merge_sent_state(target: dict, source: dict, logger: logging.Logger) -> int:
    """Zwraca liczbe kontaktow oznaczonych jako sent w target."""
    src_contacts = source.get("contacts") or {}
    tgt_contacts = target.setdefault("contacts", {})
    if not isinstance(src_contacts, dict) or not isinstance(tgt_contacts, dict):
        return 0

    sent_emails: set[str] = set()
    sent_keys: set[str] = set()
    sent_domains: set[str] = set()
    for _url, info in src_contacts.items():
        if not isinstance(info, dict):
            continue
        if (info.get("email_status") or "").strip().lower() != "sent":
            continue
        em = (info.get("email_target") or "").strip().lower()
        if em:
            sent_emails.add(em)
        key = _company_key(info)
        if key:
            sent_keys.add(key)
        dom = _domain_from_info(info, _url)
        if dom:
            sent_domains.add(dom)

    for bucket in ("email_suppression", "email_sent_targets", "email_daily", "email_domain_daily"):
        src_val = source.get(bucket)
        if isinstance(src_val, dict) and src_val:
            merged = target.setdefault(bucket, {})
            if isinstance(merged, dict):
                for k, v in src_val.items():
                    merged[k] = v

    marked = 0
    for place_url, info in tgt_contacts.items():
        if not isinstance(info, dict):
            continue
        em = (info.get("email_target") or "").strip().lower()
        key = _company_key(info)
        dom = _domain_from_info(info, place_url)
        if em and em in sent_emails:
            info["email_status"] = "sent"
            marked += 1
            continue
        if key and key in sent_keys:
            info["email_status"] = "sent"
            marked += 1
            continue
        if dom and dom in sent_domains:
            info["email_status"] = "sent"
            marked += 1

    if marked:
        logger.info("Oznaczono %s kontaktow jako sent (z poprzedniego cache)", marked)
    return marked


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--prior-cache",
        type=Path,
        required=True,
        help="Sciezka do cache z ostatniej wysylki (de-gu-wyniki-tue)",
    )
    parser.add_argument(
        "--target-cache",
        type=Path,
        default=scraper.CACHE_FILE,
        help="Cache docelowy (domyslnie Wyniki/de_gu_bauunternehmen_cache.json)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger("apply_prior_send")

    with open(args.prior_cache, encoding="utf-8") as f:
        source = json.load(f)
    with open(args.target_cache, encoding="utf-8") as f:
        target = json.load(f)

    n = merge_sent_state(target, source, logger)
    scraper.save_cache(target, logger)
    print(f"Zapisano cache: {args.target_cache} (sent przeniesione: {n})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
