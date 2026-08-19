# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.excel_from_json_validate import (
    fill_export_from_json,
    find_excel_gaps,
    json_contact_has_needed_data,
    merge_contacts_maps,
    verify_and_fill_until_complete,
)


class JsonNeededDataTests(unittest.TestCase):
    def test_passes_email(self):
        self.assertTrue(
            json_contact_has_needed_data(
                "https://firma.ua",
                {"email_target": "a@firma.ua", "company_name_clean": ""},
            )
        )

    def test_passes_name(self):
        self.assertTrue(
            json_contact_has_needed_data(
                "https://budmat.ua", {"company_name_clean": "Будматеріали X"}
            )
        )

    def test_passes_phone_from_emails_found_fallback(self):
        self.assertTrue(
            json_contact_has_needed_data(
                "https://sklad.ua",
                {"emails_found": "biuro@sklad.ua, info@sklad.ua"},
            )
        )

    def test_rejects_empty(self):
        self.assertFalse(json_contact_has_needed_data("https://x.ua", {}))
        self.assertFalse(json_contact_has_needed_data("", {"company_name_clean": "X"}))


class MergeAndFillLoopTests(unittest.TestCase):
    def test_merge_prefers_richer_email(self):
        a = {"https://a.ua": {"company_name_clean": "A"}}
        b = {"https://a.ua": {"company_name_clean": "A", "email_target": "a@a.ua"}}
        merged = merge_contacts_maps(a, b)
        self.assertEqual(merged["https://a.ua"]["email_target"], "a@a.ua")

    def test_fill_missing_row_and_empty_email(self):
        contacts = {
            "https://a.ua": {
                "company_name_clean": "Alpha",
                "email_target": "a@a.ua",
                "phones_found": "38050100200",
                "bundesland": "Kyiv",
            },
            "https://b.ua": {
                "company_name_clean": "Beta",
                "email_target": "b@b.ua",
            },
        }
        excel = [
            {
                "URL": "https://a.ua",
                "Nazwa firmy": "Alpha",
                "E-mail": "",
                "Telefon": "",
                "Adres": "",
                "Obwód": "",
                "Strona www": "",
            }
        ]
        gaps = find_excel_gaps(contacts, excel)
        reasons = {g["url"]: g["reason"] for g in gaps}
        self.assertEqual(reasons["https://a.ua"], "empty_columns")
        self.assertEqual(reasons["https://b.ua"], "missing_row")
        filled, n = fill_export_from_json(contacts, excel)
        self.assertGreater(n, 0)
        done, gaps2, rounds = verify_and_fill_until_complete(contacts, filled)
        self.assertEqual(gaps2, [])
        self.assertGreaterEqual(rounds, 0)
        by_url = {r["URL"]: r for r in done}
        self.assertEqual(by_url["https://a.ua"]["E-mail"], "a@a.ua")
        self.assertEqual(by_url["https://a.ua"]["Telefon"], "38050100200")
        self.assertEqual(by_url["https://a.ua"]["Obwód"], "Kyiv")
        self.assertEqual(by_url["https://b.ua"]["E-mail"], "b@b.ua")

    def test_loop_fills_until_excel_complete(self):
        contacts = {
            "https://c.ua": {
                "company_name_clean": "Cement UA",
                "email_target": "c@c.ua",
                "full_address": "Kyiv, Khreschatyk 1",
                "discovery_bundesland": "Kyiv",
            }
        }
        excel: list[dict] = []
        done, gaps, rounds = verify_and_fill_until_complete(contacts, excel)
        self.assertEqual(gaps, [])
        self.assertGreaterEqual(rounds, 1)
        self.assertEqual(done[0]["Nazwa firmy"], "Cement UA")
        self.assertEqual(done[0]["Adres"], "Kyiv, Khreschatyk 1")
        self.assertEqual(done[0]["Obwód"], "Kyiv")

    def test_numeric_phone_from_excel_is_not_a_gap(self):
        contacts = {
            "https://a.ua": {
                "company_name_clean": "Alpha",
                "email_target": "a@a.ua",
                "phones_found": "38050100200",
            }
        }
        excel = [
            {
                "URL": "https://a.ua",
                "Nazwa firmy": "Alpha",
                "E-mail": "a@a.ua",
                "Telefon": 38050100200,
                "Strona www": "https://a.ua",
            }
        ]
        self.assertEqual(find_excel_gaps(contacts, excel), [])


if __name__ == "__main__":
    unittest.main()
