# -*- coding: utf-8 -*-
"""Claude Sonnet: kontakty UA — prompt PL, wsparcie dla kandydatów z regex."""
from __future__ import annotations

from typing import Callable

from claude_client import claude_generate_text
from contact_extract_utils import parse_contact_extract_response
from scraper_env import get_anthropic_api_key
from ua_claude_prompts import build_contact_extract_prompt_pl

UA_CONTACT_EXTRACT_CACHE_VERSION = "ua_contact_pl_v2"


def _contact_extract_cache_key(place_url: str, regex_candidates: list[str]) -> str:
    base = (place_url or "").strip() or "?"
    if not regex_candidates:
        return f"{base}#{UA_CONTACT_EXTRACT_CACHE_VERSION}"
    hint = ",".join(sorted({e.strip().lower() for e in regex_candidates if e and "@" in e})[:6])
    return f"{base}#{UA_CONTACT_EXTRACT_CACHE_VERSION}:{hint[:160]}"


def build_contact_extract_page_bundle(
    *,
    crawl_text: str = "",
    page_snippet: str = "",
    extra_context: str = "",
    regex_phones: list[str] | None = None,
) -> str:
    """Skleja tekst dla Claude gdy crawl jest ubogi (WAF) lub niepełny."""
    parts: list[str] = []
    crawl = (crawl_text or "").strip()
    if crawl:
        parts.append(crawl)
    snippet = (page_snippet or "").strip()
    if snippet and snippet not in crawl:
        parts.append(f"=== fragment strony ===\n{snippet}")
    extra = (extra_context or "").strip()
    if extra:
        parts.append(f"=== kontekst dodatkowy ===\n{extra}")
    phones = [p.strip() for p in (regex_phones or []) if (p or "").strip()]
    if phones:
        parts.append("=== telefony (regex) ===\n" + "\n".join(f"- {p}" for p in phones))
    return "\n\n".join(parts).strip()


def claude_extract_contacts_from_pages_ua(
    company_name: str,
    website: str,
    page_text: str,
    logger,
    cache: dict | None,
    *,
    cache_key: str = "",
    regex_candidates: list[str] | None = None,
    impressum_candidates: list[str] | None = None,
    regex_phones: list[str] | None = None,
    extra_context: str = "",
    on_step: Callable[[str], None] | None = None,
) -> dict | None:
    """Szuka / weryfikuje e-maile i telefony — prompt PL, z podpowiedzią regex."""
    api_key = get_anthropic_api_key()
    regex_emails = [
        e.strip()
        for e in (regex_candidates or [])
        if (e or "").strip() and "@" in e
    ]
    bundle = build_contact_extract_page_bundle(
        crawl_text=page_text,
        page_snippet="",
        extra_context=extra_context,
        regex_phones=regex_phones,
    )
    if not api_key or (not bundle and not regex_emails):
        return None

    key = _contact_extract_cache_key(
        (cache_key or website or company_name or "").strip(),
        regex_emails,
    )
    extract_cache = (cache or {}).setdefault("claude_contact_extract", {})
    if key in extract_cache:
        cached = extract_cache[key]
        return dict(cached) if isinstance(cached, dict) else None

    prompt = build_contact_extract_prompt_pl(
        company_name,
        website,
        bundle,
        regex_candidates=regex_emails,
        impressum_candidates=impressum_candidates,
        regex_phones=regex_phones,
        extra_context=extra_context,
    )
    try:
        text, model = claude_generate_text(
            prompt,
            logger,
            api_key,
            cache=cache,
            model_tier="verify",
            on_step=on_step,
        )
        if logger:
            logger.info(
                "Claude contact extract UA (PL), model=%s, key=%s, regex_hints=%s",
                model,
                key[:100],
                len(regex_emails),
            )
        parsed = parse_contact_extract_response(text)
        extract_cache[key] = parsed
        return parsed
    except Exception as exc:
        if logger:
            logger.warning("Claude contact extract UA: %s", exc)
        return None
