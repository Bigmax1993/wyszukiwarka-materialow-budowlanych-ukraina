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
                "https://firma.pl",
                {"email_target": "a@firma.pl", "company_name_clean": ""},
            )
        )

    def test_passes_name(self):
        self.assertTrue(
            json_contact_has_needed_data(
                "https://hurt.pl", {"company_name_clean": "Hurtownia X"}
            )
        )

    def test_rejects_empty(self):
        self.assertFalse(json_contact_has_needed_data("https://x.pl", {}))
        self.assertFalse(json_contact_has_needed_data("", {"company_name_clean": "X"}))


class MergeAndFillLoopTests(unittest.TestCase):
    def test_merge_prefers_richer_email(self):
        a = {"https://a.pl": {"company_name_clean": "A"}}
        b = {"https://a.pl": {"company_name_clean": "A", "email_target": "a@a.pl"}}
        merged = merge_contacts_maps(a, b)
        self.assertEqual(merged["https://a.pl"]["email_target"], "a@a.pl")

    def test_fill_missing_row_and_empty_email(self):
        contacts = {
            "https://a.pl": {
                "company_name_clean": "Alpha",
                "email_target": "a@a.pl",
                "phones_found": "500100200",
            },
            "https://b.pl": {
                "company_name_clean": "Beta",
                "email_target": "b@b.pl",
            },
        }
        excel = [
            {
                "URL": "https://a.pl",
                "Nazwa firmy": "Alpha",
                "E-mail": "",
                "Telefon": "",
                "Adres": "",
                "Województwo": "",
                "Strona www": "",
            }
        ]
        gaps = find_excel_gaps(contacts, excel)
        reasons = {g["url"]: g["reason"] for g in gaps}
        self.assertEqual(reasons["https://a.pl"], "empty_columns")
        self.assertEqual(reasons["https://b.pl"], "missing_row")
        filled, n = fill_export_from_json(contacts, excel)
        self.assertGreater(n, 0)
        done, gaps2, rounds = verify_and_fill_until_complete(contacts, filled)
        self.assertEqual(gaps2, [])
        self.assertGreaterEqual(rounds, 0)
        by_url = {r["URL"]: r for r in done}
        self.assertEqual(by_url["https://a.pl"]["E-mail"], "a@a.pl")
        self.assertEqual(by_url["https://a.pl"]["Telefon"], "500100200")
        self.assertEqual(by_url["https://b.pl"]["E-mail"], "b@b.pl")


if __name__ == "__main__":
    unittest.main()
