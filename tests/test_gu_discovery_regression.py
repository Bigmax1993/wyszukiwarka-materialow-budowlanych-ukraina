# -*- coding: utf-8 -*-
"""
Testy regresyjne discovery GU (serper-only, małe firmy, limit Serper, rotacja).

Uruchomienie:
  python tests/test_gu_discovery_regression.py
  python -m unittest tests.test_gu_discovery_regression -v
"""
from __future__ import annotations

import logging
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import de_gu_bauunternehmen_scraper as scraper
from retail_store_builder_filter import (
    is_loose_serper_discovery_candidate,
    is_serper_only_pending_candidate,
)

_LOGGER = logging.getLogger("test_gu_discovery_regression")


class SerperLimitRegression(unittest.TestCase):
    def test_reset_clears_daily_counter(self):
        cache = scraper._empty_cache()
        today = scraper.campaign_today()
        cache.setdefault("serper_daily", {})[today] = 300
        cache.setdefault("serper_limit_reached", {})[today] = True
        scraper.reset_serper_daily_for_discovery(cache)
        self.assertEqual(cache["serper_daily"][today], 0)
        self.assertNotIn(today, cache.get("serper_limit_reached", {}))

    def test_ensure_budget_raises_when_exhausted(self):
        cache = scraper._empty_cache()
        today = scraper.campaign_today()
        cache["serper_daily"][today] = scraper.SERPER_DAILY_LIMIT
        with self.assertRaises(RuntimeError):
            scraper.ensure_serper_budget_or_fail(cache)

    def test_ensure_budget_ok_after_reset(self):
        cache = scraper._empty_cache()
        scraper.reset_serper_daily_for_discovery(cache)
        scraper.ensure_serper_budget_or_fail(cache)
        _, used, remaining = scraper.get_remaining_daily_serper_limit(cache)
        self.assertEqual(used, 0)
        self.assertEqual(remaining, scraper.SERPER_DAILY_LIMIT)

    def test_empty_serper_cache_respects_ttl(self):
        cache = scraper._empty_cache()
        cache.setdefault("serper_discovery", {})
        key = scraper._serper_discovery_cache_key("test query", use_places_endpoint=False)
        cache["serper_discovery"][key] = {
            "empty": True,
            "at": datetime.now().isoformat(),
            "rows": [],
        }
        rows = scraper.get_cached_serper_discovery_rows(
            cache, "test query", use_places_endpoint=False
        )
        self.assertEqual(rows, [])

    def test_empty_serper_cache_expires_after_ttl(self):
        cache = scraper._empty_cache()
        cache.setdefault("serper_discovery", {})
        key = scraper._serper_discovery_cache_key("stale query", use_places_endpoint=False)
        old = datetime.now() - timedelta(days=scraper.SERPER_DISCOVERY_EMPTY_CACHE_DAYS + 1)
        cache["serper_discovery"][key] = {
            "empty": True,
            "at": old.isoformat(),
            "rows": [],
        }
        self.assertIsNone(
            scraper.get_cached_serper_discovery_rows(
                cache, "stale query", use_places_endpoint=False
            )
        )


class SerperOnlyFilterRegression(unittest.TestCase):
    def test_accepts_ladenbau_without_neubau_in_snippet(self):
        self.assertTrue(
            is_serper_only_pending_candidate(
                name="HELIA Ladenbau GmbH",
                url="https://helia-ladenbau.de",
                text="Ladenbau in Ulm",
            )
        )

    def test_accepts_generalunternehmer_filialbau(self):
        self.assertTrue(
            is_serper_only_pending_candidate(
                name="Bau GmbH",
                text="Generalunternehmer Filialbau Gewerbe",
            )
        )

    def test_rejects_media_publisher(self):
        self.assertFalse(
            is_serper_only_pending_candidate(
                url="https://www.hi-heute.de/supermarkte",
                name="hi-heute.de",
                text="Supermarkt Nachrichten",
            )
        )

    def test_rejects_retail_operator(self):
        self.assertFalse(
            is_serper_only_pending_candidate(
                url="https://www.rewe.de/shop",
                name="REWE Markt",
                text="Öffnungszeiten Prospekt",
            )
        )

    def test_serper_only_looser_than_loose_filter(self):
        """Serper-only akceptuje GU+Gewerbe bez Neubau/Umbau w snippetcie."""
        name = "Bau GmbH"
        url = "https://example-bau-stuttgart.de"
        text = "Generalunternehmer Stuttgart Gewerbebau Handwerk"
        self.assertTrue(
            is_serper_only_pending_candidate(name=name, text=text, url=url)
        )
        self.assertFalse(
            is_loose_serper_discovery_candidate(name=name, text=text, url=url)
        )

    def test_pending_row_eligible_for_excel(self):
        row = {
            "nazwa": "HELIA Ladenbau GmbH",
            "url": "https://helia-ladenbau.de",
            "www": "https://helia-ladenbau.de",
            "retail_verified": False,
            "verification_reason": scraper.PENDING_WWW_VERIFY_REASON,
            "email_target": "",
        }
        self.assertTrue(scraper.is_row_eligible_for_excel_export(row))


class SmallCompanyFilterRegression(unittest.TestCase):
    def test_rejects_hochtief_domain(self):
        large, reason = scraper.is_likely_large_company(
            "Bau AG", "https://www.hochtief.de", "Generalunternehmer"
        )
        self.assertTrue(large)
        self.assertIn("hochtief", reason)

    def test_rejects_strabag_name(self):
        large, _ = scraper.is_likely_large_company(
            "STRABAG AG", "https://strabag-example.de", ""
        )
        self.assertTrue(large)

    def test_accepts_familienunternehmen_ladenbau(self):
        large, reason = scraper.is_likely_large_company(
            "HELIA Ladenbau GmbH",
            "https://helia-ladenbau.de",
            "Familienunternehmen regional tätig Bauunternehmen Ladenbau",
        )
        self.assertFalse(large, reason)

    def test_accepts_gmbh_co_kg_without_konzern(self):
        large, reason = scraper.is_likely_large_company(
            "Jela Ladenbau GmbH & Co. KG",
            "https://jela-ladenbau.de",
            "Ladenbau Neubau regional",
        )
        self.assertFalse(large, reason)

    def test_rejects_gmbh_co_kg_with_konzern_signal(self):
        large, reason = scraper.is_likely_large_company(
            "Bau GmbH & Co. KG",
            "https://example.de",
            "Teil des Konzerns weltweit tätig",
        )
        self.assertTrue(large)
        self.assertIn("grosses_unternehmen", reason)


class SmallLadenbauVerifyRegression(unittest.TestCase):
    def test_is_small_ladenbau_specialist(self):
        self.assertTrue(
            scraper._is_small_ladenbau_specialist(
                "Müller-Ladenbau GmbH",
                "https://mueller-ladenbau.de",
                "Wir realisieren Neubau und Umbau von Gewerbeobjekten.",
            )
        )

    def test_rejects_without_ladenbau_in_name(self):
        self.assertFalse(
            scraper._is_small_ladenbau_specialist(
                "Allgemeine Bau GmbH",
                "https://allgemein-bau.de",
                "Neubau Gewerbe",
            )
        )

    @patch.object(scraper, "gather_website_text_for_verification")
    def test_verify_small_ladenbau_path(self, mock_gather):
        mock_gather.return_value = (
            "Wir realisieren Ladenbau und Gewerbebau Neubau regional.",
            ["https://helia-ladenbau.de"],
        )
        result = scraper.verify_company_on_website(
            "HELIA Ladenbau GmbH",
            "https://helia-ladenbau.de",
            _LOGGER,
            {},
        )
        self.assertTrue(result["verified"])
        self.assertEqual(result["verification_reason"], "kleiner_ladenbau_gu")
        self.assertTrue(result["is_small_firm"])

    @patch.object(scraper, "gather_website_text_for_verification")
    def test_verify_rejects_large_konzern(self, mock_gather):
        mock_gather.return_value = (
            "STRABAG Konzern weltweit taetig tausend Mitarbeiter",
            ["https://www.strabag.com"],
        )
        result = scraper.verify_company_on_website(
            "STRABAG SE",
            "https://www.strabag.com",
            _LOGGER,
            {},
        )
        self.assertFalse(result["verified"])
        self.assertIn("grosses_unternehmen", result["verification_reason"])


class BundeslandCountsRegression(unittest.TestCase):
    def test_count_pending_for_land(self):
        rows = [
            {
                "url": "https://a-ladenbau.de",
                "verification_reason": scraper.PENDING_WWW_VERIFY_REASON,
                "retail_verified": False,
                "discovery_bundesland": "Niedersachsen",
            },
            {
                "url": "https://b-ladenbau.de",
                "verification_reason": scraper.PENDING_WWW_VERIFY_REASON,
                "retail_verified": False,
                "discovery_bundesland": "Niedersachsen",
            },
            {
                "url": "https://c-verified.de",
                "retail_verified": True,
                "discovery_bundesland": "Niedersachsen",
            },
        ]
        cache = {
            "contacts": {
                "https://d-ladenbau.de": {
                    "verification_reason": scraper.PENDING_WWW_VERIFY_REASON,
                    "retail_verified": False,
                    "discovery_bundesland": "Niedersachsen",
                }
            }
        }
        self.assertEqual(
            scraper.count_pending_for_bundesland(rows, cache, "Niedersachsen"), 3
        )

    def test_count_verified_for_land(self):
        rows = [
            {
                "url": "https://v1.de",
                "retail_verified": True,
                "discovery_bundesland": "Bayern",
            },
            {
                "url": "https://v2.de",
                "retail_verified": True,
                "discovery_bundesland": "Bayern",
            },
        ]
        self.assertEqual(
            scraper.count_retail_verified_for_bundesland(rows, "Bayern"), 2
        )


class DiscoveryFunnelRegression(unittest.TestCase):
    def test_funnel_counters_increment(self):
        funnel = scraper.new_discovery_funnel()
        funnel["serper_queries"] = 10
        funnel["raw_hits"] = 40
        funnel["filtered_serper"] = 15
        funnel["filtered_large_serper"] = 5
        funnel["pending_saved"] = 20
        funnel["api_zero_terms"] = 3
        self.assertEqual(funnel["pending_saved"], 20)
        with self.assertLogs(_LOGGER, level="INFO") as captured:
            scraper.log_discovery_funnel(funnel, _LOGGER)
        self.assertTrue(any("[LEjek]" in m for m in captured.output))


class RotationThresholdRegression(unittest.TestCase):
    def test_rotation_commit_when_pending_enough(self):
        from gu_bundesland_rotation import (
            BUNDESLAND_ROTATION_ORDER,
            commit_rotation_after_run,
            load_rotation_state,
            peek_next_bundesland,
            rotation_state_path,
        )
        import tempfile

        tmp = Path(tempfile.mkdtemp())
        path = rotation_state_path(tmp)
        state = load_rotation_state(path)
        land = peek_next_bundesland(state)
        pending = scraper.MIN_VERIFIED_CONTACTS_ROTATION
        verified = 0
        should_rotate = (
            verified >= scraper.MIN_VERIFIED_CONTACTS_ROTATION
            or pending >= scraper.MIN_VERIFIED_CONTACTS_ROTATION
        )
        self.assertTrue(should_rotate)
        nxt = commit_rotation_after_run(path, state, land)
        self.assertIn(nxt, BUNDESLAND_ROTATION_ORDER)

    def test_rotation_stays_when_below_threshold(self):
        pending = scraper.MIN_VERIFIED_CONTACTS_ROTATION - 1
        verified = 0
        should_rotate = (
            verified >= scraper.MIN_VERIFIED_CONTACTS_ROTATION
            or pending >= scraper.MIN_VERIFIED_CONTACTS_ROTATION
        )
        self.assertFalse(should_rotate)


if __name__ == "__main__":
    unittest.main(verbosity=2)
