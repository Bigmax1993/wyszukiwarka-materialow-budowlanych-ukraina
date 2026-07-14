# -*- coding: utf-8 -*-
from __future__ import annotations

from ua_materialy_inquiry_email_uk import (
    DEFAULT_INQUIRY_PHONE_UK,
    DEFAULT_INQUIRY_SENDER_NAME_UK,
    FIXED_MATERIAL_INQUIRY_UK,
    build_fixed_material_inquiry_uk,
    build_inquiry_signature_uk,
    build_sender_contact_line_uk,
    format_inquiry_email_body_uk,
    inquiry_phone,
    inquiry_sender_name,
    is_german_phone,
    strip_de_campaign_branding,
    strip_german_phones_from_text,
)


def test_default_sender_name_constant():
    assert DEFAULT_INQUIRY_SENDER_NAME_UK == "Свінчак Максим"


def test_default_phone_constant():
    assert DEFAULT_INQUIRY_PHONE_UK == "+380977091141"


def test_is_german_phone():
    assert is_german_phone("+49 1522 3655 399")
    assert is_german_phone("004915223655399")
    assert not is_german_phone("+380977091141")


def test_inquiry_phone_defaults_to_ua(monkeypatch):
    monkeypatch.delenv("INQUIRY_PHONE", raising=False)
    assert inquiry_phone() == "+380977091141"


def test_inquiry_phone_replaces_german_with_default(monkeypatch):
    monkeypatch.setenv("INQUIRY_PHONE", "+49 1522 3655 399")
    assert inquiry_phone() == "+380977091141"


def test_custom_ua_phone_from_env(monkeypatch):
    monkeypatch.setenv("INQUIRY_PHONE", "+380671234567")
    assert inquiry_phone() == "+380671234567"


def test_signature_includes_ua_phone(monkeypatch):
    monkeypatch.setenv("MAIL_SENDER_NAME", "Свінчак Максим")
    monkeypatch.delenv("INQUIRY_PHONE", raising=False)
    monkeypatch.setenv("INQUIRY_COMPANY_NAME", "")
    monkeypatch.setenv("INQUIRY_WEBSITE", "")
    sig = build_inquiry_signature_uk()
    assert "+380977091141" in sig
    assert "Свінчак Максим" in sig
    assert "+49" not in sig


def test_contact_line_includes_ua_phone(monkeypatch):
    monkeypatch.setenv("MAIL_SENDER_NAME", "Свінчак Максим, Tel.+4915223655399")
    monkeypatch.delenv("INQUIRY_PHONE", raising=False)
    monkeypatch.setenv("INQUIRY_COMPANY_NAME", "")
    monkeypatch.setenv("INQUIRY_WEBSITE", "")
    line = build_sender_contact_line_uk()
    assert "+380977091141" in line
    assert "+49" not in line
    assert "1522" not in line


def test_fixed_template_no_mfg():
    body = build_fixed_material_inquiry_uk()
    low = body.lower()
    assert "mfg" not in low
    assert "fliesen" not in low
    assert inquiry_sender_name() in body or DEFAULT_INQUIRY_SENDER_NAME_UK in body
    assert "+380977091141" in body


def test_fixed_material_constant_has_phone():
    assert "+380977091141" in FIXED_MATERIAL_INQUIRY_UK


def test_strip_de_campaign_branding():
    raw = "Maksym Swinczak, MFG Modernerfliesenboden GmbH"
    cleaned = strip_de_campaign_branding(raw)
    assert "mfg" not in cleaned.lower()
    assert "gmbh" not in cleaned.lower()


def test_strip_de_campaign_branding_preserves_paragraphs():
    raw = "Шановні пані та панове,\n\nПерший абзац.\n\nЗ повагою,\nТест"
    cleaned = strip_de_campaign_branding(raw)
    assert "\n\n" in cleaned
    assert cleaned.startswith("Шановні пані та панове,")
    assert "З повагою," in cleaned


def test_format_inquiry_email_body_uk_dense_single_line():
    dense = (
        "Шановні пані та панове, звертаюся до Вас від імені БК «Альтбуд». "
        "Просимо прайс-лист на цемент та цеглу. "
        "З повагою, Свінчак Максим Менеджер БК «Альтбуд» www.altbud.ua Tel.: +380977091141"
    )
    formatted = format_inquiry_email_body_uk(dense)
    assert formatted.startswith("Шановні пані та панове,\n\n")
    assert "\n\nЗ повагою," in formatted
    assert "+380977091141" in formatted
    assert "www.altbud.ua" in formatted


def test_format_inquiry_email_body_uk_preserves_existing_paragraphs():
    body = "Шановні пані та панове,\n\nАбзац один.\n\nАбзац два.\n\nЗ повагою,\nІм'я"
    formatted = format_inquiry_email_body_uk(body)
    assert formatted.count("\n\n") >= 3


def test_build_inquiry_signature_has_line_breaks():
    sig = build_inquiry_signature_uk()
    assert "\n" in sig
    assert "З повагою," in sig


def test_legacy_sender_falls_back_to_ukrainian_name(monkeypatch):
    monkeypatch.setenv("MAIL_SENDER_NAME", "Maksym Swinczak, MFG Moderner Fliesenboden GmbH")
    from ua_materialy_inquiry_email_uk import inquiry_sender_name

    assert inquiry_sender_name() == DEFAULT_INQUIRY_SENDER_NAME_UK


def test_strip_german_phones_from_text():
    body = "Kontakt\nTel.: +49 1522 3655 399\n\nЗ повагою"
    cleaned = strip_german_phones_from_text(body)
    assert "+49" not in cleaned
    assert "1522" not in cleaned
    assert "З повагою" in cleaned
