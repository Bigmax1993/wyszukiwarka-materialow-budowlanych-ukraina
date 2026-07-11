# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.gdrive_upload_wyniki import (  # noqa: E402
    _list_corpora,
    _normalize_folder_id,
    versioned_xlsx_upload_name,
)


class GdriveVersionedXlsxTest(unittest.TestCase):
    def test_versions_kontakte_xlsx(self):
        name = versioned_xlsx_upload_name(
            "de_gu_bauunternehmen_kontakte.xlsx", stamp="2026-06-08_1405"
        )
        self.assertEqual(name, "de_gu_bauunternehmen_kontakte_2026-06-08_1405.xlsx")

    def test_non_xlsx_unchanged(self):
        self.assertEqual(
            versioned_xlsx_upload_name("de_gu_bauunternehmen_cache.json", stamp="x"),
            "de_gu_bauunternehmen_cache.json",
        )


class GdriveFolderHelpersTest(unittest.TestCase):
    def test_normalize_folder_id_from_url(self):
        url = "https://drive.google.com/drive/folders/abc123XYZ?usp=drive_link"
        self.assertEqual(_normalize_folder_id(url), "abc123XYZ")

    def test_list_corpora_oauth_my_drive(self):
        self.assertEqual(_list_corpora(use_oauth=True, drive_id=None), "user")

    def test_list_corpora_oauth_shared_drive(self):
        self.assertEqual(_list_corpora(use_oauth=True, drive_id="shared123"), "allDrives")


if __name__ == "__main__":
    unittest.main()
