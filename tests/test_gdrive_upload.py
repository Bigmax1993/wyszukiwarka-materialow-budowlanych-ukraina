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


class GdriveCorporaTest(unittest.TestCase):
    def test_oauth_my_drive_uses_user_corpora(self):
        self.assertEqual(_list_corpora(use_oauth=True, drive_id=None), "user")

    def test_oauth_shared_drive_uses_all_drives(self):
        self.assertEqual(_list_corpora(use_oauth=True, drive_id="abc123"), "allDrives")

    def test_service_account_uses_all_drives(self):
        self.assertEqual(_list_corpora(use_oauth=False, drive_id=None), "allDrives")

    def test_normalize_folder_id_from_url(self):
        url = "https://drive.google.com/drive/folders/1abcXYZ?id=foo"
        self.assertEqual(_normalize_folder_id(url), "1abcXYZ")


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


if __name__ == "__main__":
    unittest.main()
