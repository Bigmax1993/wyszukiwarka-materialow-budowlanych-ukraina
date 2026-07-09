# -*- coding: utf-8 -*-
"""Testy luźniejszego scoringu e-mail UA (gmail/ukr.net ze strony firmy)."""
from __future__ import annotations

import pytest

from email_targeting import MIN_EMAIL_SCORE_FOR_SEND
from ua_email_targeting import (
    local_part_matches_website,
    pick_best_email_for_inquiry_ua,
    pick_best_email_from_website_scrape_ua,
    score_email_candidate_ua,
    ua_scraped_inbox_floor_score,
)


@pytest.mark.parametrize(
    "email,website",
    [
        ("venbud.dealer@gmail.com", "https://venbud.ua"),
        ("tovektabud@gmail.com", "https://ektabud.in.ua"),
        ("wikibud7@gmail.com", "https://wikibud.com.ua"),
        ("bud-platforma@ukr.net", "https://bud-platforma.com.ua"),
    ],
)
def test_ua_third_party_inbox_accepted_from_website(email, website):
    score = score_email_candidate_ua(email, website)
    assert score >= MIN_EMAIL_SCORE_FOR_SEND
    best, picked_score = pick_best_email_for_inquiry_ua([email], website)
    assert best == email
    assert picked_score >= MIN_EMAIL_SCORE_FOR_SEND


def test_own_domain_still_preferred():
    best, score = pick_best_email_for_inquiry_ua(
        ["wikibud7@gmail.com", "info@wikibud.com.ua"],
        "https://wikibud.com.ua",
    )
    assert best == "info@wikibud.com.ua"
    assert score >= MIN_EMAIL_SCORE_FOR_SEND


def test_unrelated_gmail_still_rejected():
    score = score_email_candidate_ua("random.person@gmail.com", "https://venbud.ua")
    assert score < MIN_EMAIL_SCORE_FOR_SEND
    best, _ = pick_best_email_for_inquiry_ua(["random.person@gmail.com"], "https://venbud.ua")
    assert best == ""


def test_unsuitable_still_rejected():
    best, _ = pick_best_email_for_inquiry_ua(
        ["noreply@venbud.ua", "privacy@venbud.ua"],
        "https://venbud.ua",
    )
    assert best == ""


def test_website_scrape_picks_gmail_when_only_option():
    best, score = pick_best_email_from_website_scrape_ua(
        ["venbud.dealer@gmail.com"],
        "https://venbud.ua",
    )
    assert best == "venbud.dealer@gmail.com"
    assert score >= MIN_EMAIL_SCORE_FOR_SEND


def test_local_part_matches_website_examples():
    assert local_part_matches_website("venbud.dealer", "https://venbud.ua")
    assert local_part_matches_website("wikibud7", "https://wikibud.com.ua")
    assert local_part_matches_website("tovektabud", "https://ektabud.in.ua")
    assert not local_part_matches_website("d2535090", "https://wikibud.com.ua")


def test_floor_score_helper():
    assert ua_scraped_inbox_floor_score("venbud.dealer@gmail.com", "https://venbud.ua") >= MIN_EMAIL_SCORE_FOR_SEND
    assert ua_scraped_inbox_floor_score("d2535090@gmail.com", "https://wikibud.com.ua") == 0
