# -*- coding: utf-8 -*-
"""Bounce (mailer-daemon) — brak przypomnień."""
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
    contact_has_any_reply,
    extract_bounce_recipients,
    get_ua_pending_reminder_number,
    is_bounce_notification,
    suppress_reminders_for_bounced_contact,
    ua_needs_reminder,
)


GMAIL_BOUNCE_BODY = """
Nie znaleziono adresu
Wiadomość nie została dostarczona, ponieważ nie znaleziono adresu odbiorcy
(zapytanie@cemhurt.waw.pl) lub odbiorca nie może odebrać wiadomości.
Odpowiedź otrzymana z serwera zdalnego: 550 Unknown user / Użytkownik nieznany (0)
"""


class TestBounceDetection(unittest.TestCase):
    def test_detects_gmail_bounce(self):
        self.assertTrue(
            is_bounce_notification(
                "mailer-daemon@googlemail.com",
                "Delivery Status Notification (Failure)",
                GMAIL_BOUNCE_BODY,
            )
        )

    def test_extracts_failed_recipient(self):
        recipients = extract_bounce_recipients(
            GMAIL_BOUNCE_BODY,
            known_targets={"zapytanie@cemhurt.waw.pl", "info@test.pl"},
        )
        self.assertEqual(recipients, ["zapytanie@cemhurt.waw.pl"])


class TestBounceReminderSuppression(unittest.TestCase):
    def test_bounce_stops_reminders(self):
        contact = {
            "email_status": "sent",
            "email_target": "zapytanie@cemhurt.waw.pl",
            "email_sent_at": (datetime.now() - timedelta(days=5)).isoformat(
                timespec="seconds"
            ),
        }
        self.assertEqual(get_ua_pending_reminder_number(contact, min_days=3), 1)
        suppress_reminders_for_bounced_contact(
            contact,
            reply_at=datetime.now().isoformat(timespec="seconds"),
            snippet="550 Unknown user",
        )
        self.assertEqual(contact["email_status"], "bounced")
        self.assertEqual(contact["reply_status"], "bounce")
        self.assertTrue(contact.get("reminders_suppressed"))
        self.assertIsNone(get_ua_pending_reminder_number(contact, min_days=3))
        self.assertFalse(ua_needs_reminder(contact, min_days=3))
        self.assertTrue(contact_has_any_reply(contact))


if __name__ == "__main__":
    unittest.main()
