# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEGACY_GU = ROOT / "legacy" / "de_gu"
for p in (str(ROOT), str(LEGACY_GU)):
    if p not in sys.path:
        sys.path.insert(0, p)

from retail_store_builder_filter import (
    REQUIRED_RETAIL_CHAIN_KEYWORDS,
    has_store_shell_build_evidence,
    is_interior_fitout_specialist,
)


class StrictGuFilterTest(unittest.TestCase):
    def test_required_chains_whitelist(self):
        self.assertEqual(
            set(REQUIRED_RETAIL_CHAIN_KEYWORDS),
            {"aldi", "rewe", "edeka", "netto", "penny", "kaufland", "lidl", "norma"},
        )

    def test_store_shell_build_evidence(self):
        text = "Generalunternehmer Filialbau. Referenz: Rewe Neubau Leipzig."
        self.assertTrue(has_store_shell_build_evidence(text))

    def test_rejects_interior_without_shell(self):
        text = "Körling Interiors GmbH — Ladeneinrichtung und Shopfitting für Rewe."
        rejected, reason = is_interior_fitout_specialist(text)
        self.assertTrue(rejected)
        self.assertEqual(reason, "innenausbau_shopfitting")

    def test_accepts_filialbau_with_chain(self):
        text = (
            "Generalunternehmer Filialbau. Supermarktbau. "
            "Referenzprojekt Norma Neubau Dresden."
        )
        rejected, _ = is_interior_fitout_specialist(text)
        self.assertFalse(rejected)
        self.assertTrue(has_store_shell_build_evidence(text))


if __name__ == "__main__":
    unittest.main(verbosity=2)
