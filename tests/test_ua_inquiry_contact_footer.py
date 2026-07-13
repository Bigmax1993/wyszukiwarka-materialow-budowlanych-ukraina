# -*- coding: utf-8 -*-
from __future__ import annotations

from ua_materialy_inquiry_email_uk import ensure_inquiry_contact_in_body


def test_ensure_contact_appends_phone_to_claude_signature(monkeypatch):
    monkeypatch.setenv("MAIL_SENDER_NAME", "Свінчак Максим")
    monkeypatch.delenv("INQUIRY_PHONE", raising=False)
    body = "Шановні пані та панове,\n\nТест.\n\nЗ повагою,\nСвінчак Максим\nТОВ «Будівельник»"
    out = ensure_inquiry_contact_in_body(body)
    assert "+380977091141" in out
    assert "ТОВ «Будівельник»" in out


def test_ensure_contact_keeps_existing_phone(monkeypatch):
    monkeypatch.setenv("INQUIRY_PHONE", "+380671234567")
    body = "Текст\n\nЗ повагою,\nІм'я\nTel.: +380671234567"
    out = ensure_inquiry_contact_in_body(body)
    assert out.count("+380671234567") == 1
