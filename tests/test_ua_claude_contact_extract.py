# -*- coding: utf-8 -*-
"""Testy Claude contact extract UA (prompt PL, podpowiedzi regex)."""
from __future__ import annotations

from unittest.mock import patch

from claude_contact_extract import merge_claude_contacts_into_collected
from ua_claude_contact_extract import (
    build_contact_extract_page_bundle,
    claude_extract_contacts_from_pages_ua,
)
from ua_claude_prompts import build_contact_extract_prompt_pl


def test_build_contact_extract_prompt_pl_is_polish_and_lists_regex():
    prompt = build_contact_extract_prompt_pl(
        "Venbud",
        "https://venbud.ua",
        "=== https://venbud.ua/kontakt ===\nFormularz kontaktowy",
        regex_candidates=["venbud.dealer@gmail.com"],
        regex_phones=["068 080 48 00"],
        extra_context="Hurtownia budowlana Kijów",
    )
    assert "Jesteś analitykiem kontaktów" in prompt
    assert "Generalunternehmer" not in prompt
    assert "venbud.dealer@gmail.com" in prompt
    assert "068 080 48 00" in prompt
    assert "gmail.com" in prompt
    assert "+380" in prompt
    assert "REGEX" in prompt


def test_build_contact_extract_page_bundle_combines_sources():
    bundle = build_contact_extract_page_bundle(
        crawl_text="=== https://firma.ua ===\nmało tekstu",
        page_snippet="Skład budowlany Kijów",
        extra_context="opis z Serper",
        regex_phones=["093 111 22 33"],
    )
    assert "firma.ua" in bundle
    assert "Skład budowlany" in bundle
    assert "opis z Serper" in bundle
    assert "093 111 22 33" in bundle


@patch("ua_claude_contact_extract.claude_generate_text")
@patch("ua_claude_contact_extract.get_anthropic_api_key", return_value="test-key")
def test_claude_ua_extract_accepts_regex_candidate(mock_key, mock_gen):
    mock_gen.return_value = (
        '{"emails":["venbud.dealer@gmail.com"],"phones":[],"impressum_emails":[],'
        '"company_name":"Venbud","reason":"Wybrano z listy REGEX"}',
        "claude-sonnet-4-6",
    )
    cache: dict = {"claude_contact_extract": {}}
    parsed = claude_extract_contacts_from_pages_ua(
        "Venbud",
        "https://venbud.ua",
        "(pusty crawl WAF)",
        None,
        cache,
        cache_key="https://venbud.ua",
        regex_candidates=["venbud.dealer@gmail.com"],
    )
    assert parsed is not None
    assert parsed["emails"] == ["venbud.dealer@gmail.com"]
    prompt = mock_gen.call_args[0][0]
    assert "venbud.dealer@gmail.com" in prompt
    assert "Jesteś analitykiem" in prompt


@patch("ua_claude_contact_extract.claude_generate_text")
@patch("ua_claude_contact_extract.get_anthropic_api_key", return_value="test-key")
def test_claude_ua_extract_merges_into_collected(mock_key, mock_gen):
    mock_gen.return_value = (
        '{"emails":["office@nowy.ua"],"phones":[],"impressum_emails":[],'
        '"company_name":"","reason":"Znaleziono w tekście"}',
        "claude-sonnet-4-6",
    )
    cache: dict = {"claude_contact_extract": {}}
    parsed = claude_extract_contacts_from_pages_ua(
        "Test",
        "https://test.ua",
        "Kontakt office@nowy.ua",
        None,
        cache,
        cache_key="https://test.ua#2",
        regex_candidates=["stary@gmail.com"],
    )
    collected = {
        "emails": ["stary@gmail.com"],
        "impressum_emails": [],
        "phones": [],
        "company_name": "",
    }
    out = merge_claude_contacts_into_collected(collected, parsed)
    assert "stary@gmail.com" in out["emails"]
    assert "office@nowy.ua" in out["emails"]


@patch("ua_claude_contact_extract.claude_generate_text")
@patch("ua_claude_contact_extract.get_anthropic_api_key", return_value="test-key")
def test_claude_ua_cache_key_differs_when_regex_hints_change(mock_key, mock_gen):
    mock_gen.return_value = (
        '{"emails":["a@b.ua"],"phones":[],"impressum_emails":[],"company_name":"","reason":""}',
        "claude-sonnet-4-6",
    )
    cache: dict = {"claude_contact_extract": {}}
    claude_extract_contacts_from_pages_ua(
        "A",
        "https://a.ua",
        "text",
        None,
        cache,
        regex_candidates=["x@gmail.com"],
    )
    claude_extract_contacts_from_pages_ua(
        "A",
        "https://a.ua",
        "text",
        None,
        cache,
        regex_candidates=["y@gmail.com"],
    )
    assert mock_gen.call_count == 2
