# -*- coding: utf-8 -*-
import unittest

import ua_materialy_scraper as scraper


class UaCompanyNameFromDomainTest(unittest.TestCase):
    def test_product_title_yields_domain_brand(self):
        name = scraper.finalize_company_name_for_export(
            "",
            fallback_raw="Фольгований утеплювач",
            website="https://wikibud.com.ua",
            email="wikibud7@gmail.com",
        )
        self.assertEqual(name, "Wikibud")

    def test_ui_garbage_yields_domain_brand(self):
        name = scraper.finalize_company_name_for_export(
            "",
            fallback_raw="Advanced Search",
            website="https://kt-stal.com.ua",
            email="",
        )
        self.assertEqual(name, "Kt Stal")

    def test_raw_domain_string_yields_brand(self):
        name = scraper.finalize_company_name_for_export(
            "",
            fallback_raw="kelma.org.ua",
            website="https://kelma.org.ua",
            email="",
        )
        self.assertEqual(name, "Kelma")

    def test_legal_form_input_ignored_domain_wins(self):
        name = scraper.finalize_company_name_for_export(
            'ТОВ "Венбуд"',
            fallback_raw="Ґрунтовка Крайзель",
            website="https://venbud.ua",
            email="info@venbud.ua",
        )
        self.assertEqual(name, "Venbud")

    def test_excel_column_always_from_domain(self):
        row = {
            "nazwa": "Фольгований утеплювач",
            "company_name_clean": "Фольгований утеплювач",
            "www": "https://wikibud.com.ua",
            "url": "https://wikibud.com.ua",
        }
        cols = scraper.row_to_excel_kontakte_columns(row)
        self.assertEqual(cols["Nazwa firmy"], "Wikibud")

    def test_normalize_row_uses_domain_only(self):
        row = scraper.normalize_row_company_name(
            {
                "nazwa": "budMATERIAL: Купити",
                "www": "https://budmaterial.kyiv.ua",
            }
        )
        self.assertEqual(row["nazwa"], "Budmaterial")
        self.assertEqual(row["company_name_clean"], "Budmaterial")
        self.assertEqual(row["company_name_raw"], "budMATERIAL: Купити")


if __name__ == "__main__":
    unittest.main()
