# -*- coding: utf-8 -*-
"""Testy warstwy Claude (bez live API)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
LIBS = ROOT / "libs"
for p in (str(ROOT), str(LIBS)):
    if p not in sys.path:
        sys.path.insert(0, p)

from claude_row_cleanup import parse_claude_row_cleanup_response


class ClaudeRowCleanupTest(unittest.TestCase):
    def test_parse_cleanup_json(self):
        raw = (
            '{"company_name_clean":"Müller Bau GmbH","address":"Hauptstr. 1, 04109 Leipzig",'
            '"phone":"+49 341 123456","website":"https://mueller-bau.de","bundesland":"Sachsen"}'
        )
        parsed = parse_claude_row_cleanup_response(raw)
        self.assertEqual(parsed["company_name_clean"], "Müller Bau GmbH")
        self.assertEqual(parsed["bundesland"], "Sachsen")


class ClaudePageVerifyIntegrationTest(unittest.TestCase):
    def test_claude_verify_accepts_gu_retail(self):
        from claude_page_verify import claude_verify_company_page

        response_json = (
            '{"is_gu": true, "has_retail_context": true, '
            '"primary_role": "Generalunternehmer", '
            '"matched_gu_keywords": ["generalunternehmer"], '
            '"matched_retail_keywords": ["filialbau"], '
            '"matched_chains": ["rewe"], '
            '"matched_negative_keywords": [], '
            '"is_small_firm": true, '
            '"reason": "GU mit Filialbau"}'
        )
        with patch("claude_page_verify.get_anthropic_api_key", return_value="test-key"):
            with patch(
                "claude_page_verify.claude_generate_text",
                return_value=(response_json, "claude-sonnet-test"),
            ):
                result = claude_verify_company_page(
                    "Test Bau GmbH",
                    "https://test-bau.de",
                    "Wir sind Generalunternehmer für Filialbau und Rewe Projekte. "
                    "Familienunternehmen mit 40 Mitarbeitern.",
                    logger=MagicMock(),
                    cache={},
                )
        self.assertIsNotNone(result)
        self.assertTrue(result["verified"])
        self.assertTrue(result["is_small_firm"])
        self.assertIn("rewe", result["retail_chains"])

    def test_claude_verify_rejects_konzern_not_small(self):
        from claude_page_verify import claude_verify_company_page

        response_json = (
            '{"is_gu": true, "has_retail_context": true, '
            '"primary_role": "Generalunternehmer", '
            '"matched_gu_keywords": ["generalunternehmer"], '
            '"matched_retail_keywords": ["filialbau"], '
            '"matched_chains": ["rewe"], '
            '"matched_negative_keywords": [], '
            '"is_small_firm": false, '
            '"reason": "Weltkonzern"}'
        )
        with patch("claude_page_verify.get_anthropic_api_key", return_value="test-key"):
            with patch(
                "claude_page_verify.claude_generate_text",
                return_value=(response_json, "claude-sonnet-test"),
            ):
                result = claude_verify_company_page(
                    "STRABAG SE",
                    "https://www.strabag.com",
                    "STRABAG SE weltweit tätig. Rewe Filialbau Referenz.",
                    logger=MagicMock(),
                    cache={},
                )
        self.assertIsNotNone(result)
        self.assertFalse(result["verified"])
        self.assertFalse(result["is_small_firm"])
        self.assertIn("kleinunternehmen", result["verification_reason"])

    def test_claude_reserve_blocks_api_at_buffer_when_limited(self):
        import claude_client as cc

        cc.configure_claude_limits(daily_limit=3000, reserve=1000, unlimited=False)
        used = cc.CLAUDE_DAILY_LIMIT - cc.CLAUDE_DISCOVERY_RESERVE
        cache = {"claude_daily": {"2099-01-01": used}}
        with patch("claude_client._campaign_today", return_value="2099-01-01"):
            self.assertTrue(cc.is_claude_limit_reached_today(cache))
            with patch("claude_client.get_anthropic_api_key", return_value="test-key"):
                with self.assertRaises(RuntimeError):
                    cc.claude_generate_text("ping", MagicMock(), cache=cache)

    def test_claude_unlimited_skips_daily_cap(self):
        import claude_client as cc

        cc.configure_claude_limits(daily_limit=3000, reserve=1000, unlimited=True)
        cache = {"claude_daily": {"2099-01-01": cc.CLAUDE_DAILY_LIMIT}}
        with patch("claude_client._campaign_today", return_value="2099-01-01"):
            self.assertFalse(cc.is_claude_limit_reached_today(cache))
            with patch("claude_client.get_anthropic_api_key", return_value="test-key"):
                with patch("claude_client.requests.post") as mock_post:
                    mock_post.return_value.status_code = 200
                    mock_post.return_value.json.return_value = {
                        "content": [{"type": "text", "text": '{"company_name_clean":"OK GmbH"}'}]
                    }
                    text, _ = cc.claude_generate_text("cleanup", MagicMock(), cache=cache)
        self.assertIn("OK GmbH", text)
        self.assertEqual(cache["claude_daily"]["2099-01-01"], cc.CLAUDE_DAILY_LIMIT)

    def test_wide_email_regex_50_chars_local(self):
        import de_gu_bauunternehmen_scraper as scraper

        local = "a" * 50
        email = f"{local}@example.de"
        found = scraper._find_emails_in_text_regex(f"Kontakt: {email}")
        self.assertIn(email.lower(), found)
        too_long = f"{'b' * 51}@example.de"
        found_long = scraper._find_emails_in_text_regex(f"Kontakt: {too_long}")
        self.assertNotIn(too_long.lower(), found_long)

    def test_row_cleanup_claude_then_regex(self):
        import de_gu_bauunternehmen_scraper as scraper

        row = {
            "url": "https://beispiel-bau.de",
            "nazwa": "Beispiel Bau",
            "page_snippet": "Impressum info@beispiel-bau.de Tel +49 341 1234567",
            "email_target": "",
            "telefon": "",
        }
        with patch(
            "claude_row_cleanup.claude_cleanup_row_fields",
            return_value={
                "company_name_clean": "Beispiel Bau GmbH",
                "address": "Hauptstr. 1, 04109 Leipzig",
                "phone": "",
                "website": "https://beispiel-bau.de",
                "bundesland": "Sachsen",
                "handelsketten": "rewe, aldi",
                "url": "https://beispiel-bau.de",
            },
        ):
            with patch.object(scraper, "get_anthropic_api_key", return_value="key"):
                out = scraper.enrich_row_with_claude_cleanup(
                    dict(row), MagicMock(), {}
                )
        self.assertEqual(out["company_name_clean"], "Beispiel Bau GmbH")
        self.assertEqual(out["email_target"], "info@beispiel-bau.de")
        self.assertIn("+49", out["telefon"])
        self.assertEqual(out["retail_chains_found"], "rewe, aldi")
        excel = scraper.row_to_excel_kontakte_columns(out)
        self.assertEqual(excel["Nazwa firmy"], "Beispiel Bau GmbH")
        self.assertEqual(excel["Handelsketten"], "rewe, aldi")


if __name__ == "__main__":
    unittest.main()
