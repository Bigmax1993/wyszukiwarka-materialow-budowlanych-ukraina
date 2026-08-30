# -*- coding: utf-8 -*-
"""Testy normalizacji kontaktów — numery PL (+48)."""
from __future__ import annotations

from contact_extract_utils import normalize_phone_contact, parse_contact_extract_response


def test_normalize_phone_contact_pl_international():
    out = normalize_phone_contact("0048 22 123 45 67")
    assert out.startswith("+48")
    assert "22" in out


def test_normalize_phone_contact_pl_local_nine_digits():
    out = normalize_phone_contact("48123456789")
    assert out.startswith("+48")


def test_normalize_phone_contact_de_still_works():
    out = normalize_phone_contact("0049 30 12345678")
    assert "+49" in out


def test_parse_contact_extract_response_normalizes_pl_phones():
    parsed = parse_contact_extract_response(
        '{"emails":["kontakt@hurt.pl"],"phones":["+48 22 123 45 67"],'
        '"impressum_emails":[],"company_name":"Hurt","reason":"ok"}'
    )
    assert parsed["emails"] == ["kontakt@hurt.pl"]
    assert parsed["phones"]
    assert "48" in parsed["phones"][0].replace(" ", "")
