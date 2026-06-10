# -*- coding: utf-8 -*-
"""Referencje marketów: Referenzen, zdjęcia sklepów, opisy bez zakładki Referenzen."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import de_gu_bauunternehmen_scraper as scraper
from retail_store_builder_filter import (
    detect_required_retail_chains,
    has_market_project_evidence_on_website,
    has_retail_references_or_portfolio,
    has_required_retail_chain_mention,
    portfolio_negates_market_projects,
)


class RetailReferenceEvidence(unittest.TestCase):
    def test_classic_referenzen_tab(self):
        text = (
            "Generalunternehmer für Filialbau. Referenzen: Neubau Rewe "
            "Supermarkt in Hannover."
        )
        self.assertTrue(has_retail_references_or_portfolio(text))

    def test_store_photos_without_referenzen_tab(self):
        text = (
            "Generalunternehmer Filialbau. Fotogalerie. "
            "img alt='Rewe Filiale Neubau' src='/uploads/rewe-filiale-neubau.jpg' "
            "Supermarkt Umbau realisiert."
        )
        self.assertTrue(has_market_project_evidence_on_website(text))

    def test_project_description_only(self):
        text = (
            "Wir sind Generalunternehmer. Wir realisieren Neubau eines "
            "Supermarktes für einen Discounter — Projektbeschreibung mit Details."
        )
        self.assertTrue(has_market_project_evidence_on_website(text))

    def test_gu_without_any_reference_rejected(self):
        text = (
            "Generalunternehmer für Gewerbebau und Hallenbau. "
            "Wir bauen Bürogebäude und Logistikhallen."
        )
        self.assertFalse(has_market_project_evidence_on_website(text))

    def test_page_verify_requires_reference_when_enabled(self):
        text = (
            "Generalunternehmer Filialbau. Neubau Rewe Supermarkt. "
            "Bild /uploads/rewe-marktneubau-hamburg.webp realisiert."
        )
        ok, chains, reason = scraper.page_mentions_retail_store_projects(text)
        self.assertTrue(ok, reason)
        self.assertIn("rewe", chains)

    def test_rejects_gu_without_named_chain(self):
        text = (
            "Generalunternehmer Filialbau. Referenzen: Neubau Supermarkt "
            "img alt='Filiale Neubau' src='/uploads/marktneubau.jpg'"
        )
        ok, _, reason = scraper.page_mentions_retail_store_projects(text)
        self.assertFalse(ok)
        self.assertEqual(reason, "keine_handelskette")

    def test_required_chain_detection(self):
        self.assertTrue(has_required_retail_chain_mention("Referenzprojekt Aldi Nord"))
        self.assertEqual(
            set(detect_required_retail_chains("Penny und Kaufland")),
            {"penny", "kaufland"},
        )
        self.assertFalse(has_required_retail_chain_mention("Discounter Markt Neubau"))

    def test_faza5_filialbau_plus_referenz_without_portfolio_section(self):
        """Faza 5.1: Filialbau + referenz/projekt bez zakładki Portfolio."""
        text = (
            "Generalunternehmer Filialbau. Unsere Referenzen: "
            "Supermarktumbau und Filialmodernisierung im Einzelhandel."
        )
        self.assertTrue(has_retail_references_or_portfolio(text))

    def test_faza5_gallery_without_portfolio_word(self):
        """Faza 5.1: galeria zdjęć bez słowa Portfolio."""
        text = (
            "Generalunternehmer Filialbau. Bildergalerie unserer Arbeiten. "
            "Supermarkt Neubau und Filialumbau."
        )
        self.assertTrue(has_market_project_evidence_on_website(text))

    def test_faza5_mixed_portfolio_with_negation_but_market_signal(self):
        """Faza 5.2: biura + fraza negacji, ale jest sygnał marketu (Rewe)."""
        text = (
            "Generalunternehmer Filialbau. Referenzen Bürobau und Hallenbau. "
            "Keine Supermarktprojekte mehr geplant — abgeschlossenes Rewe Filialumbau 2023."
        )
        self.assertFalse(portfolio_negates_market_projects(text))
        self.assertTrue(has_retail_references_or_portfolio(text))

    def test_faza5_negation_without_any_market_signal(self):
        """Faza 5.2: jawna negacja bez żadnego sygnału marketowego."""
        text = (
            "Generalunternehmer Gewerbebau. Ohne Einzelhandel und ohne Filialen. "
            "Nur Bürobau und Logistikhallen."
        )
        self.assertTrue(portfolio_negates_market_projects(text))
        self.assertFalse(has_market_project_evidence_on_website(text))


class SerperUnlimited(unittest.TestCase):
    def test_unlimited_bypasses_daily_cap(self):
        cache = scraper._empty_cache()
        today = scraper.campaign_today()
        cache["serper_daily"][today] = 9999
        with patch.object(scraper, "SERPER_UNLIMITED", True):
            self.assertFalse(scraper.is_serper_limit_reached_today(cache))
            scraper.ensure_serper_budget_or_fail(cache)
            _, _, remaining = scraper.get_remaining_daily_serper_limit(cache)
            self.assertGreater(remaining, scraper.SERPER_DAILY_LIMIT)


if __name__ == "__main__":
    unittest.main()
