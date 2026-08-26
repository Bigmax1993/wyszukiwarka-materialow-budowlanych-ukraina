# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from http_page_guard import should_retry_http_status


class HttpRetryPolicyTest(unittest.TestCase):
    def test_no_retry_on_404_410_400(self):
        for status in (400, 404, 405, 410, 414):
            with self.subTest(status=status):
                self.assertFalse(should_retry_http_status(status))

    def test_retry_on_timeout_and_rate_limit(self):
        self.assertTrue(should_retry_http_status(408))
        self.assertTrue(should_retry_http_status(429))

    def test_retry_on_5xx_and_unknown(self):
        self.assertTrue(should_retry_http_status(500))
        self.assertTrue(should_retry_http_status(None))


if __name__ == "__main__":
    unittest.main()
