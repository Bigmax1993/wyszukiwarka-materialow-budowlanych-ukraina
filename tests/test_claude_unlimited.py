# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch

from claude_client import (
    configure_claude_limits,
    get_remaining_daily_claude_limit,
    is_claude_limit_reached_today,
    is_claude_unlimited,
)


class TestClaudeUnlimited(unittest.TestCase):
    def tearDown(self):
        configure_claude_limits(daily_limit=3000, reserve=1000, unlimited=True)

    def test_default_is_unlimited(self):
        configure_claude_limits(unlimited=True)
        self.assertTrue(is_claude_unlimited())
        cache = {"claude_daily": {"2099-01-01": 9999}}
        with patch("claude_client._campaign_today", return_value="2099-01-01"):
            self.assertFalse(is_claude_limit_reached_today(cache))
            _, used, remaining = get_remaining_daily_claude_limit(cache)
            self.assertEqual(used, 9999)
            self.assertGreater(remaining, 0)

    def test_limited_mode_respects_reserve(self):
        configure_claude_limits(daily_limit=100, reserve=10, unlimited=False)
        self.assertFalse(is_claude_unlimited())
        cache = {"claude_daily": {"2099-01-01": 95}}
        with patch("claude_client._campaign_today", return_value="2099-01-01"):
            self.assertTrue(is_claude_limit_reached_today(cache))


if __name__ == "__main__":
    unittest.main()
