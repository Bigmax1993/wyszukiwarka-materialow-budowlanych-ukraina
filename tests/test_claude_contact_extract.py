# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch

from claude_contact_extract import (
    claude_extract_contacts_from_pages,
    merge_claude_contacts_into_collected,
)
from claude_prompts import build_contact_extract_prompt, prioritize_page_text_for_verify
from contact_extract_utils import parse_contact_extract_response


class TestClaudeContactExtract(unittest.TestCase):
    def test_build_contact_extract_prompt_prioritizes_impressum(self):
        text = "x " * 8000 + "\n=== https://firma.de/impressum ===\ninfo@firma.de"
        p = build_contact_extract_prompt("Firma GmbH", "https://firma.de", text)
        self.assertIn("info@firma.de", p)
        self.assertIn("impressum_emails", p)
        self.assertIn("WÖRTLICH", p)

    def test_prioritize_contact_keywords(self):
        long_tail = "y " * 5000
        text = f"{long_tail}\nImpressum Kontakt info@beispiel.de Tel +49 341 999"
        out = prioritize_page_text_for_verify(
            text,
            max_chars=120,
            priority_keywords=("impressum", "kontakt", "@"),
        )
        self.assertIn("info@beispiel.de", out)

    def test_parse_contact_extract_impressum_emails(self):
        parsed = parse_contact_extract_response(
            '{"company_name":"Muster GmbH","emails":["info@muster.de"],'
            '"impressum_emails":["info@muster.de"],"phones":["+49 341 1"],'
            '"reason":"Impressum"}'
        )
        self.assertEqual(parsed["impressum_emails"], ["info@muster.de"])

    def test_merge_claude_contacts_into_collected(self):
        collected = {
            "emails": [],
            "impressum_emails": [],
            "phones": [],
            "company_name": "",
        }
        parsed = {
            "emails": ["kontakt@bau.de"],
            "impressum_emails": ["kontakt@bau.de"],
            "phones": ["+49 341 123456"],
            "company_name": "Bau GmbH",
            "reason": "Impressum",
        }
        out = merge_claude_contacts_into_collected(collected, parsed)
        self.assertEqual(out["emails"], ["kontakt@bau.de"])
        self.assertEqual(out["impressum_emails"], ["kontakt@bau.de"])
        self.assertEqual(out["phones"], ["+49 341 123456"])
        self.assertEqual(out["company_name"], "Bau GmbH")

    @patch("claude_contact_extract.claude_generate_text")
    @patch("claude_contact_extract.get_anthropic_api_key", return_value="test-key")
    def test_claude_extract_uses_cache(self, _key, mock_gen):
        mock_gen.return_value = (
            '{"emails":["office@test.de"],"phones":[],"impressum_emails":[],'
            '"company_name":"","reason":"ok"}',
            "claude-sonnet-4-6",
        )
        cache: dict = {"claude_contact_extract": {}}
        page = "Kontakt office@test.de"
        first = claude_extract_contacts_from_pages(
            "Test GmbH", "https://test.de", page, None, cache, cache_key="k1"
        )
        second = claude_extract_contacts_from_pages(
            "Test GmbH", "https://test.de", page, None, cache, cache_key="k1"
        )
        self.assertEqual(first["emails"], ["office@test.de"])
        self.assertEqual(second["emails"], ["office@test.de"])
        mock_gen.assert_called_once()


if __name__ == "__main__":
    unittest.main()
