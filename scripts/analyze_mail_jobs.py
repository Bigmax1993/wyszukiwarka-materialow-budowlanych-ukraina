# -*- coding: utf-8 -*-
"""Podglad firm kwalifikujacych sie do wysylki z aktualnego cache."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import de_gu_bauunternehmen_scraper as scraper  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-resend", action="store_true")
    args = parser.parse_args()

    logger = logging.getLogger("analyze_mail_jobs")
    jobs = scraper.build_email_jobs_from_cache_json(logger, force_resend=args.force_resend)
    cache = scraper.load_cache(logger)
    contacts = cache.get("contacts") or {}

    print(f"Contacts w cache: {len(contacts)}")
    print(f"Mail jobs gotowych do wysylki: {len(jobs)}")
    for job in jobs:
        print(
            f"  -> {job.get('email_target')} | "
            f"{(job.get('company_name') or '')[:55]}"
        )

    print("\nWszystkie kontakty z e-mailem:")
    for _url, info in sorted(
        contacts.items(),
        key=lambda x: ((x[1] or {}).get("company_name") or "").lower(),
    ):
        if not isinstance(info, dict):
            continue
        em = (info.get("email_target") or "").strip()
        if not em:
            continue
        st = (info.get("email_status") or "").strip()
        rv = "T" if info.get("retail_verified") else "F"
        name = (info.get("company_name") or "")[:45]
        print(f"  {em:38} {st:28} rv={rv} | {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
