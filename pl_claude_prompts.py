# -*- coding: utf-8 -*-
"""Prompty Claude — kampania PL: hurtownie materiałów budowlanych."""
from __future__ import annotations

import re

from pl_campaign_keyword_profile import (
    SERPER_TEMPLATE_PATTERNS,
    gu_required_keywords_sample,
    large_company_markers_sample,
    negative_keywords_sample,
    retail_chain_keywords_sample,
    retail_context_keywords_sample,
    small_company_markers_sample,
)

_REQUIRED_MATERIALS = "cement, piasek, żwir, cegła, bloczek, armatura, styropian, płytka, gips"
PAGE_VERIFY_MAX_CHARS = 18000
CONTACT_EXTRACT_MAX_CHARS = 16000
_CONTACT_EXTRACT_TEXT_PRIORITY = (
    "kontakt",
    "contact",
    "mailto",
    "@",
    "tel",
    "telefon",
    "e-mail",
    "email",
    "adres",
    "impressum",
    "dane firmy",
)
_PAGE_VERIFY_TEXT_PRIORITY = (
    "materiały budowlane",
    "budowlane",
    "hurtownia",
    "skład budowlany",
    "katalog",
    "asortyment",
    "produkty",
    "cennik",
    "ceny",
    "hurt",
    "skład",
    "dostawa",
    "cement",
    "piasek",
    "żwir",
    "cegła",
    "styropian",
    "płytka",
)


def prioritize_page_text_for_verify(
    page_text: str,
    *,
    max_chars: int = PAGE_VERIFY_MAX_CHARS,
    priority_keywords: tuple[str, ...] | None = None,
) -> str:
    keys = priority_keywords or _PAGE_VERIFY_TEXT_PRIORITY
    raw = (page_text or "").strip()
    if len(raw) <= max_chars:
        return raw
    if "=== http" in raw:
        sections = re.split(r"(?=\n=== https?://)", "\n" + raw)
        sections = [s.strip() for s in sections if s.strip()]
        priority_sec: list[str] = []
        other_sec: list[str] = []
        for sec in sections:
            low = sec.lower()
            if any(k in low for k in keys):
                priority_sec.append(sec)
            else:
                other_sec.append(sec)
        merged = "\n\n".join(priority_sec + other_sec)
    else:
        lines = [ln.strip() for ln in re.split(r"[\n\r]+", raw) if ln.strip()]
        if not lines:
            return raw[:max_chars]
        priority: list[str] = []
        other: list[str] = []
        for ln in lines:
            low = ln.lower()
            if any(k in low for k in keys):
                priority.append(ln)
            else:
                other.append(ln)
        merged = " ".join(priority + other)
    if len(merged) <= max_chars:
        return merged
    return merged[: max_chars - 3] + "..."


def build_contact_extract_prompt_pl(
    company_name: str,
    website: str,
    page_text: str,
    *,
    regex_candidates: list[str] | None = None,
    impressum_candidates: list[str] | None = None,
    regex_phones: list[str] | None = None,
    extra_context: str = "",
) -> str:
    """Prompt PL dla ekstrakcji kontaktów z crawl www (kampania PL)."""
    from claude_page_text import build_claude_context_header, extract_crawl_section_urls

    raw = page_text or ""
    header = build_claude_context_header(
        company_name,
        website,
        pages_crawled=max(raw.count("=== http"), 1 if raw else 0),
        priority_urls=extract_crawl_section_urls(raw),
    )
    snippet = prioritize_page_text_for_verify(
        raw,
        max_chars=CONTACT_EXTRACT_MAX_CHARS,
        priority_keywords=_CONTACT_EXTRACT_TEXT_PRIORITY,
    )
    regex_lines = [
        e.strip()
        for e in (regex_candidates or [])
        if (e or "").strip() and "@" in e
    ]
    impressum_lines = [
        e.strip()
        for e in (impressum_candidates or [])
        if (e or "").strip() and "@" in e
    ]
    phone_lines = [p.strip() for p in (regex_phones or []) if (p or "").strip()]
    regex_block = (
        "\n".join(f"- {e}" for e in regex_lines)
        if regex_lines
        else "(brak — szukaj wyłącznie w tekście strony)"
    )
    impressum_block = (
        "\n".join(f"- {e}" for e in impressum_lines)
        if impressum_lines
        else "(brak)"
    )
    phones_block = (
        "\n".join(f"- {p}" for p in phone_lines)
        if phone_lines
        else "(brak)"
    )
    extra = (extra_context or "").strip()
    if len(extra) > 2500:
        extra = extra[:2497] + "..."
    return f"""ROLA
Jesteś analitykiem kontaktów B2B dla hurtowni i składów materiałów budowlanych w Polsce.
Twoje jedyne zadanie: wskazać najlepszy e-mail do zapytania ofertowego oraz telefony firmy.

KONTEKST
{header}

KANDYDACI Z REGEX (system ich nie wybrał do wysyłki — zweryfikuj, wybierz najlepszy LUB znajdź inny w tekście)
{regex_block}

KANDYDACI Z IMPRESSUM / KONTAKT (regex)
{impressum_block}

TELEFONY ZNALEZIONE PRZEZ REGEX
{phones_block}

DODATKOWY KONTEKST (Serper, weryfikacja, fragment strony)
{extra or "(brak)"}

ZASADY (ścisłe)
• Wyciągaj wyłącznie dane obecne DOSŁOWNIE w tekście strony LUB na listach REGEX powyżej.
• Jeśli REGEX znalazł sensowny e-mail firmowy — UMIEŚĆ go w emails (możesz wybrać najlepszy z listy).
• Priorytet stron: /kontakt, /contact, impressum, o firmie, dane kontaktowe.
• Telefony PL: +48 lub format 0XX… (komórka/stacjonarny); max 3 unikalne numery.
• Odrzuć: noreply, no-reply, privacy, newsletter, rekrutacja, portale (instagram, facebook).
• Local-part (przed @): 1–50 znaków.
• Gdy crawl jest ubogi (WAF, Cloudflare, mało tekstu) — oprzyj się na REGEX + dodatkowym kontekście.
• Niczego nie wymyślaj — jeśli brak danych, zwróć puste listy.

WYJŚCIE (wyłącznie JSON, bez markdown)
{{"company_name":"","emails":[],"phones":[],"impressum_emails":[],"reason":""}}

Pola:
• company_name — oficjalna nazwa firmy tylko gdy jasno w kontakcie/impressum, inaczej ""
• emails — wszystkie sensowne e-maile firmowe (w tym wybrane z REGEX)
• impressum_emails — podzbiór emails ze stron kontakt/impressum/legal
• phones — max 3 unikalne numery PL (+48 lub 0XX…)
• reason — max 1 zdanie po polsku

FRAGMENT STRONY (crawl domeny)
{snippet or "(pusty lub zablokowany przez WAF — użyj REGEX i kontekstu powyżej)"}
"""


def build_page_verify_prompt(
    company_name: str,
    website: str,
    page_text: str,
    *,
    max_chars: int = PAGE_VERIFY_MAX_CHARS,
    serper_blob: str = "",
    pages_crawled: int = 0,
) -> str:
    from claude_page_text import (
        build_automatic_evidence_excerpt,
        build_claude_context_header,
        extract_crawl_section_urls,
    )

    raw = page_text or ""
    priority_urls = extract_crawl_section_urls(raw)
    header = build_claude_context_header(
        company_name,
        website,
        serper_blob=serper_blob,
        pages_crawled=pages_crawled or max(raw.count("=== http"), 1 if raw else 0),
        priority_urls=priority_urls,
    )
    evidence = build_automatic_evidence_excerpt(raw)
    snippet = prioritize_page_text_for_verify(raw, max_chars=max_chars)
    supplier_kw = ", ".join(gu_required_keywords_sample())
    material_kw = ", ".join(retail_context_keywords_sample())
    category_kw = ", ".join(retail_chain_keywords_sample())
    neg_kw = ", ".join(negative_keywords_sample())
    small_kw = ", ".join(small_company_markers_sample())
    large_kw = ", ".join(large_company_markers_sample())
    return f"""ROLA
Jesteś analitykiem B2B dla wyszukiwania dostawców materiałów budowlanych w Polsce.
Cel: hurtownie, składy budowlane, producenci i dystrybutorzy materiałów budowlanych.
NIE cel: portale informacyjne, urzędy, czysti wykonawcy remontów bez sprzedaży materiałów, ogłoszenia OLX.

ZADANIE
Przeczytaj wycinek strony (wszystkie podstrony oznaczone «=== URL ===»).
Czy to komercyjny dostawca materiałów budowlanych? Odpowiedz WYŁĄCZNIE JSON — bez markdown.

CO UZNAĆ ZA DOWÓD
• Sprzedaż/hurt materiałów budowlanych, skład, dostawa, katalog, cennik
• Wzmianka kategorii: {_REQUIRED_MATERIALS}
• Rola: dostawca, producent, dystrybutor, hurtownia, skład budowlany

ODRZUĆ (is_gu=false / has_retail_context=false)
• Biuro architektoniczne, wykończenia wnętrz, remont mieszkań bez sprzedaży materiałów
• Wiadomości, media, urzędy, banki, oferty pracy bez oferty handlowej
• OLX/ogłoszenia używane bez stabilnej działalności hurtowej

POLA JSON (te same klucze dla kompatybilności z pipeline)
• is_gu = true jeśli to dostawca/producent/skład materiałów budowlanych
• has_retail_context = true jeśli jest komercyjna oferta materiałów (katalog, asortyment, ceny, hurt)
• matched_chains = kategorie materiałów z tekstu (cement, piasek, …) — tylko jeśli wymienione
• is_small_firm = regionalna/mała firma (nie duża międzynarodowa sieć)

MAŁE OZNaki: {small_kw}
DUŻE OZNaki (is_small_firm=false): {large_kw}

SŁOWA KLUCZOWE DOSTAWCY: {supplier_kw}
KONTEKST MATERIAŁÓW: {material_kw}
KATEGORIE: {category_kw}
NEGATYWNE: {neg_kw}

SCHEMAT JSON
{{
  "matched_gu_keywords": [],
  "matched_retail_keywords": [],
  "matched_chains": [],
  "matched_negative_keywords": [],
  "is_gu": false,
  "has_retail_context": false,
  "is_small_firm": false,
  "primary_role": "",
  "reason": ""
}}

KONTEKST
{header}

AUTODOWODY
{evidence}

WYCIĄG STRONY
{snippet or "(pusty)"}
"""


def build_row_cleanup_prompt(
    *,
    company: str,
    address: str,
    phone: str,
    email: str,
    website: str,
    states: str,
    handelsketten: str = "",
    url: str = "",
) -> str:
    return f"""ROLA
Przygotowujesz wiersz Excel dla bazy B2B dostawców materiałów budowlanych w Polsce.
Odpowiedz WYŁĄCZNIE JSON.

SCHEMAT
{{"company_name_clean":"","address":"","phone":"","website":"","bundesland":"","handelsketten":"","url":""}}

ZASADY
• company_name_clean — oficjalna nazwa + forma prawna (sp. z o.o., S.A., sp.k., sp.j.) lub ""
• address — pełny adres pocztowy w Polsce (ulica, kod pocztowy, miasto) lub "" (NIE opis produktu, NIE fragment SEO)
• phone — jeden numer PL (+48 lub 0XX…) lub ""
• website — https://domena (katalog główny) lub ""
• bundesland — dokładnie jedno województwo z listy: [{states}] lub "" (NIGDY kod pocztowy, NIGDY numer telefonu)
• handelsketten — kategorie materiałów (cement, piasek, …) oddzielone przecinkiem lub ""
• url — jak website

WEJŚCIE
company={company!r}
address={address!r}
phone={phone!r}
email={email!r}
website={website!r}
handelsketten={handelsketten!r}
url={url!r}
"""


def build_personalized_inquiry_email_prompt_pl(
    *,
    company_name: str,
    website: str = "",
    wojewodztwo: str = "",
    address: str = "",
    materials: str = "",
    page_snippet: str = "",
    style_hint: str = "",
) -> str:
    from pl_materialy_inquiry_email_pl import (
        build_inquiry_sender_brief_pl,
        build_inquiry_signature_pl,
        build_sender_contact_line_pl,
        inquiry_phone,
    )

    snippet = (page_snippet or "").strip()
    if len(snippet) > 3500:
        snippet = snippet[:3497] + "..."
    style = (style_hint or "profesjonalny, naturalny styl B2B, bez szablonowych fraz").strip()
    mats = materials or "materiały budowlane (szeroki asortyment)"
    sender_brief = build_inquiry_sender_brief_pl()
    sender_contact = build_sender_contact_line_pl()
    signature_block = build_inquiry_signature_pl()
    phone = inquiry_phone()
    return f"""ROLA
Jesteś autorem listów B2B po polsku. Piszesz UNIKALNY list do KONKRETNEJ hurtowni / dostawcy materiałów budowlanych w Polsce.
Każdy list ma różnić się sformułowaniami — nie kopiuj jednego szablonu.

NADAWCA (kontekst, nie wymyślaj innych faktów)
{sender_brief}
Kontakt: {sender_contact or "kupujący materiałów budowlanych"}

ODBIORCA
Nazwa: {company_name}
Strona: {website or "(brak)"}
Województwo: {wojewodztwo or "(nieznane)"}
Adres: {address or "(brak)"}
Kategorie materiałów (z bazy): {mats}

FRAGMENT STRONY / OPIS (użyj do personalizacji — wspomnij asortyment, region, specjalizację):
{snippet or "(brak — zwróć się ogólnie do dostawcy materiałów budowlanych)"}

ZADANIE
Napisz w pełni spersonalizowany list ZAPYTANIA o współpracę / ceny hurtowe / cennik.
• Język: WYŁĄCZNIE polski.
• Zwrot: „Szanowni Państwo” lub spersonalizowany do {company_name}.
• Koniecznie wspomnij coś konkretnego o tej firmie (asortyment, region, typ działalności).
• Poproś o cennik lub kontakt do działu hurtu / sprzedaży.
• Nie wymyślaj cen, rabatów, terminów dostawy.
• Styl: {style}
• Długość treści: 120–220 słów (bez podpisu).

ZAKAZANE
• Numery ukraińskie (+380) i niemieckie (+49)
• Jedyny telefon kontaktowy w podpisie: {phone}
• Słowa: gratis, promocja, pilnie, kliknij, rabat 50%
• Ten sam tekst dla różnych firm
• Załączniki / pliki / linki do pobrania
• HTML, markdown

PODPIS (dodaj na końcu body BEZ zmian):
{signature_block}

WYJŚCIE — TYLKO JSON (bez markdown):
{{"subject":"...","body":"..."}}

subject: unikalny, do 78 znaków, po polsku, z nazwą lub specjalizacją firmy
body: pełny list gotowy do wysyłki (plain text), łącznie z podpisem powyżej
"""


def build_custom_email_prompt_uk(
    draft: str,
    company_name: str,
    *,
    city_name: str = "",
    delivery_address: str = "",
) -> str:
    ctx_city = f"Region: {city_name}. " if city_name else ""
    ctx_addr = f"Adres dostawy (bez zmian): {delivery_address}. " if delivery_address else ""
    return f"""ROLA
Jesteś redaktorem listów B2B po polsku. Minimalnie dostosuj szablon do konkretnej firmy.

ODBIORCA
{company_name}
{ctx_city}{ctx_addr}

ZADANIE
Dostosuj szablon (1–2 zdania kontekstu o firmie). Zachowaj WSZYSTKIE fakty: wolumeny, adresy, telefony, podpis.

ZAKAZANE
• Wymyślone ceny
• gratis, promocja, pilnie
• Zmiana podpisu

WYJŚCIE (tylko JSON)
{{"subject":"...","body":"..."}}

SZABLON
{draft}
"""
