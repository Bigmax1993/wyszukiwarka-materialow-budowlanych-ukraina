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

ROOT = Path(__file__).resolve().parents[2]
LEGACY_GU = ROOT / "legacy" / "de_gu"
for p in (str(ROOT), str(LEGACY_GU)):
    if p not in sys.path:
        sys.path.insert(0, p)

import de_gu_bauunternehmen_scraper as scraper
from de_gu_keywords import (
    ALL_BUNDESLAENDER,
    RETAIL_CHAINS_ROTATION,
    build_discovery_terms,
    default_max_discovery_terms_for,
)
from retail_store_builder_filter import (
    is_generalunternehmer,
    is_loose_serper_discovery_candidate,
    is_serper_only_pending_candidate,
)

_LOGGER = logging.getLogger("test_gu_discovery_regression")


class BundesweitRegression(unittest.TestCase):
    def test_default_covers_all_bundeslaender(self):
        self.assertEqual(len(ALL_BUNDESLAENDER), 16)
        self.assertEqual(len(scraper.CAMPAIGN_ACTIVE_BUNDESLAENDER), 16)

    def test_bundesweit_region_suffix_short(self):
        """Faza 3: suffix Serper bez NRW/BY/… przy ≥4 landach."""
        from de_gu_keywords import build_region_suffix

        self.assertEqual(build_region_suffix(list(ALL_BUNDESLAENDER)), "Deutschland")
        self.assertEqual(
            build_region_suffix(["Nordrhein-Westfalen", "Bayern", "Hessen", "Sachsen"]),
            "Deutschland",
        )

    def test_two_lands_keep_short_suffix(self):
        from de_gu_keywords import build_region_suffix

        suffix = build_region_suffix(["Nordrhein-Westfalen", "Bayern"])
        self.assertIn("Deutschland", suffix)
        self.assertIn("NRW", suffix)

    def test_bundesweit_has_many_discovery_terms(self):
        self.assertGreaterEqual(len(scraper.SERPER_DISCOVERY_TERMS), 500)
        self.assertGreaterEqual(
            default_max_discovery_terms_for(list(ALL_BUNDESLAENDER)), 2000
        )

    def test_serper_only_target_uses_new_rows_not_total(self):
        rows = [{"url": f"https://example.de/{i}"} for i in range(200)]
        self.assertFalse(
            scraper._discovery_target_reached(
                rows,
                total_new_rows=10,
                rotate_mode=False,
                serper_only=True,
            )
        )
        self.assertTrue(
            scraper._discovery_target_reached(
                rows,
                total_new_rows=scraper.MIN_CONTACTS_TARGET,
                rotate_mode=False,
                serper_only=True,
            )
        )


class SerperQuotaExhaustionRegression(unittest.TestCase):
    def test_detects_402_quota_error(self):
        class FakeResp:
            status_code = 402

            def json(self):
                return {"message": "Not enough credits"}

        class FakeErr(Exception):
            response = FakeResp()

        self.assertTrue(scraper._is_serper_quota_error(FakeErr()))

    def test_mark_exhausted_stops_further_discovery(self):
        cache = scraper._empty_cache()
        scraper.mark_serper_api_exhausted(cache, "402 Payment Required")
        self.assertTrue(scraper.is_serper_api_exhausted(cache))
        self.assertTrue(scraper.is_serper_limit_reached_today(cache))

    def test_process_terms_stops_when_api_exhausted(self):
        cache = scraper._empty_cache()
        scraper.mark_serper_api_exhausted(cache, "test")
        all_rows: list = []
        total, stopped = scraper._process_serper_terms(
            ["Generalunternehmer Filialbau Berlin Rewe"] * 5,
            "test",
            all_rows=all_rows,
            seen_global=set(),
            cache=cache,
            logger=_LOGGER,
            enable_auto_email=False,
            apply_distance_filter=False,
            max_new_rows=None,
            total_new_rows=0,
            stop_requested=False,
            serper_only=True,
        )
        self.assertTrue(stopped)
        self.assertEqual(total, 0)


class SerperLimitRegression(unittest.TestCase):
    def test_reset_clears_daily_counter(self):
        cache = scraper._empty_cache()
        today = scraper.campaign_today()
        cache.setdefault("serper_daily", {})[today] = 300
        cache.setdefault("serper_limit_reached", {})[today] = True
        cache["serper"] = {"q1": {"rows": []}}
        cache["serper_discovery"] = {"q2": {"empty": True, "rows": []}}
        scraper.reset_serper_daily_for_discovery(cache)
        self.assertEqual(cache["serper_daily"][today], 0)
        self.assertNotIn(today, cache.get("serper_limit_reached", {}))
        self.assertEqual(cache["serper"], {})
        self.assertEqual(cache["serper_discovery"], {})

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


class StrictGuFilterRegression(unittest.TestCase):
    def test_is_generalunternehmer_positive(self):
        ok, marker = is_generalunternehmer(
            "Weber Generalunternehmer GmbH Filialbau Supermarkt"
        )
        self.assertTrue(ok)
        self.assertEqual(marker, "generalunternehmer")

    def test_is_generalunternehmer_rejects_ladenbau_only(self):
        ok, marker = is_generalunternehmer("HELIA Ladenbau GmbH Filialbau Neubau")
        self.assertFalse(ok)
        self.assertEqual(marker, "")

    def test_is_generalunternehmer_rejects_bauunternehmen_only(self):
        ok, _ = is_generalunternehmer("Bauunternehmen Müller GmbH Gewerbebau")
        self.assertFalse(ok)


class GeoFilterRegression(unittest.TestCase):
    def test_geo_filters_disabled_by_default(self):
        self.assertFalse(scraper.ENABLE_REGION_PLZ_FILTER)
        self.assertFalse(scraper.ENABLE_DISTANCE_FROM_REGION_KM)
        self.assertFalse(scraper._geo_filters_enabled())
        self.assertTrue(scraper.location_within_region_km("München Hamburg Köln"))

    def test_is_germany_accepts_de_domain(self):
        self.assertTrue(
            scraper.is_germany_de_candidate("https://firma-bau.de/kontakt", "GU Leipzig", "")
        )

    def test_is_germany_accepts_plz_on_com_domain(self):
        self.assertTrue(
            scraper.is_germany_de_candidate(
                "https://bau-gmbh.com",
                "Bau GmbH",
                "50321 Brühl Deutschland",
            )
        )

    def test_is_germany_rejects_at_domain(self):
        self.assertFalse(
            scraper.is_germany_de_candidate("https://firma-bau.at/kontakt", "Bau Wien", "")
        )

    def test_is_germany_ignores_schweiz_in_snippet_for_de_site(self):
        """Faza 3: słowo Schweiz w opisie nie odrzuca .de."""
        self.assertTrue(
            scraper.is_germany_de_candidate(
                "https://gu-leipzig.de",
                "GU Leipzig",
                "Projekte Deutschland und Schweiz Grenzregion",
            )
        )

    def test_run_config_disables_geo_filters(self):
        import de_gu_bauunternehmen_scraper as mod

        apply = scraper.apply_gu_run_config_extras
        apply(mod, {"geo_filter_enabled": False})
        self.assertFalse(mod.ENABLE_REGION_PLZ_FILTER)
        self.assertFalse(mod.ENABLE_DISTANCE_FROM_REGION_KM)


class LooseSerperFilterRegression(unittest.TestCase):
    def test_accepts_filialbau_without_neubau(self):
        """Faza 2: Filialbau w snippetcie bez Neubau/Umbau."""
        self.assertTrue(
            is_loose_serper_discovery_candidate(
                name="Müller Filialbau GmbH",
                url="https://mueller-filialbau.de",
                text="Generalunternehmer Filialbau und Supermarktbau Referenz Rewe",
            )
        )

    def test_accepts_filialbau_specialist_without_gu_word(self):
        """Faza 2: specjalista EH bez słowa generalunternehmer."""
        self.assertTrue(
            is_loose_serper_discovery_candidate(
                name="Partner Einzelhandelsbau GmbH",
                url="https://partner-eh.de",
                text="Einzelhandelsbau und Marktbau für Rewe und Edeka in Bayern",
            )
        )

    def test_accepts_chain_from_search_term_filialbau(self):
        self.assertTrue(
            is_loose_serper_discovery_candidate(
                name="Nord Bau GmbH",
                url="https://nord-bau.de",
                text="Gewerbebau Stuttgart Referenzprojekte",
                search_term="Generalunternehmer Supermarktbau Stuttgart",
            )
        )

    def test_rejects_without_chain_or_trade_context(self):
        self.assertFalse(
            is_loose_serper_discovery_candidate(
                name="Weber GU GmbH",
                url="https://weber-gu.de",
                text="Generalunternehmer Filialbau Gewerbebau",
            )
        )

    def test_rejects_media_publisher(self):
        self.assertFalse(
            is_loose_serper_discovery_candidate(
                url="https://www.hi-heute.de/supermarkte",
                name="hi-heute.de",
                text="Supermarkt Nachrichten Aldi Rewe",
            )
        )

    def test_loose_accepts_more_than_strict_core(self):
        """Luźny Serper: Filialbau bez słowa GU; strict core wymaga generalunternehmer."""
        from retail_store_builder_filter import (
            mentions_retail_store_build_activity_core,
            mentions_retail_store_build_activity_serper_discovery,
        )

        text = "Partner Filialbau GmbH Einzelhandel Neubau regional"
        self.assertTrue(mentions_retail_store_build_activity_serper_discovery(text))
        self.assertFalse(mentions_retail_store_build_activity_core(text))


class SerperOnlyFilterRegression(unittest.TestCase):
    def test_rejects_ladenbau_without_gu_in_snippet(self):
        self.assertFalse(
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
                text="Generalunternehmer Filialbau Gewerbe Referenz Rewe",
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
        text = "Generalunternehmer Stuttgart Gewerbebau Handwerk Referenz Aldi"
        self.assertTrue(
            is_serper_only_pending_candidate(name=name, text=text, url=url)
        )
        self.assertFalse(
            is_loose_serper_discovery_candidate(name=name, text=text, url=url)
        )

    def test_serper_only_accepts_gu_in_company_name(self):
        self.assertTrue(
            is_serper_only_pending_candidate(
                name="BAUTAL GU GmbH, Wuppertal",
                url="https://bautal-gu.de",
                text="Bauunternehmen Wuppertal Referenz Edeka Filialbau",
            )
        )

    def test_serper_only_rejects_gu_without_named_chain(self):
        self.assertFalse(
            is_serper_only_pending_candidate(
                name="Weber Generalunternehmer GmbH",
                url="https://weber-gu.de",
                text="Generalunternehmer Filialbau Gewerbebau",
            )
        )

    def test_serper_only_accepts_chain_from_search_term_not_snippet(self):
        """Snippet bez nazwy sieci — fraza Serper zawiera Lidl."""
        self.assertTrue(
            is_serper_only_pending_candidate(
                name="Müller GU GmbH",
                url="https://mueller-gu-koeln.de",
                text="Generalunternehmer Filialbau Köln Referenzprojekte",
                search_term="Generalunternehmer Köln Filialumbau Lidl",
            )
        )

    def test_serper_only_accepts_filialbau_in_search_term_without_chain(self):
        """Faza 1: fraza z Filialbau wystarczy — snippet bez marki sieci."""
        self.assertTrue(
            is_serper_only_pending_candidate(
                name="Stuttgart Bau GmbH",
                url="https://stuttgart-bau.de",
                text="Gewerbebau und Hallenbau Referenzprojekte",
                search_term="Generalunternehmer Filialbau Stuttgart",
            )
        )

    def test_serper_only_accepts_trade_signal_without_gu_marker(self):
        """Faza 1: markery branżowe w snippetcie bez słowa generalunternehmer."""
        self.assertTrue(
            is_serper_only_pending_candidate(
                name="Partner Marktbau GmbH",
                url="https://partner-marktbau.de",
                text="Einzelhandelsbau und Supermarktprojekte in Bayern",
                search_term="Generalunternehmer Marktbau München",
            )
        )

    def test_serper_only_accepts_extended_chain_kaufland(self):
        self.assertTrue(
            is_serper_only_pending_candidate(
                name="Nord Bau GmbH",
                url="https://nord-bau.de",
                text="Generalunternehmer Filialbau Referenz Kaufland Neubau",
            )
        )

    def test_pending_not_purged_from_cache(self):
        from retail_store_builder_filter import is_cache_contact_not_store_builder

        info = {
            "company_name_clean": "ZD BAU GmbH",
            "verification_reason": scraper.PENDING_WWW_VERIFY_REASON,
            "retail_verified": False,
        }
        self.assertFalse(
            is_cache_contact_not_store_builder("https://zd-bau.de", info)
        )

    def test_reverify_all_includes_rejected_cache_contacts(self):
        cache = scraper._empty_cache()
        cache["contacts"] = {
            "https://a.de": {
                "verification_reason": "keine_handelskette",
                "retail_verified": False,
            },
            "https://b.de": {
                "verification_reason": scraper.PENDING_WWW_VERIFY_REASON,
                "retail_verified": False,
            },
        }
        pending_only = scraper.collect_urls_for_www_reverify(cache, reverify_all=False)
        all_urls = scraper.collect_urls_for_www_reverify(cache, reverify_all=True)
        self.assertEqual(pending_only, ["https://b.de"])
        self.assertEqual(set(all_urls), {"https://a.de", "https://b.de"})

    def test_excel_roundtrip_restores_pending(self):
        rec = {
            "Nazwa firmy": "BAUTAL GU GmbH",
            "URL": "https://bautal-gu.de",
            "Strona www": "https://bautal-gu.de",
            "WWW_geprueft": "nein",
            "E-mail": "",
            "Handelsketten": "rewe",
            "GU": "ja",
        }
        row = scraper.row_from_excel_record(rec)
        row["verification_reason"] = scraper.PENDING_WWW_VERIFY_REASON
        row["page_snippet"] = "Generalunternehmer Referenz Rewe Filialbau"
        self.assertEqual(row.get("verification_reason"), scraper.PENDING_WWW_VERIFY_REASON)
        self.assertTrue(scraper.is_row_eligible_for_excel_export(row))

    def test_pick_email_prefers_impressum_over_homepage_junk(self):
        target, score, method = scraper.pick_email_with_impressum_priority(
            all_emails=[
                "d@enschutzhinweisen.akzeptieren",
                "privacy@firma.de",
            ],
            impressum_emails=["info@k-in.de"],
            website="https://koerling-interiors.de",
        )
        self.assertEqual(target, "info@k-in.de")
        self.assertIn(method, ("impressum", "impressum_rules"))
        self.assertGreaterEqual(score, scraper.MIN_EMAIL_SCORE_FOR_SEND)

    def test_collect_impressum_urls_includes_guessed_paths(self):
        urls = scraper.collect_impressum_urls(
            "https://www.beispiel-bau.de/leistungen/",
            ["https://www.beispiel-bau.de/kontakt/"],
        )
        self.assertTrue(any("/impressum" in u for u in urls))
        self.assertNotIn("https://www.beispiel-bau.de/kontakt/", urls)

    def test_website_inbox_email_on_short_domain(self):
        from email_targeting import (
            MIN_EMAIL_SCORE_FOR_SEND,
            pick_best_email_for_inquiry,
            pick_best_email_from_website_scrape,
        )

        strict, strict_score = pick_best_email_for_inquiry(
            ["info@k-in.de"], "https://koerling-interiors.de"
        )
        self.assertEqual(strict, "")
        self.assertEqual(strict_score, 6)
        relaxed, relaxed_score = pick_best_email_from_website_scrape(
            ["info@k-in.de"], "https://koerling-interiors.de"
        )
        self.assertEqual(relaxed, "info@k-in.de")
        self.assertGreaterEqual(relaxed_score, MIN_EMAIL_SCORE_FOR_SEND)

    def test_sync_pipeline_rows_populates_email_jobs(self):
        cache = scraper._empty_cache()
        rows = [
            {
                "nazwa": "Körling Interiors GmbH",
                "url": "https://koerling-interiors.de",
                "www": "https://koerling-interiors.de",
                "email_target": "info@k-in.de",
                "retail_verified": True,
                "is_gu": True,
                "is_small_firm": True,
                "retail_chains_found": "rewe",
                "verification_reason": "ok",
                "page_snippet": "Generalunternehmer Ladenbau Referenz Rewe",
            }
        ]
        scraper.sync_pipeline_rows_to_contacts_cache(rows, cache)
        jobs = scraper.build_email_jobs_from_cache_json(
            logging.getLogger("test"), cache=cache
        )
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["email_target"], "info@k-in.de")

    def test_excel_info_sheet_documents_append_mode(self):
        rows = scraper.build_excel_info_sheet_rows()
        self.assertGreaterEqual(len(rows), 3)
        text = " ".join(
            str(v)
            for row in rows
            for v in row.values()
        ).lower()
        self.assertIn("append", text)
        self.assertIn("przebudow", text)

    def test_merge_pipeline_preserves_existing_when_cache_empty(self):
        existing = [
            {
                "nazwa": "BAUTAL GU GmbH",
                "url": "https://bautal-gu.de",
                "verification_reason": scraper.PENDING_WWW_VERIFY_REASON,
            }
        ]
        merged = scraper.merge_pipeline_rows(existing, [])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["nazwa"], "BAUTAL GU GmbH")

    def test_pending_row_eligible_for_excel_when_gu_in_snippet(self):
        row = {
            "nazwa": "Weber Generalunternehmer GmbH",
            "url": "https://weber-gu.de",
            "www": "https://weber-gu.de",
            "retail_verified": False,
            "verification_reason": scraper.PENDING_WWW_VERIFY_REASON,
            "page_snippet": "Generalunternehmer Filialbau Gewerbebau Referenz Aldi Neubau",
            "email_target": "",
        }
        self.assertTrue(scraper.is_row_eligible_for_excel_export(row))

    def test_pending_row_rejected_without_gu(self):
        row = {
            "nazwa": "HELIA Ladenbau GmbH",
            "url": "https://helia-ladenbau.de",
            "www": "https://helia-ladenbau.de",
            "retail_verified": False,
            "verification_reason": scraper.PENDING_WWW_VERIFY_REASON,
            "email_target": "",
        }
        self.assertFalse(scraper.is_row_eligible_for_excel_export(row))

    def test_discovered_row_rejected_after_verify_without_chain(self):
        row = {
            "nazwa": "BAUTAL GU GmbH",
            "url": "https://bautal-gu.de",
            "bundesland": "Nordrhein-Westfalen",
            "discovery_bundesland": "Nordrhein-Westfalen",
            "retail_verified": False,
            "verification_reason": "kein_generalunternehmer",
            "email_target": "",
        }
        self.assertFalse(scraper.is_row_eligible_for_excel_export(row))

    def test_verified_row_rejected_when_not_small(self):
        row = {
            "nazwa": "Müller GU GmbH",
            "url": "https://mueller-gu.de",
            "retail_verified": True,
            "is_gu": True,
            "is_small_firm": False,
            "retail_chains_found": "rewe",
            "page_snippet": "Generalunternehmer Referenz Rewe",
            "email_target": "",
        }
        self.assertFalse(scraper.is_row_eligible_for_excel_export(row))


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

    def test_whitelist_regional_gu_with_moderate_employee_count(self):
        """Faza 4: 280 Mitarbeiter + regionalny GU — nie odrzucaj jako koncern."""
        page = (
            "Generalunternehmer Filialbau regional tätig in Bayern. "
            "280 Mitarbeiter. Referenzprojekte Rewe Aldi."
        )
        large, reason = scraper.is_likely_large_company(
            "Weber GU GmbH",
            "https://weber-gu-bayern.de",
            page,
            serper_blob="weltweit tätig konzern international tätig",
        )
        self.assertFalse(large, reason)

    def test_whitelist_does_not_apply_above_employee_threshold(self):
        large, _ = scraper.is_likely_large_company(
            "Regional GU GmbH",
            "https://regional-gu.de",
            "Generalunternehmer Filialbau regional. 650 Mitarbeiter.",
        )
        self.assertFalse(large)  # bez markerów koncernu — tylko liczba > 499

    def test_whitelist_blocked_by_strong_konzern_signal(self):
        """Silny sygnał koncernu (börsennotiert) blokuje whitelist mimo regionalnego GU."""
        large, reason = scraper.is_likely_large_company(
            "Bau GmbH",
            "https://bau-gmbh.de",
            "Generalunternehmer Filialbau regional. 200 Mitarbeiter. Börsennotiert Konzern.",
        )
        self.assertTrue(large)
        self.assertIn("grosses_unternehmen", reason)

    def test_whitelist_does_not_override_known_konzern_domain(self):
        large, _ = scraper.is_likely_large_company(
            "Regional Bau",
            "https://www.hochtief.de",
            "Generalunternehmer Filialbau regional 150 Mitarbeiter",
        )
        self.assertTrue(large)

    def test_max_employee_count_parser(self):
        self.assertEqual(
            scraper._max_employee_count_in_blob("ca. 280 mitarbeiter in deutschland"),
            280,
        )
        self.assertEqual(
            scraper._max_employee_count_in_blob("Belegschaft von 120 Mitarbeiterinnen"),
            120,
        )


class CompanyNameLegalFormRegression(unittest.TestCase):
    """Faza 6: e.K. / GbR jako prawidłowa forma prawna w nazwie do Excela."""

    def test_accepts_ek_legal_form(self):
        for name in (
            "Müller Filialbau e.K.",
            "Müller Filialbau e. K.",
            "Bau Meier eK",
            "Hans Bau E.K",
        ):
            with self.subTest(name=name):
                self.assertTrue(scraper._company_name_has_legal_form(name))

    def test_accepts_gbr_legal_form(self):
        for name in ("Weber Bau GbR", "Schmidt & Partner GbR", "Partner GbR."):
            with self.subTest(name=name):
                self.assertTrue(scraper._company_name_has_legal_form(name))

    def test_rejects_ekfm_as_legal_form(self):
        self.assertFalse(scraper._company_name_has_legal_form("Schmidt e.Kfm."))
        self.assertFalse(scraper._company_name_has_legal_form("e.Kfm. Schmidt Bau"))

    def test_ek_gbr_not_rejected_for_export(self):
        self.assertFalse(
            scraper.is_rejected_company_name_for_export(
                "Müller Filialbau e.K.",
                "https://mueller-filialbau.de",
                "info@mueller-filialbau.de",
            )
        )
        self.assertFalse(
            scraper.is_rejected_company_name_for_export(
                "Schmidt & Partner GbR",
                "https://schmidt-bau.de",
                "kontakt@schmidt-bau.de",
            )
        )

    def test_finalize_prefers_ek_name(self):
        name = scraper.finalize_company_name_for_export(
            "Müller Filialbau e.K.",
            fallback_raw="Müller Filialbau",
            website="https://mueller-filialbau.de",
            email="info@mueller-filialbau.de",
        )
        self.assertEqual(name, "Müller Filialbau e.K.")


class SmallLadenbauVerifyRegression(unittest.TestCase):
    def test_is_small_ladenbau_specialist_requires_gu(self):
        self.assertTrue(
            scraper._is_small_ladenbau_specialist(
                "Müller Generalunternehmer GmbH",
                "https://mueller-ladenbau.de",
                "Generalunternehmer für Ladenbau — Neubau und Umbau von Gewerbeobjekten.",
            )
        )
        self.assertFalse(
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

    @patch.object(scraper, "ENABLE_CLAUDE_PAGE_VERIFY", False)
    @patch.object(scraper, "gather_website_text_for_verification")
    def test_verify_small_ladenbau_path_requires_gu(self, mock_gather):
        mock_gather.return_value = (
            "Generalunternehmer für Ladenbau. Referenzen: Neubau Rewe Filiale. "
            "img alt='Rewe Filiale' src='/uploads/rewe-filiale.jpg'",
            ["https://helia-ladenbau.de"],
        )
        result = scraper.verify_company_on_website(
            "HELIA Generalunternehmer GmbH",
            "https://helia-ladenbau.de",
            _LOGGER,
            {},
        )
        self.assertTrue(result["verified"])
        self.assertIn("rewe", result.get("retail_chains") or [])
        self.assertTrue(result["is_small_firm"])
        self.assertTrue(result["is_gu"])

    @patch.object(scraper, "ENABLE_CLAUDE_PAGE_VERIFY", False)
    @patch.object(scraper, "gather_website_text_for_verification")
    def test_verify_accepts_filialbau_with_chain_without_gu_word(self, mock_gather):
        mock_gather.return_value = (
            "Wir realisieren Filialbau und Ladenbau für den Einzelhandel. "
            "Referenzen: Neubau Rewe Filiale in Bayern. Portfolio Supermarktprojekte.",
            ["https://markus-bau.de/referenzen"],
        )
        result = scraper.verify_company_on_website(
            "Markus-Bau GmbH",
            "https://markus-bau.de",
            _LOGGER,
            {},
        )
        self.assertTrue(result["is_gu"])
        self.assertIn("rewe", result.get("retail_chains") or [])

    @patch.object(scraper, "ENABLE_CLAUDE_PAGE_VERIFY", False)
    @patch.object(scraper, "gather_website_text_for_verification")
    def test_verify_rejects_ladenbau_without_gu(self, mock_gather):
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
        self.assertFalse(result["verified"])
        self.assertIn(
            result["verification_reason"],
            (
                "kein_generalunternehmer",
                "kein_gu_filialbau_kontext",
                "keine_handelskette",
                "kein_markt_nachweis",
                "nicht_klein",
                "kein_kleinunternehmen",
            ),
        )

    @patch.object(scraper, "ENABLE_CLAUDE_PAGE_VERIFY", False)
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


class RetailChainSerperRotationRegression(unittest.TestCase):
    def test_discovery_terms_include_rotating_chains(self):
        terms = build_discovery_terms(["Nordrhein-Westfalen"], max_terms=21)
        chains_low = [c.lower() for c in RETAIL_CHAINS_ROTATION]
        for term in terms:
            self.assertTrue(
                any(c in term.lower() for c in chains_low),
                msg=f"brak sieci w frazie: {term}",
            )
        found = {
            c
            for c in RETAIL_CHAINS_ROTATION
            if any(c.lower() in t.lower() for t in terms)
        }
        self.assertGreaterEqual(len(found), 3)

    def test_discovery_terms_cycle_all_whitelist_chains(self):
        terms = build_discovery_terms(["Bayern"], max_terms=len(RETAIL_CHAINS_ROTATION) * 2)
        found = [
            c
            for c in RETAIL_CHAINS_ROTATION
            if any(c.lower() in t.lower() for t in terms)
        ]
        self.assertEqual(len(found), len(RETAIL_CHAINS_ROTATION))


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


class EnrichRowSerperSkipRegression(unittest.TestCase):
    @patch.object(scraper, "REQUIRE_WEBSITE_RETAIL_VERIFICATION", False)
    @patch.object(scraper, "search_official_website_with_serper")
    @patch.object(scraper, "collect_contacts_from_website")
    def test_reverify_skips_serper_when_url_in_row(self, mock_collect, mock_serper):
        mock_collect.return_value = {
            "emails": ["info@firma.de"],
            "impressum_emails": ["info@firma.de"],
            "phones": [],
            "website": "https://firma.de",
            "source_urls": ["https://firma.de"],
            "page_snippet": "",
        }
        row = {
            "url": "https://firma.de",
            "www": "https://firma.de",
            "nazwa": "Firma Bau GmbH",
        }
        cache = {"contacts": {}}
        scraper.enrich_row_with_contacts(
            row, cache, _LOGGER, force_refresh=True
        )
        mock_serper.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
