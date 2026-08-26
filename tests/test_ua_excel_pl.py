# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ua_excel_pl import (
    SHEET_INFO,
    SHEET_KONTAKTY,
    SHEET_OBWODY,
    append_sheet_rows,
    canonical_header,
    merge_workbooks,
    normalize_record,
    ordered_columns,
    polish_flag_value,
    write_merged_workbook,
)


class ExcelPlHeadersTest(unittest.TestCase):
    def test_maps_german_and_mixed_headers(self):
        self.assertEqual(canonical_header("Firmenname"), "Nazwa firmy")
        self.assertEqual(canonical_header("E-Mail"), "E-mail")
        self.assertEqual(canonical_header("Webseite"), "Strona www")
        self.assertEqual(canonical_header("WWW_geprueft"), "WWW sprawdzone")
        self.assertEqual(canonical_header("Kleinunternehmen"), "Mała firma")
        self.assertEqual(canonical_header("Kategorie_materialow"), "Kategoria materiałów")
        self.assertEqual(canonical_header("GU"), "Generalny wykonawca")
        self.assertEqual(canonical_header("Obwód"), "Obwód")

    def test_flag_values_to_polish(self):
        self.assertEqual(polish_flag_value("ja"), "tak")
        self.assertEqual(polish_flag_value("Nein"), "nie")
        self.assertEqual(polish_flag_value("Так"), "tak")
        self.assertEqual(polish_flag_value("pending"), "pending")

    def test_normalize_record_unions_aliases(self):
        rec = normalize_record(
            {
                "Firmenname": "Budmax",
                "WWW_geprueft": "ja",
                "E-Mail": "a@bud.max",
                "Extra_DE": "zostaje",
            }
        )
        self.assertEqual(rec["Nazwa firmy"], "Budmax")
        self.assertEqual(rec["WWW sprawdzone"], "tak")
        self.assertEqual(rec["E-mail"], "a@bud.max")
        self.assertEqual(rec["Extra_DE"], "zostaje")
        self.assertNotIn("Firmenname", rec)


class ExcelPlAppendTest(unittest.TestCase):
    def test_append_unions_columns_and_merges_by_url(self):
        existing = [
            {
                "Nazwa firmy": "Alpha",
                "URL": "https://alpha.ua",
                "Telefon": "",
            }
        ]
        incoming = [
            {
                "Firmenname": "Alpha",
                "URL": "https://alpha.ua",
                "Telefon": "+380",
                "Kategorie_materialow": "cement",
            },
            {
                "Nazwa firmy": "Beta",
                "URL": "https://beta.ua",
            },
        ]
        rows = append_sheet_rows(existing, incoming, sheet=SHEET_KONTAKTY)
        self.assertEqual(len(rows), 2)
        alpha = next(r for r in rows if r["URL"] == "https://alpha.ua")
        self.assertEqual(alpha["Telefon"], "+380")
        self.assertEqual(alpha["Kategoria materiałów"], "cement")
        cols = ordered_columns(SHEET_KONTAKTY, rows)
        self.assertIn("Kategoria materiałów", cols)
        self.assertLess(cols.index("Nazwa firmy"), cols.index("Kategoria materiałów"))

    def test_rows_without_url_or_email_are_not_collapsed(self):
        existing = [{"Nazwa firmy": "Nieznana firma", "Adres": "A"}]
        incoming = [{"Nazwa firmy": "Nieznana firma", "Adres": "B", "Telefon": "1"}]
        rows = append_sheet_rows(existing, incoming, sheet=SHEET_KONTAKTY)
        self.assertEqual(len(rows), 2)

    def test_merge_two_xlsx_files(self):
        import pandas as pd

        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            a = d / "a.xlsx"
            b = d / "b.xlsx"
            pd.DataFrame(
                [
                    {
                        "Firmenname": "Stara",
                        "Webseite": "https://stara.ua",
                        "WWW_geprueft": "nein",
                    }
                ]
            ).to_excel(a, index=False, sheet_name="Kontakte")
            with pd.ExcelWriter(b, engine="openpyxl") as writer:
                pd.DataFrame(
                    [
                        {
                            "Nazwa firmy": "Nowa",
                            "Strona www": "https://nowa.ua",
                            "WWW sprawdzone": "tak",
                            "Nowa kolumna": "x",
                        }
                    ]
                ).to_excel(writer, index=False, sheet_name="Kontakty")
                pd.DataFrame(
                    [{"Nazwa firmy": "Nowa", "Obwód": "Odeska", "URL": "https://nowa.ua"}]
                ).to_excel(writer, index=False, sheet_name="Wojewodztwa")

            sheets = merge_workbooks([a, b])
            names = {r.get("Nazwa firmy") for r in sheets[SHEET_KONTAKTY]}
            self.assertEqual(names, {"Stara", "Nowa"})
            nowa = next(r for r in sheets[SHEET_KONTAKTY] if r["Nazwa firmy"] == "Nowa")
            self.assertEqual(nowa["Nowa kolumna"], "x")
            self.assertEqual(nowa["WWW sprawdzone"], "tak")
            self.assertEqual(len(sheets[SHEET_OBWODY]), 1)

            out = d / "zbiorczy.xlsx"
            write_merged_workbook(out, sheets)
            book = pd.read_excel(out, sheet_name=None, dtype=str)
            self.assertIn(SHEET_KONTAKTY, book)
            self.assertIn(SHEET_OBWODY, book)
            self.assertIn(SHEET_INFO, book)
            self.assertNotIn("Kontakte", book)
            self.assertNotIn("Firmenname", list(book[SHEET_KONTAKTY].columns))


class MergeEnrichMailColsTest(unittest.TestCase):
    def test_wyslane_name_to_email_and_stamp(self):
        from merge_drive_excel_pl import _email_from_wyslane_name

        email, stamp = _email_from_wyslane_name(
            "2026-07-13_101823_mag_at_dimaks.com.ua_Zapytanie.eml"
        )
        self.assertEqual(email, "mag@dimaks.com.ua")
        self.assertEqual(stamp, "2026-07-13 10:18:23")

    def test_enrich_fills_status_maila_and_wyslano(self):
        from merge_drive_excel_pl import enrich_kontakty_rows

        rows = [
            {
                "Nazwa firmy": "Dimaks",
                "E-mail": "mag@dimaks.com.ua",
                "URL": "https://dimaks.com.ua",
                "Status": "sent",
                "Status maila": "",
                "Wysłano": "",
            }
        ]
        enriched, stats = enrich_kontakty_rows(
            rows,
            contacts={},
            sent_by_email={"mag@dimaks.com.ua": "2026-07-13 10:18:23"},
        )
        self.assertEqual(enriched[0]["Status maila"], "sent")
        self.assertEqual(enriched[0]["Wysłano"], "2026-07-13 10:18:23")
        self.assertGreaterEqual(stats["rows_touched"], 1)


if __name__ == "__main__":
    unittest.main()
