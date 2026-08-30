# -*- coding: utf-8 -*-
"""
Testy regresyjne kampanii PL — słowa kluczowe, filtry, maile, rotacja województw.

  python -m unittest tests.test_pl_materialy_regression -v
  python -m pytest tests/test_pl_materialy_regression.py -v
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pl_materialy_scraper as scraper
from campaign_data_paths import GOOGLE_DRIVE_PL_FOLDER_ID, campaign_output_paths
from pl_materialy_inquiry_email_pl import (
    DEFAULT_INQUIRY_PHONE_PL,
    build_fixed_material_inquiry_pl,
    build_inquiry_signature_pl,
)
from pl_materialy_supplier_filter import (
    is_loose_serper_discovery_candidate,
    is_serper_only_pending_candidate,
    is_valid_retail_store_builder_contact,
)
from pl_wojewodztwo_keywords import (
    ALL_WOJEWODZTWA,
    SERPER_DISCOVERY_BROAD_TERMS,
    SERPER_DISCOVERY_FALLBACK_TERMS,
    SERPER_DISCOVERY_LANDKREIS_TERMS,
    SERPER_DISCOVERY_PLACES_TERMS,
    SERPER_DISCOVERY_TERMS,
    build_discovery_terms,
    build_region_suffix,
    default_max_discovery_terms_for,
)
from pl_wojewodztwo_rotation import (
    WOJEWODZTWO_ROTATION_ORDER,
    commit_rotation_after_run,
    load_rotation_state,
    peek_next_wojewodztwo,
    rotation_state_path,
)


class WojewodztwoCoverageRegression(unittest.TestCase):
    def test_all_wojewodztwa_configured(self):
        self.assertEqual(len(ALL_WOJEWODZTWA), 16)
        self.assertEqual(len(scraper.CAMPAIGN_ACTIVE_BUNDESLAENDER), 16)

    def test_countrywide_region_suffix(self):
        self.assertEqual(build_region_suffix(list(ALL_WOJEWODZTWA)), "Polska")
        self.assertEqual(build_region_suffix(["mazowieckie", "malopolskie"]), "Polska MZ MA")

    def test_discovery_terms_polish(self):
        terms = build_discovery_terms(["mazowieckie"], max_terms=10)
        self.assertGreaterEqual(len(terms), 5)
        joined = " ".join(terms).lower()
        self.assertIn("materiały", joined)
        self.assertIn("warszawa", joined.lower())

    def test_discovery_waves_exported(self):
        self.assertGreaterEqual(len(SERPER_DISCOVERY_FALLBACK_TERMS), 5)
        self.assertGreaterEqual(len(SERPER_DISCOVERY_BROAD_TERMS), 10)
        self.assertGreaterEqual(len(SERPER_DISCOVERY_LANDKREIS_TERMS), 5)
        self.assertGreaterEqual(len(SERPER_DISCOVERY_PLACES_TERMS), 5)
        self.assertGreaterEqual(len(SERPER_DISCOVERY_TERMS), 100)


class SerperConfigRegression(unittest.TestCase):
    def test_serper_pl_locale(self):
        self.assertEqual(scraper.SERPER_COUNTRY, "pl")
        self.assertEqual(scraper.SERPER_LANGUAGE, "pl")
        self.assertEqual(scraper.COUNTRY_RESTRICTION, "PL")

    def test_max_discovery_terms_scale(self):
        self.assertGreaterEqual(default_max_discovery_terms_for(list(ALL_WOJEWODZTWA)), 1000)


class SupplierFilterRegression(unittest.TestCase):
    def test_accepts_building_supplier(self):
        self.assertTrue(
            is_valid_retail_store_builder_contact(
                email="info@budmat.pl",
                url="https://www.budmat.pl/",
                name="Hurtownia Budowlana Warszawa Sp. z o.o.",
                text="Hurtownia materiałów budowlanych cement piasek żwir katalog ceny dostawa",
            )
        )

    def test_rejects_interior_design(self):
        self.assertFalse(
            is_valid_retail_store_builder_contact(
                email="info@design.pl",
                url="https://design.pl",
                name="Wykończenia wnętrz",
                text="remont mieszkań pod klucz",
            )
        )

    def test_loose_serper_candidate(self):
        self.assertTrue(
            is_loose_serper_discovery_candidate(
                url="https://budmat.pl",
                name="Skład budowlany",
                text="materiały budowlane hurt",
            )
        )

    def test_serper_only_pending(self):
        self.assertTrue(
            is_serper_only_pending_candidate(
                name="Hurtownia Kraków",
                url="https://bud-krak.pl",
                text="hurtownia budowlana cement",
            )
        )


class EmailBrandingRegression(unittest.TestCase):
    def test_default_phone(self):
        self.assertEqual(DEFAULT_INQUIRY_PHONE_PL, "516513965")
        self.assertIn("516513965", build_inquiry_signature_pl())

    def test_polish_template(self):
        body = build_fixed_material_inquiry_pl()
        self.assertIn("Szanowni Państwo", body)
        self.assertIn("materiałów budowlanych", body)
        self.assertNotIn("+380", body)

    @patch("mail_transport.send_smtp_email")
    @patch("scraper_env.get_mail_password", return_value="secret")
    @patch("scraper_env.get_mail_user", return_value="test@gmail.com")
    def test_send_email_no_attachments(self, _u, _p, mock_send):
        import logging

        mock_send.return_value = (True, "ok")
        ok, _ = scraper.send_email_pl_materialy(
            "kontakt@hurt.pl",
            "Zapytanie o dostawę materiałów budowlanych",
            build_fixed_material_inquiry_pl(),
            logging.getLogger("test"),
        )
        self.assertTrue(ok)
        self.assertEqual(mock_send.call_args.kwargs.get("attachment_paths"), [])


class WojewodztwoRotationRegression(unittest.TestCase):
    def test_rotation_order_length(self):
        self.assertEqual(len(WOJEWODZTWO_ROTATION_ORDER), 16)
        self.assertEqual(peek_next_wojewodztwo(), WOJEWODZTWO_ROTATION_ORDER[0])

    def test_commit_advances_index(self):
        tmp = Path(tempfile.mkdtemp())
        path = rotation_state_path(tmp)
        state = load_rotation_state(path)
        woj = peek_next_wojewodztwo(state)
        nxt = commit_rotation_after_run(path, state, woj)
        self.assertIn(nxt, WOJEWODZTWO_ROTATION_ORDER)
        self.assertNotEqual(nxt, woj)


class ContactDataRegression(unittest.TestCase):
    def test_polish_phone_regex(self):
        phones = scraper._find_phones_in_text_regex(
            "Zadzwoń: +48 22 123 45 67 lub 0 601 234 567"
        )
        self.assertTrue(phones)
        joined = " ".join(phones)
        self.assertIn("48", joined.replace(" ", ""))

    def test_extract_bundesland_from_plz(self):
        woj = scraper.extract_bundesland({"adres": "ul. Testowa 1, 30-001 Kraków"})
        self.assertEqual(woj, "malopolskie")

    def test_extract_bundesland_rejects_german_state(self):
        woj = scraper.extract_bundesland({"bundesland": "Sachsen", "adres": ""})
        self.assertNotEqual(woj, "Sachsen")

    def test_serper_address_not_snippet(self):
        item = {
            "snippet": "Cement portlandzki CEM I 42,5 — najlepsza cena",
            "address": "ul. Budowlana 5, 00-001 Warszawa",
        }
        self.assertEqual(scraper._extract_serper_address(item), "ul. Budowlana 5, 00-001 Warszawa")

    def test_reconcile_keeps_serper_phone(self):
        row = {"telefon": "+48 22 123 45 67", "www": "https://hurt.pl"}
        collected = {"website": "https://hurt.pl", "phones": []}
        out = scraper.reconcile_contact_sources(row, collected)
        self.assertIn("48", out["telefon"].replace(" ", ""))

    def test_pl_country_hints_polish(self):
        self.assertIn("warszawa", scraper.PL_COUNTRY_HINTS)
        self.assertNotIn("ukraine", scraper.PL_COUNTRY_HINTS)

    def test_row_enrichment_cache_ttl_and_version(self):
        cache = scraper._empty_cache()
        payload = {"company_name_clean": "Test", "address": "ul. A 1", "phone": "+48 22 123 45 67"}
        scraper._store_row_enrichment_cache_entry(cache, "https://test.pl", payload)
        self.assertEqual(
            scraper._get_row_enrichment_cache_entry(cache, "https://test.pl"),
            payload,
        )
        stale = {
            "data": payload,
            "at": (datetime.now() - timedelta(days=30)).isoformat(),
            "version": scraper.PL_CACHE_ENRICHMENT_VERSION,
        }
        cache["claude_row_enrichment"]["https://test.pl"] = stale
        self.assertIsNone(scraper._get_row_enrichment_cache_entry(cache, "https://test.pl"))

    def test_serper_discovery_cache_requires_version(self):
        cache = scraper._empty_cache()
        sd = cache.setdefault("serper_discovery", {})
        sd["search:test"] = {
            "rows": [{"url": "https://x.pl", "adres": "snippet produktu"}],
            "at": datetime.now().isoformat(),
        }
        self.assertIsNone(
            scraper.get_cached_serper_discovery_rows(cache, "test", use_places_endpoint=False)
        )

    def test_contact_cache_payload_includes_address_fields(self):
        row = {
            "nazwa": "Hurtownia",
            "adres": "ul. Test 1, 00-001 Warszawa",
            "telefon": "+48 22 123 45 67",
            "bundesland": "mazowieckie",
            "discovery_bundesland": "mazowieckie",
        }
        payload = scraper._contact_cache_payload(row, {"email_target": "kontakt@test.pl"})
        self.assertEqual(payload["full_address"], "ul. Test 1, 00-001 Warszawa")
        self.assertEqual(payload["telefon"], "+48 22 123 45 67")
        self.assertEqual(payload["bundesland"], "mazowieckie")

    def test_apply_regex_keeps_serper_phone_when_no_regex_match(self):
        row = {
            "telefon": "+48 22 999 88 77",
            "nazwa": "Hurtownia",
            "adres": "Warszawa",
        }
        out = scraper.apply_regex_row_contact_cleanup(row)
        self.assertIn("48", (out.get("telefon") or "").replace(" ", ""))

    def test_looks_like_postal_address(self):
        self.assertTrue(scraper._looks_like_postal_address("ul. Test 1, 00-001 Warszawa"))
        self.assertFalse(
            scraper._looks_like_postal_address("Cement portlandzki — najlepsza cena")
        )

    def test_extract_serper_address_empty_for_product_snippet_only(self):
        item = {"snippet": "Cement portlandzki CEM I 42,5 — promocja"}
        self.assertEqual(scraper._extract_serper_address(item), "")

    def test_extract_bundesland_uses_discovery_bundesland(self):
        woj = scraper.extract_bundesland(
            {"discovery_bundesland": "pomorskie", "adres": ""}
        )
        self.assertEqual(woj, "pomorskie")

    def test_pl_plz_prefix_map_covers_all_prefixes(self):
        self.assertEqual(len(scraper.PL_PLZ_PREFIX_TO_WOJEWODZTWO), 100)
        self.assertEqual(scraper.PL_PLZ_PREFIX_TO_WOJEWODZTWO["00"], "mazowieckie")
        self.assertEqual(scraper.PL_PLZ_PREFIX_TO_WOJEWODZTWO["30"], "malopolskie")


class CacheConfigRegression(unittest.TestCase):
    def test_cache_version_constant(self):
        self.assertEqual(scraper.PL_CACHE_ENRICHMENT_VERSION, "pl_enrichment_v2")

    def test_run_config_syncs_cache_ttl_from_discovery_days(self):
        from scraper_run_config import load_run_config_file

        mod = type("M", (), {
            "CLAUDE_DISCOVERY_CACHE_DAYS": 7,
            "SERPER_DISCOVERY_CACHE_DAYS": 99,
            "CLAUDE_ROW_ENRICHMENT_CACHE_DAYS": 99,
            "WEBSITE_CRAWL_CACHE_DAYS": 99,
        })()
        data = load_run_config_file("run_config/pl_materialy.json", ROOT)
        scraper.apply_pl_run_config_extras(mod, data)
        self.assertEqual(mod.CLAUDE_DISCOVERY_CACHE_DAYS, 7)
        self.assertEqual(mod.SERPER_DISCOVERY_CACHE_DAYS, 7)
        self.assertEqual(mod.CLAUDE_ROW_ENRICHMENT_CACHE_DAYS, 7)
        self.assertEqual(mod.WEBSITE_CRAWL_CACHE_DAYS, 7)


class CampaignPathsRegression(unittest.TestCase):
    def test_pl_output_paths_basename(self):
        paths = campaign_output_paths(ROOT, "pl_materialy")
        self.assertTrue(str(paths["cache_file"]).endswith("pl_materialy_cache.json"))
        self.assertTrue(str(paths["output_file"]).endswith("pl_materialy_kontakte.xlsx"))

    def test_pl_drive_folder_id(self):
        self.assertEqual(GOOGLE_DRIVE_PL_FOLDER_ID, "1O15CdN0TH8rx74sPP5C1GuYSweX81IGw")


if __name__ == "__main__":
    unittest.main(verbosity=2)
