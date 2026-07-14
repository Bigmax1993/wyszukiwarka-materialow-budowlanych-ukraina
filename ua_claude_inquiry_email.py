# -*- coding: utf-8 -*-
"""Claude: spersonalizowane zapytania mailowe UA (ukraiński) per firma."""
from __future__ import annotations

import json
from typing import Callable

from claude_client import claude_generate_text
from email_custom_template import parse_llm_email_json
from scraper_env import get_anthropic_api_key, require_claude_inquiry_email
from ua_claude_prompts import build_personalized_inquiry_email_prompt_uk
from ua_materialy_inquiry_email_uk import ensure_inquiry_contact_in_body
from ua_regional_construction_refs import (
    address_present_in_body,
    inject_construction_project_context,
    pick_construction_project,
)
from ua_regional_sender_context import resolve_discovery_oblast


def _contact_blob(contact_info: dict | None) -> dict[str, str]:
    info = contact_info or {}
    return {
        "company_name": str(
            info.get("company_name_clean")
            or info.get("company_name")
            or info.get("nazwa")
            or ""
        ).strip(),
        "website": str(
            info.get("official_website") or info.get("www") or info.get("url") or ""
        ).strip(),
        "oblast": str(info.get("bundesland") or info.get("oblast") or "").strip(),
        "discovery_bundesland": str(info.get("discovery_bundesland") or "").strip(),
        "address": str(
            info.get("full_address") or info.get("adres") or info.get("address") or ""
        ).strip(),
        "materials": str(info.get("retail_chains_found") or "").strip(),
        "page_snippet": str(info.get("page_snippet") or info.get("snippet") or "").strip(),
        "phone": str(info.get("phones_found") or info.get("phone") or "").strip(),
    }


def _resolve_cache_key(
    *,
    cache_key: str = "",
    contact_info: dict | None = None,
    company_name: str = "",
) -> str:
    ctx = _contact_blob(contact_info)
    key = (cache_key or ctx.get("website") or company_name).strip()
    return key or (company_name or "firma").strip()


def _cached_inquiry_is_usable(cached: object) -> bool:
    """Tylko wpisy z realnym adresem budowy (po 5c3764c) — stare szablony odrzucamy."""
    if not isinstance(cached, dict):
        return False
    subj = str(cached.get("subject") or "").strip()
    body = str(cached.get("body") or "").strip()
    addr = str(cached.get("construction_address") or "").strip()
    if not subj or not body or not addr:
        return False
    return address_present_in_body(body, addr)


def invalidate_claude_inquiry_email_cache(
    cache: dict | None,
    *,
    contact_info: dict | None = None,
    cache_key: str = "",
    company_name: str = "",
) -> None:
    """Usuwa zapis Claude dla kontaktu (np. force_resend / nowy szablon regionalny)."""
    if not cache:
        return
    mail_cache = cache.get("claude_inquiry_email")
    if not isinstance(mail_cache, dict):
        return
    ctx = _contact_blob(contact_info)
    keys = {
        (cache_key or "").strip(),
        (ctx.get("website") or "").strip(),
        (company_name or "").strip(),
        (ctx.get("company_name") or "").strip(),
    }
    for key in keys:
        if key:
            mail_cache.pop(key, None)


def claude_generate_inquiry_email_ua(
    company_name: str,
    logger,
    cache: dict | None,
    *,
    contact_info: dict | None = None,
    cache_key: str = "",
    style_hint: str = "",
    on_step: Callable[[str], None] | None = None,
    require: bool | None = None,
) -> tuple[str, str] | None:
    """
    Pełna personalizacja maila B2B po ukraińsku. Zwraca (subject, body) lub None.
    Wynik cache'owany w cache['claude_inquiry_email'] (z construction_address).
    """
    must_call = require if require is not None else require_claude_inquiry_email()
    api_key = get_anthropic_api_key()
    if not api_key:
        if must_call:
            raise RuntimeError(
                "Brak ANTHROPIC_API_KEY — Claude inquiry email jest wymagany "
                "(regionalne maile z realnym adresem budowy)."
            )
        return None

    key = _resolve_cache_key(
        cache_key=cache_key, contact_info=contact_info, company_name=company_name
    )

    mail_cache = (cache or {}).setdefault("claude_inquiry_email", {})
    cached = mail_cache.get(key)
    if _cached_inquiry_is_usable(cached):
        subj = str(cached.get("subject") or "").strip()
        body = str(cached.get("body") or "").strip()
        return subj, body

    ctx = _contact_blob(contact_info)
    display_name = ctx["company_name"] or (company_name or "").strip() or "Постачальник"
    region_key = resolve_discovery_oblast(ctx, fallback=ctx.get("oblast") or "")
    project = pick_construction_project(region_key, seed=key or display_name)
    prompt = build_personalized_inquiry_email_prompt_uk(
        company_name=display_name,
        website=ctx["website"],
        oblast=ctx["oblast"],
        address=ctx["address"],
        materials=ctx["materials"],
        page_snippet=ctx["page_snippet"],
        style_hint=style_hint,
        discovery_oblast=ctx["discovery_bundesland"],
        construction_project=project,
    )
    try:
        text, model = claude_generate_text(
            prompt,
            logger,
            api_key,
            cache=cache,
            model_tier="verify",
            on_step=on_step,
            bypass_daily_limit=True,
        )
        logger.info("Claude inquiry email UA, model=%s, key=%s", model, key[:80])
        fallback_subject = f"Запит щодо постачання будматеріалів — {display_name}"
        subject, body = parse_llm_email_json(text, fallback_subject)
        body = inject_construction_project_context(body, project)
        body = ensure_inquiry_contact_in_body(body)
        from ua_materialy_inquiry_email_uk import (
            strip_de_campaign_branding,
            strip_german_phones_from_text,
        )

        body = strip_german_phones_from_text(body)
        body = strip_de_campaign_branding(body)
        if not address_present_in_body(body, project.address_uk):
            raise ValueError(
                f"Claude inquiry email bez zweryfikowanego adresu budowy: {project.address_uk}"
            )
        mail_cache[key] = {
            "subject": subject,
            "body": body,
            "model": model,
            "construction_project": project.name_uk,
            "construction_address": project.address_uk,
        }
        return subject, body
    except (json.JSONDecodeError, ValueError, KeyError) as exc:
        logger.warning("Claude inquiry email UA parse error: %s", exc)
        if must_call:
            raise RuntimeError(f"Claude inquiry email wymagany, błąd parsowania: {exc}") from exc
        return None
    except Exception as exc:
        logger.warning("Claude inquiry email UA: %s", exc)
        if must_call:
            raise RuntimeError(f"Claude inquiry email wymagany, błąd API: {exc}") from exc
        return None
