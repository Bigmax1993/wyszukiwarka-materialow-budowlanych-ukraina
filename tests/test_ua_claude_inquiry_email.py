# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest

from ua_claude_prompts import build_personalized_inquiry_email_prompt_uk
from ua_materialy_inquiry_email_uk import DEFAULT_INQUIRY_PHONE_UK, DEFAULT_INQUIRY_SENDER_NAME_UK


def test_prompt_ukrainian_personalization():
    p = build_personalized_inquiry_email_prompt_uk(
        company_name="ТОВ Будмаркет Львів",
        website="https://budmarket.lviv.ua",
        oblast="Lvivska",
        materials="цегла, блок",
        page_snippet="Продаж цегли та блоків оптом у Львові",
    )
    assert "ТОВ Будмаркет Львів" in p
    assert "україн" in p.lower()
    assert "цегла" in p or "блок" in p


def test_prompt_no_mfg_branding(monkeypatch):
    monkeypatch.setenv("MAIL_SENDER_NAME", "Тестовий Менеджер")
    monkeypatch.setenv("INQUIRY_COMPANY_NAME", "")
    monkeypatch.setenv("INQUIRY_PHONE", "")
    monkeypatch.setenv("INQUIRY_WEBSITE", "")
    p = build_personalized_inquiry_email_prompt_uk(company_name="Test ТОВ")
    lowered = p.lower()
    assert "mfg" not in lowered
    assert "fliesen" not in lowered
    assert "moderner" not in lowered


def test_prompt_includes_ua_phone_and_sender(monkeypatch):
    from ua_materialy_inquiry_email_uk import inquiry_phone, inquiry_sender_name

    monkeypatch.setenv("MAIL_SENDER_NAME", "Свінчак Максим Tel.+4915223655399")
    monkeypatch.setenv("INQUIRY_PHONE", "+49 1522 3655 399")
    monkeypatch.setenv("INQUIRY_COMPANY_NAME", "")
    monkeypatch.setenv("INQUIRY_WEBSITE", "")
    p = build_personalized_inquiry_email_prompt_uk(
        company_name="Test ТОВ",
        discovery_oblast="Kyiv",
    )
    assert DEFAULT_INQUIRY_PHONE_UK in p
    assert inquiry_sender_name() in p
    assert DEFAULT_INQUIRY_SENDER_NAME_UK in p
    assert inquiry_phone() == DEFAULT_INQUIRY_PHONE_UK
    assert "1522" not in p


def test_prompt_forbids_attachments():
    p = build_personalized_inquiry_email_prompt_uk(company_name="Test")
    assert "вкладення" in p.lower() or "файли" in p.lower()


def test_prompt_requires_json_output():
    p = build_personalized_inquiry_email_prompt_uk(company_name="Test")
    assert '"subject"' in p
    assert '"body"' in p


def test_prompt_requires_paragraph_layout():
    p = build_personalized_inquiry_email_prompt_uk(company_name="Test")
    assert "ФОРМАТ ЛИСТА" in p
    assert "\\n\\n" in p
    assert "З повагою," in p


def test_cached_inquiry_without_construction_address_is_ignored():
    from ua_claude_inquiry_email import _cached_inquiry_is_usable

    assert not _cached_inquiry_is_usable(
        {"subject": "Test", "body": "Treść bez adresu budowy."}
    )


def test_cached_inquiry_with_verified_address_is_reused():
    from ua_regional_construction_refs import pick_construction_project
    from ua_claude_inquiry_email import _cached_inquiry_is_usable

    project = pick_construction_project("Khmelnytska", seed="demo")
    body = f"Будуємо об'єкт за адресою {project.address_uk}."
    assert _cached_inquiry_is_usable(
        {
            "subject": "Test",
            "body": body,
            "construction_address": project.address_uk,
        }
    )


def test_require_claude_raises_without_api_key(monkeypatch):
    import logging

    from ua_claude_inquiry_email import claude_generate_inquiry_email_ua

    monkeypatch.setattr(
        "ua_claude_inquiry_email.get_anthropic_api_key",
        lambda: "",
    )
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        claude_generate_inquiry_email_ua(
            "Test ТОВ",
            logging.getLogger("test"),
            {},
            require=True,
        )
