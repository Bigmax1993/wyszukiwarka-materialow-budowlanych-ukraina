# -*- coding: utf-8 -*-
"""
Własna treść zapytania ofertowego z GUI → dopracowanie Gemini per firma.
Nie dotyczy maili przypominających (scraper_email_replies.build_reminder_email).
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from scraper_env import ENV_GEMINI_MODEL, ENV_GEMINI_MODELS, get_env_value, get_google_ai_studio_api_key

GEMINI_TIMEOUT = 45
GEMINI_INTER_MODEL_DELAY = 15


def build_custom_draft_prompt(
    draft: str,
    company_name: str,
    lang: str = "pl",
    *,
    city_name: str = "",
    delivery_address: str = "",
) -> str:
    draft = (draft or "").strip()
    if lang == "de":
        return (
            "Du bist B2B-Assistent. Der Nutzer hat eine E-Mail-Vorlage für eine Preisanfrage geliefert.\n"
            f"Empfängerfirma: {company_name}.\n"
            f"{f'Projektstadt: {city_name}. ' if city_name else ''}"
            f"{f'Lieferadresse (unverändert lassen): {delivery_address}. ' if delivery_address else ''}"
            "Aufgabe: Passe die Vorlage minimal an diese Firma an (1–2 Sätze Kontext), "
            "verbessere Formulierung und Lesbarkeit, behalte aber ALLE Fakten exakt "
            "(Mengen, Daten, Adressen, Fraktionen, Telefon, Firmennamen, Signaturblock).\n"
            "Die Signatur am Ende muss inhaltlich identisch bleiben (gleiche Person/Firma/Telefon).\n"
            "Antworte NUR mit JSON: {\"subject\":\"...\",\"body\":\"...\"}\n"
            "subject: max 78 Zeichen, konkret, ohne Re:/Erinnerung.\n"
            "body: vollständige sendefertige E-Mail auf Deutsch.\n"
            "Keine erfundenen Preise. Keine Wörter: kostenlos, Sonderangebot, dringend.\n\n"
            f"VORLAGE DES NUTZERS:\n{draft}"
        )
    return (
        "Jesteś asystentem B2B. Użytkownik wkleił szablon maila z zapytaniem ofertowym.\n"
        f"Firma adresat: {company_name}.\n"
        f"{f'Miasto/inwestycja: {city_name}. ' if city_name else ''}"
        f"{f'Adres dostawy (bez zmian merytorycznych): {delivery_address}. ' if delivery_address else ''}"
        "Zadanie: lekko spersonalizuj szablon pod tę firmę (1–2 zdania kontekstu), "
        "uporządkuj styl i popraw język, ale zachowaj WSZYSTKIE fakty dokładnie "
        "(ilości, daty, adresy, frakcje, telefony, nazwy firm, blok podpisu).\n"
        "Stopka/podpis na końcu musi pozostać merytorycznie taka sama (ta sama osoba/firma/telefon).\n"
        "Odpowiedz WYŁĄCZNIE JSON: {\"subject\":\"...\",\"body\":\"...\"}\n"
        "subject: max 78 znaków, konkretny, bez Re:/Przypomnienie.\n"
        "body: pełny gotowy do wysyłki mail (plain text).\n"
        "Nie wymyślaj cen. Bez słów: gratis, promocja, pilne, kliknij.\n\n"
        f"SZABLON UŻYTKOWNIKA:\n{draft}"
    )


def parse_gemini_email_json(text: str, fallback_subject: str) -> tuple[str, str]:
    match = re.search(r"\{.*\}", text or "", flags=re.DOTALL)
    raw = match.group(0) if match else (text or "")
    parsed = json.loads(raw)
    subject = str(parsed.get("subject") or fallback_subject).strip()
    body = str(parsed.get("body") or "").strip()
    if not body:
        raise ValueError("Gemini zwróciło pusty body")
    return subject, body


def _gemini_models() -> list[str]:
    raw = get_env_value(ENV_GEMINI_MODELS) or get_env_value(ENV_GEMINI_MODEL) or "gemini-2.0-flash"
    return [m.strip() for m in raw.replace(";", ",").split(",") if m.strip()]


def gemini_generate_text_simple(
    prompt: str, logger: logging.Logger | None = None
) -> tuple[str, str]:
    import requests

    api_key = get_google_ai_studio_api_key()
    if not api_key:
        raise RuntimeError("Brak GOOGLE_AI_STUDIO_API_KEY")
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    last_err: Exception | None = None
    models = _gemini_models()
    for i, model in enumerate(models):
        if i > 0:
            time.sleep(GEMINI_INTER_MODEL_DELAY)
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )
        try:
            r = requests.post(url, json=payload, timeout=GEMINI_TIMEOUT)
            if r.status_code == 429:
                last_err = RuntimeError("Gemini rate limit (429)")
                continue
            r.raise_for_status()
            data = r.json()
            text = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )
            if text:
                return text.strip(), model
        except Exception as e:
            last_err = e
            if logger:
                logger.warning(f"Gemini {model}: {e}")
    raise last_err or RuntimeError("Brak odpowiedzi Gemini")


def beautify_custom_email_draft(
    draft: str,
    company_name: str,
    lang: str = "pl",
    *,
    fallback_subject: str = "",
    city_name: str = "",
    delivery_address: str = "",
    logger: logging.Logger | None = None,
) -> tuple[str, str]:
    """
    Dopracowuje wklejoną treść pod konkretną firmę (zapytania ofertowe).
    """
    draft = (draft or "").strip()
    if not draft:
        raise ValueError("Pusta treść szablonu")
    if not fallback_subject:
        fallback_subject = (
            f"Preisanfrage – {company_name}"
            if lang == "de"
            else f"Zapytanie ofertowe – {company_name}"
        )
    prompt = build_custom_draft_prompt(
        draft,
        company_name,
        lang,
        city_name=city_name,
        delivery_address=delivery_address,
    )
    text, model = gemini_generate_text_simple(prompt, logger=logger)
    if logger:
        logger.info(f"Gemini (własny szablon), model: {model}")
    return parse_gemini_email_json(text, fallback_subject)


def fallback_email_without_gemini(
    draft: str, company_name: str, fallback_subject: str
) -> tuple[str, str]:
    """Gdy brak API — wstaw nazwę firmy w pierwszej linii kontekstu."""
    body = draft.strip()
    if company_name and company_name not in body:
        body = f"{body}\n\n(Firma: {company_name})"
    return fallback_subject, body


def inquiry_try_custom(
    *,
    use_custom: bool,
    custom_draft: str,
    company_name: str,
    lang: str,
    logger: logging.Logger,
    subject_hint: str,
    email_context: dict[str, Any] | None = None,
    on_step: Any = None,
) -> tuple[str, str] | None:
    """
    Jeśli włączony własny szablon — zwraca (subject, body) z Gemini.
    Jeśli nie — zwraca None (scraper używa standardowego generatora).
    Nie dotyczy przypomnień e-mail.
    """
    draft = (custom_draft or "").strip()
    if not use_custom or not draft:
        return None
    if on_step:
        on_step(f"E-mail z własnego szablonu (Gemini, {lang}): {company_name}")
    ctx = email_context or {}
    city_name = str(ctx.get("city_name") or ctx.get("city") or "")
    delivery_address = str(ctx.get("delivery_address") or "")
    try:
        return beautify_custom_email_draft(
            draft,
            company_name,
            lang,
            fallback_subject=subject_hint,
            city_name=city_name,
            delivery_address=delivery_address,
            logger=logger,
        )
    except Exception as e:
        logger.warning(f"Gemini (własny szablon) fallback: {e}")
        if get_google_ai_studio_api_key():
            raise
        return fallback_email_without_gemini(draft, company_name, subject_hint)
