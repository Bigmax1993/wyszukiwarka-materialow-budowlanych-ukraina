# -*- coding: utf-8 -*-
import unittest

from claude_prompts import (
    build_contact_extract_prompt,
    build_custom_email_prompt_de,
    build_custom_email_prompt_pl,
    build_discovery_terms_prompt,
    build_page_verify_prompt,
    build_row_cleanup_prompt,
    prioritize_page_text_for_verify,
)


class TestClaudePrompts(unittest.TestCase):
    def test_page_verify_prompt_structure(self):
        p = build_page_verify_prompt("Test GmbH", "https://test.de", "Filialbau Rewe")
        self.assertIn("ENTSCHEIDUNGSBAUM", p)
        self.assertIn("NICHT immer auf der Website", p)
        self.assertIn("Fotos/Galerie", p)
        self.assertIn("is_small_firm", p)
        self.assertIn("Familienunternehmen", p)
        self.assertIn("is_gu", p)
        self.assertIn("Test GmbH", p)
        self.assertIn("rewe", p.lower())
        self.assertIn("Whitelist", p)
        self.assertIn("Auftraggeber Netto", p)
        self.assertIn("norma", p.lower())
        self.assertNotIn("IM ZWEIFEL: FOR TRUE", p)

    def test_prioritize_page_text_puts_retail_lines_first(self):
        long_tail = "x " * 5000
        text = f"{long_tail}\nAuftraggeber Netto Marken-Discount Retail-Projekte"
        out = prioritize_page_text_for_verify(text, max_chars=200)
        self.assertTrue(out.startswith("Auftraggeber Netto"))

    def test_row_cleanup_prompt_excel_schema(self):
        p = build_row_cleanup_prompt(
            company="Müller Bau GmbH",
            address="Hauptstr. 1",
            phone="+49 341 123",
            email="info@test.de",
            website="https://test.de",
            states="Sachsen, Bayern",
        )
        self.assertIn("company_name_clean", p)
        self.assertIn("handelsketten", p)
        self.assertIn("KILLER-REGELN", p)
        self.assertIn("Sachsen, Bayern", p)

    def test_contact_extract_prompt_schema(self):
        p = build_contact_extract_prompt(
            "Bau GmbH", "https://bau.de", "Impressum info@bau.de"
        )
        self.assertIn("impressum_emails", p)
        self.assertIn("WÖRTLICH", p)
        self.assertIn("info@bau.de", p)

    def test_discovery_terms_prompt_count(self):
        p = build_discovery_terms_prompt(
            ["Sachsen"],
            city_str="Leipzig, Dresden",
            land_str="Sachsen",
            terms_requested=5,
        )
        self.assertIn("Genau 5 Zeilen", p)
        self.assertIn("Generalunternehmer", p)

    def test_email_prompts_json_only(self):
        de = build_custom_email_prompt_de("Hallo", "Firma GmbH")
        pl = build_custom_email_prompt_pl("Cześć", "Firma Sp. z o.o.")
        self.assertIn('"subject"', de)
        self.assertIn('"subject"', pl)


if __name__ == "__main__":
    unittest.main(verbosity=2)
