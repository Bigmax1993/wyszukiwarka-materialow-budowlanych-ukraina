# -*- coding: utf-8 -*-
"""Ranking e-maili UA — luźniejsze reguły dla gmail/ukr.net ze strony firmy."""
from __future__ import annotations

import re

from email_targeting import (
    GENERIC_INQUIRY_LOCAL_PARTS,
    MIN_EMAIL_SCORE_FOR_SEND,
    email_domain_related_to_website,
    get_registrable_domain,
    is_unsuitable_inquiry_email,
    score_email_candidate,
)

# Skrzynki zewnętrzne często podawane na ukraińskich stronach B2B zamiast @domena.ua.
UA_THIRD_PARTY_INBOX_DOMAINS = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "ukr.net",
        "i.ua",
        "meta.ua",
        "bigmir.net",
        "outlook.com",
        "hotmail.com",
        "yahoo.com",
        "icloud.com",
        "proton.me",
        "protonmail.com",
    }
)

UA_GENERIC_LOCAL_PARTS = GENERIC_INQUIRY_LOCAL_PARTS | frozenset(
    {
        "sales",
        "zakaz",
        "zamovlennya",
        "zamovlenia",
        "opt",
        "vidguk",
        "manager",
        "sklad",
        "postach",
        "postavka",
        "commercial",
        "order",
        "orders",
        "dealer",
    }
)


def _fold_token(value: str) -> str:
    low = (value or "").lower()
    for src, dst in (
        ("ä", "ae"),
        ("ö", "oe"),
        ("ü", "ue"),
        ("ß", "ss"),
        ("é", "e"),
    ):
        low = low.replace(src, dst)
    return re.sub(r"[^a-z0-9]", "", low)


def local_part_matches_website(local: str, website_url: str) -> bool:
    """Czy local-part wskazuje na tę samą firmę co domena www (np. venbud.dealer ↔ venbud.ua)."""
    host = get_registrable_domain(website_url)
    if not host:
        return False
    local_folded = _fold_token(local)
    if len(local_folded) < 3:
        return False
    host_label = _fold_token(host.split(".", 1)[0])
    if len(host_label) >= 4 and (host_label in local_folded or local_folded in host_label):
        return True
    for part in re.split(r"[._\-+]", local or ""):
        part_folded = _fold_token(part)
        if len(part_folded) >= 4 and (
            part_folded in host_label or host_label in part_folded
        ):
            return True
    for token in re.split(r"[-_]", host_label):
        if len(token) >= 4 and token in local_folded:
            return True
    return False


def ua_scraped_inbox_floor_score(email: str, website_url: str) -> int:
    """
    Minimalny score dla skrzynek gmail/ukr.net znalezionych na stronie firmy.
    Zwraca MIN_EMAIL_SCORE_FOR_SEND gdy adres wygląda na firmowy, inaczej 0.
    """
    low = (email or "").strip().lower()
    if is_unsuitable_inquiry_email(low):
        return 0
    local, _, domain = low.partition("@")
    local = local.strip()
    domain = domain.strip()
    if domain not in UA_THIRD_PARTY_INBOX_DOMAINS:
        return 0
    if local in UA_GENERIC_LOCAL_PARTS:
        return MIN_EMAIL_SCORE_FOR_SEND
    if local_part_matches_website(local, website_url):
        return MIN_EMAIL_SCORE_FOR_SEND
    if email_domain_related_to_website(domain, website_url):
        return MIN_EMAIL_SCORE_FOR_SEND
    return 0


def score_email_candidate_ua(email: str, website_url: str) -> int:
    score = score_email_candidate(email, website_url)
    floor = ua_scraped_inbox_floor_score(email, website_url)
    if floor:
        return max(score, floor)
    return score


def rank_email_candidates_ua(
    candidates: list[str], website_url: str
) -> list[tuple[str, int]]:
    ranked: list[tuple[str, int]] = []
    seen: set[str] = set()
    for raw in candidates:
        email = (raw or "").strip().lower()
        if not email or email in seen or "@" not in email:
            continue
        seen.add(email)
        ranked.append((email, score_email_candidate_ua(email, website_url)))
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked


def pick_best_email_for_inquiry_ua(
    candidates: list[str], website_url: str
) -> tuple[str, int]:
    ranked = rank_email_candidates_ua(candidates, website_url)
    if not ranked:
        return "", 0
    best, score = ranked[0]
    if score < MIN_EMAIL_SCORE_FOR_SEND or is_unsuitable_inquiry_email(best):
        return "", score
    return best, score


def pick_best_email_from_website_scrape_ua(
    candidates: list[str], website_url: str
) -> tuple[str, int]:
    """
    Luźniejszy wybór dla maili ze strony firmy (UA).
    Akceptuje info@/kontakt@ oraz gmail/ukr.net powiązane z domeną www.
    """
    ranked = rank_email_candidates_ua(candidates, website_url)
    if not ranked:
        return "", 0
    best, score = ranked[0]
    if is_unsuitable_inquiry_email(best):
        return "", score
    if score >= MIN_EMAIL_SCORE_FOR_SEND:
        return best, score
    local = best.split("@", 1)[0].strip().lower()
    if local in GENERIC_INQUIRY_LOCAL_PARTS and score >= 6:
        return best, max(score, MIN_EMAIL_SCORE_FOR_SEND)
    floor = ua_scraped_inbox_floor_score(best, website_url)
    if floor:
        return best, max(score, floor)
    return "", score
