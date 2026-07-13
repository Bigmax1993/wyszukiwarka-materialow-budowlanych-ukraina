# -*- coding: utf-8 -*-
"""
Inteligentny odczyt odpowiedzi e-mail (Claude + walidacja) z fallbackiem regex.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any

from email_custom_template import claude_generate_text_simple
from scraper_env import (
    ENV_USE_CLAUDE_REPLY_INTELLIGENCE,
    get_anthropic_api_key,
    get_env_value,
)

EXTRACTION_VERSION_REGEX = 3
EXTRACTION_VERSION_CLAUDE = 4

CLASSIFICATION_TO_REPLY_STATUS = {
    "offer_with_price": "replied_with_price",
    "questions": "replied_questions",
    "acknowledgment_no_price": "replied_no_price",
    "no_price": "replied_no_price",
    "auto_reply": "auto_reply",
    "bounce": "bounce",
}

ROUTE_KEYS = ("rel_1", "rel_2", "rel_3")

_QUOTE_MARKERS = re.compile(
    r"(?im)^\s*("
    r"from:\s|"
    r"-----original\s+message-----|"
    r"_{5,}|"
    r"w\s+dniu\s+.+\s+pisze:|"
    r"у\s+день\s+.+\s+пише:|"
    r"on\s+.+\s+wrote:|"
    r"am\s+.+\s+schrieb:|"
    r"le\s+.+\s+a\s+écrit|"
    r">\s*dzień\s+dobry|"
    r">\s*доброго\s+дня"
    r")"
)


def is_claude_reply_enabled() -> bool:
    raw = get_env_value(ENV_USE_CLAUDE_REPLY_INTELLIGENCE, "1").strip().lower()
    return raw not in ("0", "false", "no", "off", "nie")


def strip_quoted_reply(text: str) -> str:
    """Usuwa cytowany poprzedni mail (linie >, From:, W dniu … pisze:)."""
    if not text:
        return ""
    lines = text.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(">"):
            break
        if _QUOTE_MARKERS.search(line):
            break
        out.append(line)
    cleaned = "\n".join(out).strip()
    return cleaned if cleaned else (text or "").strip()


def _cache_key_for_reply(from_em: str, subject: str, body: str) -> str:
    digest = hashlib.sha256(
        f"{from_em}|{subject}|{body[:12000]}".encode("utf-8", errors="replace")
    ).hexdigest()[:24]
    return digest


def _relation_context(contact: dict) -> list[dict[str, str]]:
    labels = contact.get("relation_labels") or []
    rows: list[dict[str, str]] = []
    for i, key in enumerate(ROUTE_KEYS):
        label = labels[i] if i < len(labels) else f"Relacja {i + 1}"
        rows.append({"route_key": key, "route_label": str(label)})
    if not rows:
        for i, key in enumerate(ROUTE_KEYS, start=1):
            rows.append({"route_key": key, "route_label": f"Relacja {i}"})
    return rows


def build_reply_extraction_prompt(
    *,
    from_email: str,
    subject: str,
    body_clean: str,
    pdf_excerpt: str,
    lang: str,
    routes: list[dict[str, str]],
) -> str:
    routes_txt = json.dumps(routes, ensure_ascii=False)
    pdf_block = (pdf_excerpt or "").strip()[:6000] or "(brak)"
    if lang == "de":
        return (
            "Du bist Logistik-Assistent. Analysiere NUR die Antwort des Spediteurs (kein zitiertes Angebot des Absenders).\n"
            f"Absender: {from_email}\nBetreff: {subject}\n"
            f"Unsere angefragten Routen (route_key → Label): {routes_txt}\n\n"
            "Antworte NUR mit JSON:\n"
            '{"classification":"offer_with_price|questions|acknowledgment_no_price|auto_reply|bounce",'
            '"confidence":0.0,"routes":[{"route_key":"rel_1","route_label":"...","price":null,"currency":"EUR|PLN|CHF|",'
            '"evidence_quote":"..."}],"questions":[],"needs_human_review":false,"price_evidence":""}\n'
            "Regeln: Ignoriere Impressum (Stammkapital, HRB, USt-ID). Keine erfundenen Preise. "
            "Nur Transportpreise. Wenn nur Bestätigung ohne Preis → acknowledgment_no_price.\n\n"
            f"MAIL:\n{body_clean[:10000]}\n\nPDF-AUSZUG:\n{pdf_block}"
        )
    if lang == "uk":
        return (
            "Ти асистент B2B з будівельних матеріалів. Аналізуй ЛИШЕ відповідь постачальника "
            "(без цитованого нашого запиту).\n"
            f"Від: {from_email}\nТема: {subject}\n\n"
            "Відповідай ЛИШЕ JSON:\n"
            '{"classification":"offer_with_price|questions|acknowledgment_no_price|auto_reply|bounce",'
            '"confidence":0.85,"routes":[],"questions":[],"needs_human_review":false,"price_evidence":""}\n'
            "Правила: ігноруй реєстраційні дані (ЄДРПОУ, ІПН). Не вигадуй цін. "
            "Якщо є ціна/прайс — offer_with_price. Якщо лише питання — questions. "
            "Без ціни — acknowledgment_no_price.\n\n"
            f"ТЕКСТ ВІДПОВІДІ:\n{body_clean[:10000]}\n\n"
            f"PDF (фрагмент):\n{pdf_block}"
        )
    return (
        "Jesteś asystentem logistyki B2B. Analizuj TYLKO odpowiedź spedytora (bez cytowanego naszego zapytania).\n"
        f"Od: {from_email}\nTemat: {subject}\n"
        f"Nasze trasy z zapytania (route_key → etykieta): {routes_txt}\n\n"
        "Odpowiedz WYŁĄCZNIE JSON:\n"
        '{"classification":"offer_with_price|questions|acknowledgment_no_price|auto_reply|bounce",'
        '"confidence":0.85,"routes":[{"route_key":"rel_3","route_label":"Opole (PL) – Saalfeld (DE)",'
        '"price":1100,"currency":"EUR","evidence_quote":"Stawka: 1100 EUR"}],'
        '"questions":[],"needs_human_review":false,"price_evidence":"Stawka: 1100 EUR"}\n'
        "Zasady: Ignoruj stopkę rejestrową (kapitał zakładowy, KRS, NIP, REGON, BDO). "
        "Nie wymyślaj cen. Tylko stawki transportu. Gdy brak wyceny — acknowledgment_no_price.\n\n"
        f"TREŚĆ ODPOWIEDZI:\n{body_clean[:10000]}\n\n"
        f"ZAŁĄCZNIK PDF (fragment):\n{pdf_block}"
    )


def parse_claude_reply_json(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text or "", flags=re.DOTALL)
    raw = match.group(0) if match else (text or "{}")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Claude JSON nie jest obiektem")
    return data


def _safe_float(val: Any) -> float | None:
    if val is None or val == "":
        return None
    try:
        v = float(val)
    except (TypeError, ValueError):
        return None
    if 5 <= v <= 500_000:
        return v
    return None


def normalize_claude_extraction(
    data: dict[str, Any],
    *,
    routes_ctx: list[dict[str, str]],
) -> dict[str, Any]:
    classification = str(data.get("classification") or "acknowledgment_no_price").strip().lower()
    if classification not in CLASSIFICATION_TO_REPLY_STATUS:
        classification = "acknowledgment_no_price"
    try:
        confidence = float(data.get("confidence") or 0)
    except (TypeError, ValueError):
        confidence = 0.0

    rel_map: dict[str, str] = {}
    price_parts: list[str] = []
    main_price: float | None = None
    main_currency = ""
    evidence = str(data.get("price_evidence") or "").strip()

    raw_routes = data.get("routes") or []
    if isinstance(raw_routes, list):
        for item in raw_routes:
            if not isinstance(item, dict):
                continue
            rk = str(item.get("route_key") or "").strip()
            if rk not in ROUTE_KEYS:
                continue
            price = _safe_float(item.get("price"))
            cur = str(item.get("currency") or "").strip().upper()
            if cur in ("€", "EURO"):
                cur = "EUR"
            if cur in ("ZŁ", "ZL"):
                cur = "PLN"
            quote = str(item.get("evidence_quote") or "").strip()
            if price is not None and cur:
                rel_map[rk] = f"{price:.2f} {cur}"
                price_parts.append(rel_map[rk])
                if quote and not evidence:
                    evidence = quote[:300]
                if main_price is None or price > main_price:
                    main_price = price
                    main_currency = cur

    questions = data.get("questions") or []
    if isinstance(questions, list):
        q_txt = "; ".join(str(q).strip() for q in questions if str(q).strip())[:400]
    else:
        q_txt = str(questions)[:400]

    needs_review = bool(data.get("needs_human_review"))
    if confidence < 0.65 and classification == "offer_with_price":
        needs_review = True
    if classification == "offer_with_price" and main_price is None:
        classification = "acknowledgment_no_price"
        needs_review = True

    reply_status = CLASSIFICATION_TO_REPLY_STATUS[classification]
    if questions and reply_status == "replied_no_price":
        reply_status = "replied_questions"

    return {
        "reply_status": reply_status,
        "confidence": confidence,
        "price_main": f"{main_price:.2f}" if main_price is not None else "",
        "price_currency": main_currency,
        "prices_all": "; ".join(price_parts[:8]),
        "price_rel": rel_map,
        "reply_description": (evidence or q_txt)[:400],
        "price_evidence": evidence[:300],
        "needs_human_review": needs_review,
        "extraction_method": "claude",
        "extraction_version": EXTRACTION_VERSION_CLAUDE,
        "questions_text": q_txt,
        "routes_ctx": routes_ctx,
    }


def call_claude_reply_extraction(
    *,
    from_email: str,
    subject: str,
    body_clean: str,
    pdf_excerpt: str,
    lang: str,
    contact: dict,
    logger: logging.Logger | None = None,
    claude_cache: dict | None = None,
) -> dict[str, Any] | None:
    if not is_claude_reply_enabled() or not get_anthropic_api_key():
        return None
    key = _cache_key_for_reply(from_email, subject, body_clean)
    if claude_cache is not None and key in claude_cache:
        cached = claude_cache[key]
        if isinstance(cached, dict) and cached.get("reply_status"):
            return dict(cached)

    routes_ctx = _relation_context(contact)
    prompt = build_reply_extraction_prompt(
        from_email=from_email,
        subject=subject,
        body_clean=body_clean,
        pdf_excerpt=pdf_excerpt,
        lang=lang,
        routes=routes_ctx,
    )
    try:
        text, model = claude_generate_text_simple(prompt, logger=logger)
        if logger:
            logger.info(f"Claude (odpowiedź mail), model: {model}")
        parsed = parse_claude_reply_json(text)
        result = normalize_claude_extraction(parsed, routes_ctx=routes_ctx)
        if claude_cache is not None:
            claude_cache[key] = result
        return result
    except Exception as e:
        if logger:
            logger.warning(f"Claude odczyt odpowiedzi pominięty: {e}")
        return None


def merge_regex_and_claude(
    regex_fields: dict[str, Any],
    claude_fields: dict[str, Any] | None,
) -> dict[str, Any]:
    """Claude ma pierwszeństwo przy wyższej pewności; inaczej regex."""
    if not claude_fields:
        out = dict(regex_fields)
        out["extraction_method"] = "regex"
        out["extraction_version"] = EXTRACTION_VERSION_REGEX
        return out

    out = dict(regex_fields)
    out.update(
        {
            k: v
            for k, v in claude_fields.items()
            if k
            in (
                "reply_status",
                "price_main",
                "price_currency",
                "prices_all",
                "price_rel",
                "reply_description",
                "price_evidence",
                "needs_human_review",
                "extraction_method",
                "extraction_version",
                "questions_text",
            )
            and v not in ("", {}, None)
        }
    )
    if claude_fields.get("price_main") or claude_fields.get("reply_status"):
        out["extraction_method"] = "claude"
        out["extraction_version"] = claude_fields.get(
            "extraction_version", EXTRACTION_VERSION_CLAUDE
        )
    elif regex_fields.get("price_main"):
        out["extraction_method"] = "regex+claude"
    if claude_fields.get("needs_human_review"):
        out["needs_human_review"] = True
    return out


def analyze_incoming_reply(
    *,
    contact: dict,
    from_email: str,
    subject: str,
    body_text: str,
    pdf_text: str,
    pdf_source: str,
    lang: str,
    logger: logging.Logger | None = None,
    claude_cache: dict | None = None,
) -> dict[str, Any]:
    """
    Pełna analiza: strip cytatu → regex → opcjonalnie Claude → scalone pola cache.
    """
    from scraper_email_replies import (
        classify_reply_text,
        extract_price_candidates,
        merge_price_extractions,
    )

    body_clean = strip_quoted_reply(body_text)
    combined = body_clean + "\n" + (pdf_text or "")
    reply_status = classify_reply_text(combined, lang)

    body_prices = extract_price_candidates(body_clean) if reply_status == "replied_with_price" else []
    if reply_status == "replied_questions":
        body_prices = extract_price_candidates(body_clean)
    pdf_prices: list[dict] = []
    if pdf_text:
        pdf_prices = extract_price_candidates(pdf_text)
        if pdf_prices and reply_status in ("replied_no_price", "replied_questions"):
            reply_status = "replied_with_price"

    regex_merged = merge_price_extractions(body_prices, pdf_prices, pdf_source)
    regex_merged["reply_status"] = reply_status
    regex_merged["extraction_method"] = "regex"
    regex_merged["extraction_version"] = EXTRACTION_VERSION_REGEX
    regex_merged["price_evidence"] = (regex_merged.get("reply_description") or "")[:300]
    regex_merged["needs_human_review"] = False

    claude_fields = call_claude_reply_extraction(
        from_email=from_email,
        subject=subject,
        body_clean=body_clean,
        pdf_excerpt=pdf_text,
        lang=lang,
        contact=contact,
        logger=logger,
        claude_cache=claude_cache,
    )
    return merge_regex_and_claude(regex_merged, claude_fields)
