# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from retail_store_builder_filter import has_retail_context_without_named_chain


class RetailContextLooseTest(unittest.TestCase):
    def test_accepts_gu_einzelhandel_without_chain_name(self):
        text = (
            "Generalunternehmer für Gewerbe- und Einzelhandelsbau. "
            "Retail-Projekte in Deutschland."
        )
        self.assertTrue(has_retail_context_without_named_chain(text))

    def test_accepts_auftraggeber_with_trade_context(self):
        text = "Bauunternehmen. Auftraggeber aus dem Discounter-Bereich."
        self.assertTrue(has_retail_context_without_named_chain(text))

    def test_rejects_pure_wohnbau(self):
        text = "Bauunternehmen für Wohnungsbau und Bürosanierung."
        self.assertFalse(has_retail_context_without_named_chain(text))


if __name__ == "__main__":
    unittest.main(verbosity=2)
