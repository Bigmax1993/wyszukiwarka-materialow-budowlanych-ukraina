# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from email_targeting import is_public_portal_url
import ua_materialy_scraper as scraper


class PublicPortalDomainTests(unittest.TestCase):
    def test_blocks_social_and_classifieds(self):
        blocked = (
            "https://www.facebook.com/page",
            "https://olx.ua/uk/obyavlenie",
            "https://kyiv.olx.ua/uk",
            "https://prom.ua/ua/Firma",
        )
        for url in blocked:
            with self.subTest(url=url):
                self.assertTrue(is_public_portal_url(url))

    def test_allows_company_sites(self):
        allowed = (
            "https://bud24.com.ua",
            "https://www.mada.kiev.ua",
            "https://vendor-stroy.com.ua",
        )
        for url in allowed:
            with self.subTest(url=url):
                self.assertFalse(is_public_portal_url(url))

    def test_scraper_exports_for_sunday_verify(self):
        self.assertTrue(callable(getattr(scraper, "is_public_portal_url", None)))
        self.assertTrue(scraper.is_public_portal_url("https://olx.ua/"))
        self.assertFalse(scraper.is_public_portal_url("https://bud24.com.ua"))


if __name__ == "__main__":
    unittest.main()
