# -*- coding: utf-8 -*-
"""Testy przypomnień UA (ukraiński, interwał 3 dni)."""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LIBS = REPO / "libs"
if str(LIBS) not in sys.path:
    sys.path.insert(0, str(LIBS))

from scraper_email_replies import (  # noqa: E402
    UA_MAX_REMINDERS_PER_CONTACT,
    UA_REMINDER_INTERVAL_DAYS,
    UA_REMINDER_INTERVAL_HOURS,
    backfill_reminder_suppression_for_replies,
    build_reminder_email,
    contact_has_any_reply,
    get_ua_pending_reminder_number,
    had_reply_within_days_of_sent,
    reply_status_label,
    suppress_reminders_for_replied_contact,
    ua_needs_reminder,
)


class TestUaReminderEmail(unittest.TestCase):
    def test_uk_reminder_contains_ukrainian_text(self):
        contact = {
            "company_name_clean": "Budmat UA",
            "email_subject_sent": "Запит щодо цін",
            "email_body_sent": "Доброго дня,\n\nproszę o wycenę.\n\nЗ повагою,\n\nСвінчак Максим\nTel.: +380977091141",
            "email_sent_at": "2026-07-01T10:00:00",
            "email_status": "sent",
            "email_target": "info@budmat.ua",
        }
        subject, body = build_reminder_email(contact, "uk", reminder_number=1)
        self.assertIn("Re:", subject)
        self.assertIn("Доброго дня", body)
        self.assertIn("запит", body.lower())
        self.assertIn("Свінчак", body)
        self.assertIn("Попереднє повідомлення", body)

    def test_uk_second_reminder(self):
        contact = {
            "company_name_clean": "Test",
            "email_subject_sent": "Запит",
            "email_body_sent": "Treść\n\nЗ повагою,\nСвінчак",
            "email_sent_at": "2026-06-01T10:00:00",
            "reminder_sent_at": (datetime.now() - timedelta(days=4)).isoformat(timespec="seconds"),
            "reminder_count": 1,
            "email_status": "reminder_sent",
            "email_target": "a@b.ua",
        }
        _subject, body = build_reminder_email(contact, "uk", reminder_number=2)
        self.assertIn("відповід", body.lower())

    def test_reply_status_label_uk(self):
        self.assertEqual(reply_status_label("replied_with_price", "uk"), "Пропозиція")


class TestUaReminderTiming(unittest.TestCase):
    def test_interval_constants(self):
        self.assertEqual(UA_REMINDER_INTERVAL_DAYS, 3)
        self.assertEqual(UA_REMINDER_INTERVAL_HOURS, 72.0)
        self.assertEqual(UA_MAX_REMINDERS_PER_CONTACT, 1)

    def test_pending_after_3_days(self):
        contact = {
            "email_status": "sent",
            "email_target": "info@test.ua",
            "email_sent_at": (datetime.now() - timedelta(days=4)).isoformat(timespec="seconds"),
        }
        self.assertEqual(get_ua_pending_reminder_number(contact, min_days=3), 1)
        self.assertTrue(ua_needs_reminder(contact, min_days=3))

    def test_not_pending_before_3_days(self):
        contact = {
            "email_status": "sent",
            "email_target": "info@test.ua",
            "email_sent_at": (datetime.now() - timedelta(days=1)).isoformat(timespec="seconds"),
        }
        self.assertIsNone(get_ua_pending_reminder_number(contact, min_days=3))
        self.assertFalse(ua_needs_reminder(contact, min_days=3))

    def test_no_reminder_when_reply_within_3_days(self):
        sent = datetime.now() - timedelta(days=4)
        contact = {
            "email_status": "sent",
            "email_target": "info@test.ua",
            "email_sent_at": sent.isoformat(timespec="seconds"),
            "reply_at": (sent + timedelta(days=2)).isoformat(timespec="seconds"),
            "reply_status": "replied_with_price",
        }
        self.assertTrue(had_reply_within_days_of_sent(contact, 3))
        self.assertIsNone(get_ua_pending_reminder_number(contact, min_days=3))
        self.assertFalse(ua_needs_reminder(contact, min_days=3))
        self.assertEqual(contact.get("email_status"), "replied")

    def test_no_second_ua_reminder(self):
        contact = {
            "email_status": "reminder_sent",
            "email_target": "info@test.ua",
            "email_sent_at": (datetime.now() - timedelta(days=10)).isoformat(timespec="seconds"),
            "reminder_sent_at": (datetime.now() - timedelta(days=5)).isoformat(timespec="seconds"),
            "reminder_count": 1,
        }
        self.assertIsNone(get_ua_pending_reminder_number(contact, min_days=3))

    def test_no_reminder_when_reply(self):
        contact = {
            "email_status": "sent",
            "email_target": "info@test.ua",
            "email_sent_at": (datetime.now() - timedelta(days=10)).isoformat(timespec="seconds"),
            "reply_at": (datetime.now() - timedelta(days=2)).isoformat(timespec="seconds"),
            "has_reply": True,
        }
        self.assertIsNone(get_ua_pending_reminder_number(contact, min_days=3))

    def test_suppress_marks_replied_status(self):
        contact = {
            "email_status": "sent",
            "email_target": "a@b.ua",
            "reply_at": datetime.now().isoformat(timespec="seconds"),
            "reply_status": "replied_no_price",
        }
        self.assertTrue(suppress_reminders_for_replied_contact(contact))
        self.assertEqual(contact["email_status"], "replied")
        self.assertTrue(contact["reminders_suppressed"])
        self.assertIsNone(get_ua_pending_reminder_number(contact, min_days=3))

    def test_backfill_existing_replies(self):
        cache = {
            "contacts": {
                "https://x.ua": {
                    "email_status": "sent",
                    "reply_at": "2026-07-01T10:00:00",
                    "reply_status": "replied_with_price",
                }
            }
        }
        n = backfill_reminder_suppression_for_replies(cache)
        self.assertEqual(n, 1)
        self.assertEqual(cache["contacts"]["https://x.ua"]["email_status"], "replied")


if __name__ == "__main__":
    unittest.main()
