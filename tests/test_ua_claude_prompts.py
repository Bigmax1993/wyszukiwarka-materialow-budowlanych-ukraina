# -*- coding: utf-8 -*-
import unittest

from ua_claude_prompts import build_row_cleanup_prompt


class UaRowCleanupPromptTest(unittest.TestCase):
    def test_killer_prompt_structure(self):
        p = build_row_cleanup_prompt(
            company='ТОВ "Венбуд"',
            address="вул. Бориспільська, 1, м. Київ",
            phone="+380501234567",
            email="info@venbud.ua",
            website="https://venbud.ua",
            states="Київ, Львів",
            handelsketten="цемент, пісок",
            url="https://venbud.ua",
        )
        self.assertIn("company_name_clean", p)
        self.assertIn("ЗАВЖДИ", p)
        self.assertIn("wikibud.com.ua", p)
        self.assertIn("вул.", p)
        self.assertIn("Київ, Львів", p)

    def test_company_name_always_empty_in_llm_output(self):
        p = build_row_cleanup_prompt(
            company="kelma.org.ua",
            address="Композитна арматура 4 мм",
            phone="",
            email="",
            website="https://kelma.org.ua",
            states="Київ",
        )
        self.assertIn('company_name_clean=""', p)
        self.assertIn("Nazwa firmy", p)


if __name__ == "__main__":
    unittest.main()
