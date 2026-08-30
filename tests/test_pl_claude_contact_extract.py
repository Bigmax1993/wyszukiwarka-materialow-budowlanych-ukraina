# -*- coding: utf-8 -*-
"""Testy Claude contact extract PL (prompt polski, podpowiedzi regex)."""
from __future__ import annotations

from unittest.mock import patch

from claude_contact_extract import merge_claude_contacts_into_collected
from pl_claude_contact_extract import (
    PL_CONTACT_EXTRACT_CACHE_VERSION,
    build_contact_extract_page_bundle,
    claude_extract_contacts_from_pages,
)
from pl_claude_prompts import build_contact_extract_prompt_pl


def test_build_contact_extract_prompt_pl_is_polish_and_lists_regex():
    prompt = build_contact_extract_prompt_pl(
        "Hurtownia Budmat",
        "https://budmat.pl",
        "=== https://budmat.pl/kontakt ===\nFormularz kontaktowy",
        regex_candidates=["kontakt@budmat.pl"],
        regex_phones=["+48 22 123 45 67"],
        extra_context="Hurtownia budowlana Warszawa",
    )
    assert "Jesteś analitykiem kontaktów" in prompt
    assert "Polsce" in prompt
    assert "Generalunternehmer" not in prompt
    assert "kontakt@budmat.pl" in prompt
    assert "+48 22 123 45 67" in prompt
    assert "+380" not in prompt
    assert "REGEX" in prompt


def test_build_contact_extract_page_bundle_combines_sources():
    bundle = build_contact_extract_page_bundle(
        crawl_text="=== https://hurt.pl ===\nmało tekstu",
        page_snippet="Skład budowlany Warszawa",
        extra_context="opis z Serper",
        regex_phones=["+48 601 234 567"],
    )
    assert "hurt.pl" in bundle
    assert "Skład budowlany" in bundle
    assert "opis z Serper" in bundle
    assert "+48 601 234 567" in bundle


@patch("pl_claude_contact_extract.claude_generate_text")
@patch("pl_claude_contact_extract.get_anthropic_api_key", return_value="test-key")
def test_claude_pl_extract_accepts_regex_candidate(mock_key, mock_gen):
    mock_gen.return_value = (
        '{"emails":["kontakt@budmat.pl"],"phones":[],"impressum_emails":[],'
        '"company_name":"Budmat","reason":"Wybrano z listy REGEX"}',
        "claude-sonnet-4-6",
    )
    cache: dict = {"claude_contact_extract": {}}
    parsed = claude_extract_contacts_from_pages(
        "Budmat",
        "https://budmat.pl",
        "(pusty crawl WAF)",
        None,
        cache,
        cache_key="https://budmat.pl",
        regex_candidates=["kontakt@budmat.pl"],
    )
    assert parsed is not None
    assert parsed["emails"] == ["kontakt@budmat.pl"]
    prompt = mock_gen.call_args[0][0]
    assert "kontakt@budmat.pl" in prompt
    assert "Jesteś analitykiem" in prompt
    assert PL_CONTACT_EXTRACT_CACHE_VERSION in str(cache.get("claude_contact_extract"))


@patch("pl_claude_contact_extract.claude_generate_text")
@patch("pl_claude_contact_extract.get_anthropic_api_key", return_value="test-key")
def test_claude_pl_extract_merges_into_collected(mock_key, mock_gen):
    mock_gen.return_value = (
        '{"emails":["biuro@nowy.pl"],"phones":["+48 22 111 22 33"],'
        '"impressum_emails":[],"company_name":"","reason":"Znaleziono w tekście"}',
        "claude-sonnet-4-6",
    )
    cache: dict = {"claude_contact_extract": {}}
    parsed = claude_extract_contacts_from_pages(
        "Test",
        "https://test.pl",
        "Kontakt biuro@nowy.pl",
        None,
        cache,
        cache_key="https://test.pl#2",
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
    assert "biuro@nowy.pl" in out["emails"]
    assert any("48" in p for p in out["phones"])


@patch("pl_claude_contact_extract.claude_generate_text")
@patch("pl_claude_contact_extract.get_anthropic_api_key", return_value="test-key")
def test_claude_pl_cache_key_differs_when_regex_hints_change(mock_key, mock_gen):
    mock_gen.return_value = (
        '{"emails":["a@b.pl"],"phones":[],"impressum_emails":[],"company_name":"","reason":""}',
        "claude-sonnet-4-6",
    )
    cache: dict = {"claude_contact_extract": {}}
    claude_extract_contacts_from_pages(
        "A",
        "https://a.pl",
        "text",
        None,
        cache,
        regex_candidates=["x@gmail.com"],
    )
    claude_extract_contacts_from_pages(
        "A",
        "https://a.pl",
        "text",
        None,
        cache,
        regex_candidates=["y@gmail.com"],
    )
    assert mock_gen.call_count == 2
