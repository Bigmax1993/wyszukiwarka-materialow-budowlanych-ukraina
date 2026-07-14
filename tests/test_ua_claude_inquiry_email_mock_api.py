# -*- coding: utf-8 -*-
"""Testy inquiry email UA z mockiem Claude API (bez live Anthropic)."""
from __future__ import annotations

import json
import logging
from unittest.mock import MagicMock, patch

import pytest

from ua_regional_construction_refs import (
    address_present_in_body,
    pick_construction_project,
)

_LOGGER = logging.getLogger("test_ua_claude_inquiry_email_mock_api")

KYIV_CONTACT = {
    "company_name": "ТОВ «БудМатеріали Київ»",
    "official_website": "https://bud-kyiv.example.ua",
    "bundesland": "Kyiv",
    "discovery_bundesland": "Kyiv",
    "full_address": "м. Київ, вул. Хрещатик, 1",
    "retail_chains_found": "цемент, газоблок",
    "page_snippet": "Оптовий продаж будматеріалів у Києві",
}

SK_CONTACT = {
    "company_name": "ТОВ «БудМатеріали Старокостянтинів»",
    "official_website": "https://bud-sk.example.ua",
    "bundesland": "Khmelnytska",
    "discovery_bundesland": "Khmelnytska",
    "full_address": "м. Старокостянтинів, вул. Соборна, 12",
    "retail_chains_found": "цемент, цегла",
    "page_snippet": "Оптовий склад у Старокostянтinові",
}


def _email_json(subject: str, body: str) -> str:
    return json.dumps({"subject": subject, "body": body}, ensure_ascii=False)


def _mock_claude_response(*, project_address: str, company: str, sender: str) -> str:
    body = (
        f"Шановні пані та панове {company},\n\n"
        f"Звертаємось від імені {sender}. "
        f"Будуємо об'єкт за адресою {project_address}. "
        f"Просимо надіслати прайс-лист.\n\n"
        f"З повагою,\nСвінчак Максим\nTel.: +380977091141"
    )
    return _email_json(f"Запит щодо будматеріалів — {company}", body)


@pytest.fixture(autouse=True)
def _mock_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-mock")
    monkeypatch.delenv("REQUIRE_CLAUDE_INQUIRY_EMAIL", raising=False)


@patch("ua_claude_inquiry_email.claude_generate_text")
def test_kyiv_inquiry_email_mock_api_uses_kyiv_project(mock_gen):
    from ua_claude_inquiry_email import claude_generate_inquiry_email_ua

    project = pick_construction_project(
        "Kyiv", seed="https://bud-kyiv.example.ua", prefer_city="Київ"
    )
    assert project.address_uk.startswith("м. Київ")

    mock_gen.return_value = (
        _mock_claude_response(
            project_address=project.address_uk,
            company=KYIV_CONTACT["company_name"],
            sender="ТОВ «Київбуд-Сервіс»",
        ),
        "claude-sonnet-mock",
    )
    cache: dict = {}
    subject, body = claude_generate_inquiry_email_ua(
        KYIV_CONTACT["company_name"],
        _LOGGER,
        cache,
        contact_info=KYIV_CONTACT,
        cache_key=KYIV_CONTACT["official_website"],
    )
    assert subject
    assert address_present_in_body(body, project.address_uk)
    assert mock_gen.call_count == 1
    cached = cache["claude_inquiry_email"][KYIV_CONTACT["official_website"]]
    assert cached["construction_address"] == project.address_uk
    assert cached["model"] == "claude-sonnet-mock"


@patch("ua_claude_inquiry_email.claude_generate_text")
def test_starokonstantynov_mock_api_prefers_local_city_project(mock_gen):
    from ua_claude_inquiry_email import claude_generate_inquiry_email_ua

    project = pick_construction_project(
        "Khmelnytska",
        seed="https://bud-sk.example.ua",
        prefer_city="Старокостянтинів",
    )
    assert "Старокостянтинів" in project.address_uk

    mock_gen.return_value = (
        _mock_claude_response(
            project_address=project.address_uk,
            company=SK_CONTACT["company_name"],
            sender="ТОВ «Хмельницькбуд-Регіон»",
        ),
        "claude-sonnet-mock",
    )
    cache: dict = {}
    subject, body = claude_generate_inquiry_email_ua(
        SK_CONTACT["company_name"],
        _LOGGER,
        cache,
        contact_info=SK_CONTACT,
        cache_key=SK_CONTACT["official_website"],
    )
    assert address_present_in_body(body, project.address_uk)
    assert mock_gen.call_count == 1


@patch("ua_claude_inquiry_email.claude_generate_text")
def test_inquiry_email_injects_address_when_claude_omits_it(mock_gen):
    from ua_claude_inquiry_email import claude_generate_inquiry_email_ua

    project = pick_construction_project(
        "Lvivska", seed="https://lviv.example.ua", prefer_city="Львів"
    )
    mock_gen.return_value = (
        _email_json(
            "Запит прайсу — ТОВ Львів",
            "Шановні пані та панове,\n\nПросимо прайс на цемент.\n\nЗ повагою,\nТест",
        ),
        "claude-sonnet-mock",
    )
    cache: dict = {}
    contact = {
        **KYIV_CONTACT,
        "company_name": "ТОВ Львів",
        "bundesland": "Lvivska",
        "discovery_bundesland": "Lvivska",
        "full_address": "м. Львів, вул. Городоцька, 1",
    }
    _, body = claude_generate_inquiry_email_ua(
        "ТОВ Львів",
        _LOGGER,
        cache,
        contact_info=contact,
        cache_key="https://lviv.example.ua",
    )
    assert address_present_in_body(body, project.address_uk)
    assert project.name_uk in body


@patch("ua_claude_inquiry_email.claude_generate_text")
def test_cached_inquiry_skips_second_api_call(mock_gen):
    from ua_claude_inquiry_email import claude_generate_inquiry_email_ua

    project = pick_construction_project("Kyiv", seed="cache-key-1", prefer_city="Київ")
    mock_gen.return_value = (
        _mock_claude_response(
            project_address=project.address_uk,
            company="ТОВ Cache",
            sender="ТОВ «Київбуд»",
        ),
        "claude-sonnet-mock",
    )
    cache: dict = {}
    kwargs = dict(
        company_name="ТОВ Cache",
        logger=_LOGGER,
        cache=cache,
        contact_info=KYIV_CONTACT,
        cache_key="cache-key-1",
    )
    first = claude_generate_inquiry_email_ua(**kwargs)
    second = claude_generate_inquiry_email_ua(**kwargs)
    assert first == second
    assert mock_gen.call_count == 1


@patch("ua_claude_inquiry_email.claude_generate_text")
def test_stale_cache_without_construction_address_triggers_api(mock_gen):
    from ua_claude_inquiry_email import claude_generate_inquiry_email_ua

    project = pick_construction_project("Odeska", seed="stale", prefer_city="Одеса")
    mock_gen.return_value = (
        _mock_claude_response(
            project_address=project.address_uk,
            company="ТОВ Odesa",
            sender="ТОВ «Одесбуд»",
        ),
        "claude-sonnet-mock",
    )
    cache = {
        "claude_inquiry_email": {
            "stale-key": {
                "subject": "Stary temat",
                "body": "Stary szablon bez adresu budowy.",
            }
        }
    }
    contact = {
        "company_name": "ТОВ Odesa",
        "bundesland": "Odeska",
        "discovery_bundesland": "Odeska",
        "full_address": "м. Одеса, вул. Дерибасівська, 1",
    }
    _, body = claude_generate_inquiry_email_ua(
        "ТОВ Odesa",
        _LOGGER,
        cache,
        contact_info=contact,
        cache_key="stale-key",
    )
    assert mock_gen.call_count == 1
    assert address_present_in_body(body, project.address_uk)


@patch("ua_claude_inquiry_email.claude_generate_text")
def test_invalidate_cache_forces_regeneration(mock_gen):
    from ua_claude_inquiry_email import (
        claude_generate_inquiry_email_ua,
        invalidate_claude_inquiry_email_cache,
    )

    project = pick_construction_project("Kyiv", seed="inv", prefer_city="Київ")
    mock_gen.return_value = (
        _mock_claude_response(
            project_address=project.address_uk,
            company="ТОВ Invalidate",
            sender="ТОВ «Київбуд»",
        ),
        "claude-sonnet-mock",
    )
    cache: dict = {}
    kwargs = dict(
        company_name="ТОВ Invalidate",
        logger=_LOGGER,
        cache=cache,
        contact_info=KYIV_CONTACT,
        cache_key="inv-key",
    )
    claude_generate_inquiry_email_ua(**kwargs)
    invalidate_claude_inquiry_email_cache(
        cache,
        contact_info=KYIV_CONTACT,
        cache_key="inv-key",
        company_name="ТОВ Invalidate",
    )
    claude_generate_inquiry_email_ua(**kwargs)
    assert mock_gen.call_count == 2


@patch("ua_claude_inquiry_email.claude_generate_text")
def test_require_raises_on_api_error(mock_gen, monkeypatch):
    from ua_claude_inquiry_email import claude_generate_inquiry_email_ua

    monkeypatch.setenv("REQUIRE_CLAUDE_INQUIRY_EMAIL", "1")
    mock_gen.side_effect = RuntimeError("Anthropic API 503")
    with pytest.raises(RuntimeError, match="Claude inquiry email wymagany"):
        claude_generate_inquiry_email_ua(
            "ТОВ Fail",
            _LOGGER,
            {},
            contact_info=KYIV_CONTACT,
            require=True,
        )


@patch("ua_claude_inquiry_email.claude_generate_text")
def test_generate_email_content_scraper_uses_mock_claude(mock_gen, monkeypatch):
    import ua_materialy_scraper as scraper

    monkeypatch.setattr(scraper, "ENABLE_CLAUDE_INQUIRY_EMAIL", True)
    monkeypatch.setattr(scraper, "USE_CUSTOM_EMAIL_TEMPLATE", False)
    monkeypatch.setenv("REQUIRE_CLAUDE_INQUIRY_EMAIL", "1")

    project = pick_construction_project("Kyiv", seed="scraper", prefer_city="Київ")
    mock_gen.return_value = (
        _mock_claude_response(
            project_address=project.address_uk,
            company=KYIV_CONTACT["company_name"],
            sender="ТОВ «Київбуд-Сервіс»",
        ),
        "claude-sonnet-mock",
    )
    cache: dict = {}
    subject, body = scraper.generate_email_content(
        KYIV_CONTACT["company_name"],
        _LOGGER,
        cache=cache,
        contact_info=KYIV_CONTACT,
        place_url=KYIV_CONTACT["official_website"],
    )
    assert address_present_in_body(body, project.address_uk)
    assert mock_gen.call_count == 1
    assert subject


@patch("ua_claude_inquiry_email.claude_generate_text")
def test_empty_cache_dict_persists_inquiry_email(mock_gen):
    """Pusty dict cache musi być mutowany ({} jest falsy — regresja)."""
    from ua_claude_inquiry_email import claude_generate_inquiry_email_ua

    project = pick_construction_project(
        "Kyiv", seed="https://bud-kyiv.example.ua", prefer_city="Київ"
    )
    mock_gen.return_value = (
        _mock_claude_response(
            project_address=project.address_uk,
            company="ТОВ Persist",
            sender="ТОВ «Київбуд»",
        ),
        "claude-sonnet-mock",
    )
    cache: dict = {}
    claude_generate_inquiry_email_ua(
        "ТОВ Persist",
        _LOGGER,
        cache,
        contact_info=KYIV_CONTACT,
        cache_key=KYIV_CONTACT["official_website"],
    )
    assert "claude_inquiry_email" in cache
    assert KYIV_CONTACT["official_website"] in cache["claude_inquiry_email"]


@patch("claude_client.requests.post")
def test_claude_client_messages_api_mock(mock_post):
    import claude_client as cc

    cc.configure_claude_limits(unlimited=True)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "content": [{"type": "text", "text": '{"subject":"Test","body":"Treść mock API."}'}]
    }
    mock_post.return_value = mock_resp

    text, model = cc.claude_generate_text(
        "prompt test",
        _LOGGER,
        api_key="test-key",
        cache={},
        bypass_daily_limit=True,
    )
    assert "Treść mock API" in text
    assert model
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["json"]["model"]
    assert call_kwargs["headers"]["x-api-key"] == "test-key"
    assert call_kwargs["json"]["messages"][0]["content"] == "prompt test"
