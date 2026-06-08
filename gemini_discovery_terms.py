# -*- coding: utf-8 -*-
"""
Gemini: generowanie fraz Serper (uzupełnienie) gdy szablony dały za mało wyników.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Callable

from campaign_keyword_profile import (
    SERPER_TEMPLATE_PATTERNS,
    gu_required_keywords_sample,
    negative_keywords_sample,
    retail_context_keywords_sample,
)
from de_gu_keywords import BUNDESLAND_CONFIG
from retail_store_builder_filter import (
    STRICT_GU_MARKERS,
    is_generalunternehmer,
)

GEMINI_DISCOVERY_MAX_TERM_LEN = 55
GEMINI_DISCOVERY_MIN_TERM_LEN = 12

_PARSE_LINE_RE = re.compile(r"^\s*(?:\d+[\.\)]\s*)?(.+?)\s*$")


def parse_gemini_term_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("{") or line.startswith("["):
            continue
        m = _PARSE_LINE_RE.match(line)
        candidate = (m.group(1) if m else line).strip().strip('"').strip("'")
        if candidate and candidate not in lines:
            lines.append(candidate)
    return lines


def validate_discovery_term(term: str) -> bool:
    t = (term or "").strip()
    if len(t) < GEMINI_DISCOVERY_MIN_TERM_LEN or len(t) > GEMINI_DISCOVERY_MAX_TERM_LEN:
        return False
    low = t.lower()
    if not is_generalunternehmer(low)[0]:
        return False
    if "bauunternehmen" in low and not any(m.strip() in low for m in STRICT_GU_MARKERS if m.strip()):
        return False
    from de_gu_keywords import SERPER_NEGATIVE_TERMS

    if any(neg in low for neg in SERPER_NEGATIVE_TERMS if len(neg) >= 4):
        return False
    return True


def _cities_for_lands(lands: list[str], *, max_cities: int = 8) -> list[str]:
    cities: list[str] = []
    for land in lands:
        cfg = BUNDESLAND_CONFIG.get(land) or {}
        for city in cfg.get("cities") or ():
            if city not in cities:
                cities.append(city)
            if len(cities) >= max_cities:
                return cities
    return cities


def build_gemini_discovery_prompt(
    lands: list[str],
    *,
    cities: list[str] | None = None,
    terms_requested: int = 10,
    exclude_terms: list[str] | None = None,
) -> str:
    city_list = cities or _cities_for_lands(lands)
    land_str = ", ".join(lands) if lands else "Deutschland"
    city_str = ", ".join(city_list[:8]) if city_list else "—"
    templates = "\n".join(f"- {t}" for t in SERPER_TEMPLATE_PATTERNS[:10])
    exclude_block = ""
    if exclude_terms:
        exclude_block = (
            "\nBereits verwendet (nicht wiederholen):\n"
            + "\n".join(f"- {t}" for t in exclude_terms[:20])
        )
    return (
        "Du bist Assistent für B2B-Prospecting in Deutschland.\n"
        "Ziel: kurze Google-Suchanfragen (Serper) für Generalunternehmer (GU) "
        "im Filialbau / Supermarktbau / Gewerbebau für Einzelhandel.\n\n"
        f"Bundesland: {land_str}\n"
        f"Städte: {city_str}\n\n"
        "Vorlagen (jede neue Zeile = Variante davon, {city} durch Stadt ersetzen):\n"
        f"{templates}\n\n"
        "STRICT:\n"
        f"- Jede Zeile MUSS eines enthalten: {', '.join(gu_required_keywords_sample(max_items=6))}\n"
        f"- Retail-Kontext erwünscht: {', '.join(retail_context_keywords_sample(max_items=8))}\n"
        f"- NICHT: {', '.join(negative_keywords_sample(max_items=8))}\n"
        f"- Max {GEMINI_DISCOVERY_MAX_TERM_LEN} Zeichen pro Zeile\n"
        "- Deutsch, keine Nummerierung, keine Anführungszeichen\n"
        "- Kein reines Ladenbau/Bauunternehmen ohne GU\n"
        f"{exclude_block}\n\n"
        f"Genau {terms_requested} Zeilen, eine Anfrage pro Zeile, sonst nichts."
    )


def _cache_bucket(cache: dict) -> dict:
    return cache.setdefault("gemini_discovery_terms", {})


def get_cached_gemini_terms(
    cache: dict,
    land: str,
    *,
    cache_days: int,
) -> list[str] | None:
    entry = _cache_bucket(cache).get((land or "").strip())
    if not isinstance(entry, dict):
        return None
    at_raw = entry.get("at") or ""
    try:
        at = datetime.fromisoformat(at_raw)
    except (TypeError, ValueError):
        return None
    if datetime.now() - at > timedelta(days=cache_days):
        return None
    terms = entry.get("terms")
    if isinstance(terms, list) and terms:
        return [str(t) for t in terms if str(t).strip()]
    return None


def store_cached_gemini_terms(cache: dict, land: str, terms: list[str]) -> None:
    land_key = (land or "").strip() or "Deutschland"
    _cache_bucket(cache)[land_key] = {
        "at": datetime.now().isoformat(),
        "terms": list(terms),
    }


def generate_gemini_discovery_terms(
    cache: dict,
    logger,
    lands: list[str],
    *,
    gemini_generate_text: Callable,
    api_key: str,
    terms_requested: int = 10,
    cache_days: int = 7,
    use_cache: bool = True,
    exclude_terms: list[str] | None = None,
) -> list[str]:
    """Zwraca zwalidowane frazy Serper (max terms_requested)."""
    land_key = (lands[0] if lands else "").strip() or "Deutschland"
    if use_cache:
        cached = get_cached_gemini_terms(cache, land_key, cache_days=cache_days)
        if cached:
            logger.info("Gemini discovery: cache %s (%s fraz)", land_key, len(cached))
            return cached[:terms_requested]

    if not api_key:
        logger.warning("Gemini discovery: brak GOOGLE_AI_STUDIO_API_KEY")
        return []

    prompt = build_gemini_discovery_prompt(
        lands,
        terms_requested=terms_requested,
        exclude_terms=exclude_terms,
    )
    try:
        logger.info("Gemini discovery: generowanie %s fraz", terms_requested)
        text, model = gemini_generate_text(prompt, logger, api_key, cache=cache)
        logger.info("Gemini discovery terms, model=%s", model)
    except Exception as exc:
        logger.warning("Gemini discovery terms: %s", exc)
        return []

    validated: list[str] = []
    for line in parse_gemini_term_lines(text):
        if validate_discovery_term(line) and line not in validated:
            validated.append(line)
        if len(validated) >= terms_requested:
            break

    if validated and use_cache:
        store_cached_gemini_terms(cache, land_key, validated)
    return validated
