# -*- coding: utf-8 -*-
"""
Testy integracyjne pipeline kontaktów UA:
regex → scoring UA → Claude (PL) → merge → pick → Excel/backfill.

  python -m pytest tests/test_ua_contact_pipeline_integration.py -v
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

import ua_materialy_scraper as scraper
from claude_contact_extract import merge_claude_contacts_into_collected
from email_targeting import MIN_EMAIL_SCORE_FOR_SEND
from ua_claude_contact_extract import build_contact_extract_page_bundle

_LOGGER = logging.getLogger("test_ua_contact_pipeline_integration")

# Przypadki z piątkowego discovery (GHA 2026-07-09)
DISCOVERY_GMAIL_CASES = [
    ("https://venbud.ua", "Venbud", ["venbud.dealer@gmail.com"]),
    ("https://ektabud.in.ua", "Ektabud", ["tovektabud@gmail.com"]),
    ("https://wikibud.com.ua", "Wikibud", ["wikibud7@gmail.com", "d2535090@gmail.com"]),
    ("https://bud-platforma.com.ua", "Bud Platforma", ["bud-platforma@ukr.net"]),
]

OWN_DOMAIN_CASES = [
    ("https://dimaks.com.ua", ["mag@dimaks.com.ua"]),
    ("https://budmaterial.kyiv.ua", ["info@budmaterial.kyiv.ua", "info@budmaterial.ua"]),
    ("https://konstruktyv.ua", ["info@konstruktyv.ua"]),
]


class TestEmailPickPipelineIntegration:
    @pytest.mark.parametrize("website,company,candidates", DISCOVERY_GMAIL_CASES)
    def test_pick_email_with_impressum_accepts_gmail_from_discovery(
        self, website: str, company: str, candidates: list[str]
    ):
        target, score, method = scraper.pick_email_with_impressum_priority(
            candidates, [], website
        )
        assert target in candidates, f"{company}: brak wyboru dla {candidates}"
        assert score >= MIN_EMAIL_SCORE_FOR_SEND
        assert method in ("rules", "website_inbox", "impressum", "impressum_rules")

    @pytest.mark.parametrize("website,candidates", OWN_DOMAIN_CASES)
    def test_pick_email_prefers_own_domain(self, website: str, candidates: list[str]):
        target, score, _ = scraper.pick_email_with_impressum_priority(
            candidates, [], website
        )
        assert target
        assert score >= MIN_EMAIL_SCORE_FOR_SEND
        host = scraper.get_registrable_domain(website)
        assert host.split(".")[0] in target or target.split("@")[1].startswith(
            host.split(".")[0]
        ) or "@" in target


class TestBackfillIntegration:
    def test_backfill_fills_gmail_rejected_by_old_scoring(self):
        cache = scraper._empty_cache()
        cache["contacts"] = {
            "https://venbud.ua": {
                "company_name_clean": "Venbud",
                "official_website": "https://venbud.ua",
                "emails_found": "venbud.dealer@gmail.com",
                "email_target": "",
                "email_status": "no_suitable_email",
            }
        }
        stats = scraper.backfill_emails_in_cache(cache, _LOGGER)
        info = cache["contacts"]["https://venbud.ua"]
        assert stats["filled"] == 1
        assert info["email_target"] == "venbud.dealer@gmail.com"
        assert info["email_target_score"] >= MIN_EMAIL_SCORE_FOR_SEND


class TestClaudeContactPipelineIntegration:
    @patch("ua_claude_contact_extract.claude_generate_text")
    @patch("ua_claude_contact_extract.get_anthropic_api_key", return_value="test-key")
    def test_claude_confirms_regex_then_pick_succeeds(self, _key, mock_gen):
        from ua_claude_contact_extract import claude_extract_contacts_from_pages_ua

        mock_gen.return_value = (
            '{"emails":["venbud.dealer@gmail.com"],"phones":[],"impressum_emails":[],'
            '"company_name":"Venbud","reason":"Wybrano z listy REGEX"}',
            "claude-sonnet-4-6",
        )
        cache: dict = {"claude_contact_extract": {}}
        collected = {
            "emails": ["venbud.dealer@gmail.com"],
            "impressum_emails": [],
            "phones": ["068 080 48 00"],
            "website": "https://venbud.ua",
            "page_snippet": "Hurtownia budowlana",
            "source_urls": ["https://venbud.ua"],
        }
        target_before, _, _ = scraper.pick_email_with_impressum_priority(
            collected["emails"], [], "https://venbud.ua"
        )
        assert target_before == "venbud.dealer@gmail.com"

        bundle = build_contact_extract_page_bundle(
            crawl_text="(WAF — mało tekstu)",
            page_snippet=collected["page_snippet"],
            regex_phones=collected["phones"],
        )
        parsed = claude_extract_contacts_from_pages_ua(
            "Venbud",
            "https://venbud.ua",
            bundle,
            _LOGGER,
            cache,
            cache_key="https://venbud.ua",
            regex_candidates=collected["emails"],
            regex_phones=collected["phones"],
        )
        assert parsed is not None
        merged = merge_claude_contacts_into_collected(collected, parsed)
        target, score, method = scraper.resolve_inquiry_email_target(
            merged,
            "https://venbud.ua",
            "Venbud",
            _LOGGER,
            cache,
            retail_verified=True,
        )
        assert target == "venbud.dealer@gmail.com"
        assert score >= MIN_EMAIL_SCORE_FOR_SEND

    @patch("ua_claude_contact_extract.claude_generate_text")
    @patch("ua_claude_contact_extract.get_anthropic_api_key", return_value="test-key")
    def test_claude_finds_new_email_when_regex_empty(self, _key, mock_gen):
        from ua_claude_contact_extract import claude_extract_contacts_from_pages_ua

        mock_gen.return_value = (
            '{"emails":["kontakt@kub.in.ua"],"phones":["068 080 48 00"],'
            '"impressum_emails":["kontakt@kub.in.ua"],"company_name":"Kub",'
            '"reason":"Znaleziono w fragmencie kontaktu"}',
            "claude-sonnet-4-6",
        )
        cache: dict = {"claude_contact_extract": {}}
        collected = {
            "emails": [],
            "impressum_emails": [],
            "phones": [],
            "website": "https://kub.in.ua",
            "page_snippet": "",
            "source_urls": [],
        }
        parsed = claude_extract_contacts_from_pages_ua(
            "Kub",
            "https://kub.in.ua",
            "=== https://kub.in.ua/kontakt ===\nkontakt@kub.in.ua tel 068",
            _LOGGER,
            cache,
            cache_key="https://kub.in.ua",
            regex_candidates=[],
        )
        merged = merge_claude_contacts_into_collected(collected, parsed)
        target, score, _ = scraper.resolve_inquiry_email_target(
            merged,
            "https://kub.in.ua",
            "Kub",
            _LOGGER,
            cache,
            retail_verified=True,
        )
        assert target == "kontakt@kub.in.ua"
        assert score >= MIN_EMAIL_SCORE_FOR_SEND


class TestExcelExportIntegration:
    def test_row_to_excel_includes_picked_gmail(self):
        row = {
            "company_name_clean": "Venbud",
            "nazwa": "Venbud",
            "bundesland": "Kyiv",
            "telefon": "068 080 48 00",
            "official_website": "https://venbud.ua",
            "www": "https://venbud.ua",
            "url": "https://venbud.ua",
            "email_target": "venbud.dealer@gmail.com",
            "retail_chains_found": "цемент, пісок",
        }
        cols = scraper.row_to_excel_kontakte_columns(row)
        assert cols["E-mail"] == "venbud.dealer@gmail.com"
        assert cols["Strona www"] == "https://venbud.ua"
        assert cols["Obwód"] == "Kyiv"


class TestUaPromptIntegration:
    def test_contact_extract_prompt_not_german(self):
        from ua_claude_prompts import build_contact_extract_prompt_pl

        prompt = build_contact_extract_prompt_pl(
            "Venbud",
            "https://venbud.ua",
            "tekst",
            regex_candidates=["venbud.dealer@gmail.com"],
        )
        assert "Jesteś analitykiem" in prompt
        assert "Generalunternehmer in Deutschland" not in prompt
        assert "REGEX" in prompt

    def test_scraper_does_not_import_german_contact_prompt(self):
        import ua_claude_contact_extract as mod

        assert "build_contact_extract_prompt_pl" in dir(
            __import__("ua_claude_prompts")
        )
        assert not hasattr(mod, "build_contact_extract_prompt")
