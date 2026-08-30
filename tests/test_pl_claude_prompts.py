# -*- coding: utf-8 -*-
"""Testy promptów Claude — kampania PL materiały budowlane."""
from __future__ import annotations

from pl_claude_prompts import (
    build_contact_extract_prompt_pl,
    build_page_verify_prompt,
    build_personalized_inquiry_email_prompt_pl,
    build_row_cleanup_prompt,
    prioritize_page_text_for_verify,
)


def test_page_verify_prompt_polish_no_ukrainian():
    prompt = build_page_verify_prompt(
        "Hurtownia Budowlana",
        "https://budmat.pl",
        "Hurtownia materiałów budowlanych cement piasek Warszawa",
    )
    assert "Polsce" in prompt
    assert "is_gu" in prompt
    assert "украин" not in prompt.lower()
    assert "ТОВ" not in prompt
    assert "budowlane" in prompt.lower() or "materiał" in prompt.lower()


def test_row_cleanup_prompt_polish_phone_and_wojewodztwo():
    prompt = build_row_cleanup_prompt(
        company="Hurtownia Test sp. z o.o.",
        address="ul. Test 1, 00-001 Warszawa",
        phone="+48 22 123 45 67",
        email="kontakt@test.pl",
        website="https://test.pl",
        states="mazowieckie, malopolskie",
    )
    assert "+48" in prompt
    assert "sp. z o.o." in prompt
    assert "województwo" in prompt.lower() or "bundesland" in prompt.lower()
    assert "NIE opis produktu" in prompt or "NIE fragment SEO" in prompt
    assert "+380" not in prompt
    assert "офіційна" not in prompt


def test_contact_extract_prompt_pl_polish():
    prompt = build_contact_extract_prompt_pl(
        "Skład Budowlany",
        "https://sklad.pl",
        "tel: +48 12 345 67 89 kontakt@sklad.pl",
        regex_phones=["+48 12 345 67 89"],
    )
    assert "Polsce" in prompt
    assert "+48" in prompt
    assert "+380" not in prompt
    assert "Ukrainie" not in prompt


def test_inquiry_email_prompt_polish():
    prompt = build_personalized_inquiry_email_prompt_pl(
        company_name="Hurtownia Mazowsze",
        wojewodztwo="mazowieckie",
        address="ul. Przykładowa 1, Warszawa",
    )
    assert "polsk" in prompt.lower()
    assert "516513965" in prompt
    assert "ZAKAZANE" in prompt
    assert "ukraińskie (+380)" in prompt
    assert "JSON" in prompt


def test_prioritize_page_text_for_verify_polish_keywords():
    long_text = (
        "hurtownia materiałów budowlanych cement piasek katalog cennik "
        + " ".join(["wypełniacz"] * 200)
    )
    out = prioritize_page_text_for_verify(long_text, max_chars=200)
    assert "hurtownia" in out.lower() or "cement" in out.lower()
