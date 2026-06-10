# -*- coding: utf-8 -*-
"""
Killer-Prompts für Claude Sonnet — GU/Filialbau-Kampagne DE.
Jeder Prompt: eine Aufgabe, strikt JSON — Portale/PDF/Operatoren ablehnen.
"""
from __future__ import annotations

import re

from campaign_keyword_profile import (
    SERPER_TEMPLATE_PATTERNS,
    gu_required_keywords_sample,
    large_company_markers_sample,
    negative_keywords_sample,
    retail_chain_keywords_sample,
    retail_context_keywords_sample,
    small_company_markers_sample,
)

_REQUIRED_CHAINS = "aldi, rewe, edeka, netto, penny, kaufland, norma"
PAGE_VERIFY_MAX_CHARS = 18000
CONTACT_EXTRACT_MAX_CHARS = 16000
_CONTACT_EXTRACT_TEXT_PRIORITY = (
    "impressum",
    "kontakt",
    "contact",
    "anschrift",
    "geschäftsführ",
    "datenschutz",
    "mailto",
    "@",
    "tel",
    "telefon",
    "phone",
    "fax",
    "e-mail",
    "email",
)
_PAGE_VERIFY_TEXT_PRIORITY = (
    "referenz",
    "projekt",
    "auftraggeber",
    "netto",
    "rewe",
    "aldi",
    "lidl",
    "kaufland",
    "penny",
    "edeka",
    "einzelhandel",
    "retail",
    "filial",
    "supermarkt",
    "discounter",
    "generalunternehmer",
    "gewerbebau",
    "karriere",
    "stellen",
)


def prioritize_page_text_for_verify(
    page_text: str,
    *,
    max_chars: int = PAGE_VERIFY_MAX_CHARS,
    priority_keywords: tuple[str, ...] | None = None,
) -> str:
    """Wichtige Zeilen zuerst — innerhalb max_chars (Keywords konfigurierbar)."""
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
    gu_kw = ", ".join(gu_required_keywords_sample())
    retail_kw = ", ".join(retail_context_keywords_sample())
    chain_kw = ", ".join(retail_chain_keywords_sample())
    neg_kw = ", ".join(negative_keywords_sample())
    small_kw = ", ".join(small_company_markers_sample())
    large_kw = ", ".join(large_company_markers_sample())
    return f"""ROLLE
Du bist Senior-Due-Diligence-Analyst für B2B-Outreach an kleine Generalunternehmer in Deutschland,
die Lebensmittelmärkte / Filialen NEU BAUEN oder UMBAUEN (Filialbau, Supermarktbau, Marktneubau, Hochbau).
KEIN Ziel: Ladeneinrichtung, Shopfitting, Innenausbau, Einzelhandels-Betreiber, Portale, Medien.

WICHTIG — „Generalunternehmer" steht NICHT immer auf der Website!
Entscheidend: PROJEKTNACHWEIS für Markt-/Filial-BAU (Schale/Hochbau), nicht nur Innenausstattung.

AUFGABE
Lies den vollständigen Website-Auszug (alle gecrawlten Unterseiten, markiert mit „=== URL ===").
Inkl. Bildpfade, alt-Texte, Galerie-Beschriftungen, Karriere-Stellen. Passt die Firma?
Antworte NUR mit einem JSON-Objekt — kein Markdown, kein Kommentar.

WAS ZÄHLT ALS NACHWEIS (Referenzen / Portfolio — KEIN fester Tab nötig)
• Neubau/Umbau/Sanierung eines Marktgebäudes (Filialbau, Supermarktbau, Marktneubau)
• Fotos/Galerie: Baustelle, Außenansicht Markt, Eröffnung, Rohbau — nicht nur Regale/Möbel
• Projektbeschreibungen: „Neubau Rewe …", „Umbau Aldi …", „Filialbau für Netto"
• Karriere mit Auftraggeber einer erlaubten Kette (z. B. Netto Marken-Discount)

SOFORT is_gu=false / has_retail_context=false
• Ladeneinrichtung, Shopfitting, Innenausbau, Ladenausstattung, Möbelbau, Store Design
• Nur Innenausstattung eines Marktes — auch wenn Rewe/Aldi genannt wird
• Betreiber/Händler (Öffnungszeiten, Prospekt, Filialfinder), Medienportal, Vergabeportal

ENTSCHEIDUNGSBAUM (in dieser Reihenfolge)
1) Innenausbau/Shopfitting dominiert → is_gu=false
2) primary_role = Betreiber/Händler/Medienportal/Ladeneinrichter → is_gu=false
3) Kein BAU/Auftragnehmer → is_gu=false
4) Baufirma ja, aber KEIN Markt-/Filial-Bauprojekt → has_retail_context=false
5) Nur Büro/Wohn ohne Supermarkt/Discounter/Filiale → has_retail_context=false
6) Passt: is_gu=true, has_retail_context=true, matched_chains nicht leer
7) Größe → is_small_firm

HANDELSKETTE — PFLICHT (Whitelist)
Erlaubt NUR: {_REQUIRED_CHAINS}
• has_retail_context=true NUR mit Bauprojekt (Neubau/Umbau Marktgebäude) UND mindestens einer Kette in matched_chains
• matched_chains: nur Kleinbuchstaben, nur wenn Kette WÖRTLICH als Projekt/Auftraggeber genannt
• Ohne benannte Kette aus der Whitelist → has_retail_context=false

FELD is_small_firm — DU ENTSCHEIDEST (Pflichtfeld)
Ziel: kleine / regionale Baufirma — KEIN Weltkonzern.
is_small_firm=true bei z. B.:
• Familienunternehmen, inhabergeführt, Meisterbetrieb, regional, Mittelstand, GmbH mit einem Standort
• Typisch < 250 Mitarbeiter — auch wenn „Groep"/„Gruppe"/Muttergesellschaft erwähnt wird
is_small_firm=false bei z. B.:
• STRABAG, Hochtief, Goldbeck, Implenia, PORR, börsennotiert, > 500 MA, global player

KLEIN-INDIZIEN: {small_kw}
GROSS-INDIZIEN: {large_kw}

FELD is_gu — Bedeutung
true = Generalunternehmer / Bauunternehmen Hochbau/Filialbau (NICHT Ladeneinrichter).

FELD has_retail_context — Bedeutung
true = Bauprojekt für Lebensmittelmarkt/Filiale einer Whitelist-Kette.

IM ZWEIFEL: is_gu=false, has_retail_context=false.

HILFS-SCHLÜSSELWÖRTER (nicht alle müssen vorkommen)
[GU — optional]
{gu_kw}

[RETAIL / FILIALBAU / PROJEKTE]
{retail_kw}

[SIECI als Projekt — Pflicht-Whitelist]
{chain_kw}

[ODRZUĆ wenn dominiert]
{neg_kw}

BEISPIELE
✓ JA: „Filialbau seit 1990" + Galerie Rewe/Aldi Neubau Fotos
✓ JA: „Referenzprojekte: Kaufland Umbau Halle, Penny Neubau"
✓ JA: Karriere „Auftraggeber Netto Marken-Discount" + Generalunternehmer Einzelhandelsbau → matched_chains=[netto]
✗ NEIN: „Körling Interiors — Ladeneinrichtung für Rewe" (Innenausbau)
✗ NEIN: „Ladenbau Büros, Praxen, Hotels" ohne Marktprojekt mit Whitelist-Kette
✗ NEIN: GU Einzelhandelsbau ohne Aldi/Rewe/Edeka/Netto/Penny/Kaufland/Norma im Text
✗ NEIN: STRABAG SE, 77.000 Mitarbeiter → is_small_firm=false

FELDER JSON (exakt diese Keys)
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

REGELN
• matched_*: nur Begriffe aus dem Auszug (inkl. Bild-URLs/alt) — nichts erfinden
• matched_retail_keywords: z. B. filialbau, referenz, galerie, neubau, supermarkt, umbau
• matched_chains: nur Kleinbuchstaben (rewe, aldi, …), nur wenn als Projekt genannt
• primary_role: Generalunternehmer, Bauunternehmen, Filialbauer, Betreiber, Medienportal, …
• reason: max. 2 Sätze — welcher Projektnachweis (oder warum abgelehnt)

KONTEXT
{header}

AUTOMATISCHE DOWODY (Vorauswahl aus Crawl)
{evidence}

WEBSITE-AUSZUG (alle Unterseiten, === URL ===)
{snippet or "(leer)"}
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
    return f"""ROLLE
Du bist Daten-QA-Leiter vor dem Excel-Export. Dein Output landet 1:1 in der Tabelle „Kontakte".
Fehlerhafte Zeilen kosten echte B2B-Mails an falsche Empfänger — sei gnadenlos präzise.

ZIELGRUPPE (nur diese Firmen dürfen einen Namen behalten)
Kleine Generalunternehmer / Bauunternehmen mit Filialbau, Supermarktbau, Neubau oder Umbau von Märkten
(Aldi, Rewe, Edeka, Netto, Penny, Kaufland, Norma als Projekt-Referenz — keine Ladeneinrichtung).
KEINE Einzelhandels-Märkte als Betreiber. KEINE Portale. KEINE PDF-Titel. KEINE Städte als „Firmenname".

AUFGABE
Bereinige die Eingabefelder für Excel. Antworte NUR mit einem JSON-Objekt — kein Markdown.

SCHEMA (exakt, alle Keys, leere Strings erlaubt)
{{"company_name_clean":"","address":"","phone":"","website":"","bundesland":"","handelsketten":"","url":""}}

═══ company_name_clean — KILLER-REGELN (höchste Priorität) ═══
ERLAUBT: Offizieller Firmenname + Rechtsform in EINER Zeile.
Rechtsform PFLICHT: GmbH, UG, AG, GbR, e.K., KG, OHG, PartG, Co. KG, SE.
OK: „Müller Filialbau GmbH", „SuS Bau GmbH", „Wiessner Baugeschäft GmbH"
NICHT OK: „Generalunternehmer Leipzig", „ALDI Neubau Borna", „Gewerbebau", reiner Ladenbau ohne GU

SOFORT company_name_clean = "" bei:
• PDF/Dokument: [PDF], Bebauungsplan, Auswirkungsanalyse, „Seite X von Y"
• Software/IT: PDF-XChange, Adobe, Microsoft, Tracker, shop@pdf-*
• Portale/Kataloge: 11880, GelbeSeiten, Wikipedia, Vergabemarktplatz, Nexxt-Change, IHK-Listen, Top-10-Listen
• Nur Ort/Projekt/Headline: „Erfurt", „Penny Neubau", Zeitungstitel ohne Firma
• URL, E-Mail, Emoji, Marketing-Slogan, Doppelpunkt am Ende

Ableitung nur aus Impressum-Kontext erlaubt, wenn Eingabe Müll ist — NIEMALS erfinden.
Unsicher → "".

═══ Excel-Spalten (Formatierung) ═══
• address → „Straße, PLZ Ort" (Deutschland) oder ""
• phone → genau EINE deutsche Nummer (+49 oder 0…), kein Fax, kein „Tel./Fax", kein Doppelwert
• website → https://firmendomain.tld (Root, keine Unterseite, kein Verzeichnis, kein PDF)
• url → identisch zur Basis-URL (https://domain.tld)
• bundesland → GENAU ein Wert aus: [{states}] — sonst ""
• handelsketten → nur Kleinbuchstaben, kommagetrennt: rewe, aldi, edeka, netto, penny, kaufland, norma — oder ""
• email_nur_info: NICHT in JSON übernehmen — nur zur Plausibilitätsprüfung

NEGATIV-BEISPIELE (alles → leere Felder oder Name "")
Eingabe name=„PDF Bauantrag Stadt Erfurt" → company_name_clean=""
Eingabe name=„REWE Markt Süd" → company_name_clean=""
Eingabe phone=„Tel 0341 123, Fax 0341 456" → phone=„+49 341 123" (nur erste Tel.)

EINGABE
name={company}
address={address}
phone={phone}
website={website}
url={url}
handelsketten={handelsketten}
email_nur_info={email}
"""


def build_contact_extract_prompt(
    company_name: str,
    website: str,
    page_text: str,
) -> str:
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
    return f"""ROLLE
Du bist Kontakt-Rechercheur für B2B-Outreach an kleine Generalunternehmer in Deutschland.
Deine einzige Aufgabe: E-Mail-Adressen und Telefonnummern aus dem Website-Auszug finden.

KONTEXT
{header}

REGELN (streng)
• Nur Daten extrahieren, die WÖRTLICH im Auszug stehen — nichts erfinden, nichts raten.
• Impressum- und Kontaktseiten haben höchste Priorität.
• mailto:-Links und sichtbare @-Adressen zählen.
• Telefon: deutsche Nummern (+49 oder 0…), keine Fax-Zeilen wenn eine normale Tel.-Zeile existiert.
• Keine Portale (11880, GelbeSeiten), keine noreply/no-reply, keine PDF-Viewer-Adressen.
• Local-Part (vor @): 1–50 Zeichen — längere Adressen ignorieren.
• Wenn nichts gefunden: leere Listen.

OUTPUT (nur JSON, kein Markdown)
{{"company_name":"","emails":[],"phones":[],"impressum_emails":[],"reason":""}}

Felder:
• company_name — offizieller Firmenname nur wenn klar im Impressum/Kontakt genannt, sonst ""
• emails — alle gültigen Firmen-E-Mails aus dem Text
• impressum_emails — Teilmenge von emails, die aus Impressum/Datenschutz/Legal kommen
• phones — max. 3 eindeutige Telefonnummern
• reason — max. 1 Satz (z. B. „Impressum info@…" oder „keine Kontakte im Auszug")

WEBSITE-AUSZUG (vollständiger Domain-Crawl)
{snippet or "(leer)"}
"""


def build_discovery_terms_prompt(
    lands: list[str],
    *,
    city_str: str,
    land_str: str,
    terms_requested: int,
    exclude_block: str = "",
    max_term_len: int = 55,
) -> str:
    templates = "\n".join(f"- {t}" for t in SERPER_TEMPLATE_PATTERNS[:10])
    gu_kw = ", ".join(gu_required_keywords_sample(max_items=6))
    retail_kw = ", ".join(retail_context_keywords_sample(max_items=8))
    neg_kw = ", ".join(negative_keywords_sample(max_items=8))
    return f"""ROLLE
Du generierst Google-Suchanfragen (Serper API) für die Discovery kleiner GU im Filialbau in Deutschland.
Jede Zeile = eine Suchanfrage. Qualität vor Quantität.

KONTEXT
Bundesland: {land_str}
Städte: {city_str}

VORLAGEN (Varianten, {{city}} durch echte Stadt ersetzen)
{templates}

PFLICHT pro Zeile
• Mindestens ein GU-Marker: {gu_kw}
• Retail/Filialbau-Kontext erwünscht: {retail_kw}
• Max {max_term_len} Zeichen
• Deutsch, keine Nummerierung, keine Anführungszeichen, keine leeren Zeilen

VERBOTEN
• {neg_kw}
• Reines „Bauunternehmen" oder „Ladenbau" OHNE Generalunternehmer/GU/Filialbau-Marker
• Doppelte oder fast identische Zeilen
{exclude_block}

GUTE BEISPIELE
Generalunternehmer Filialbau Hannover
GU Supermarktbau Rewe Neubau Braunschweig
Generalunternehmer Aldi Neubau {city_str.split(",")[0].strip() if city_str else "Leipzig"}

SCHLECHTE BEISPIELE
Bauunternehmen Gewerbebau Hannover
Ladenbau Innenausbau München
REWE Markt Hannover

OUTPUT
Genau {terms_requested} Zeilen — eine Anfrage pro Zeile, sonst NICHTS (kein JSON, kein Kommentar).
"""


def build_custom_email_prompt_de(
    draft: str,
    company_name: str,
    *,
    city_name: str = "",
    delivery_address: str = "",
) -> str:
    ctx_city = f"Projektstadt: {city_name}. " if city_name else ""
    ctx_addr = f"Lieferadresse (unverändert): {delivery_address}. " if delivery_address else ""
    return f"""ROLLE
Du bist B2B-Texter für formelle Preisanfragen auf Deutsch. Minimal anpassen, nicht umschreiben.

EMPFÄNGER
{company_name}
{ctx_city}{ctx_addr}

AUFGABE
Passe die Nutzervorlage minimal an (1–2 Sätze Kontext zur Firma/Region).
Verbessere Lesbarkeit. ALLE Fakten exakt beibehalten: Mengen, Daten, Adressen, Fraktionen, Telefon, Signatur.

VERBOTEN
• Preise erfinden
• Wörter: kostenlos, Sonderangebot, dringend, jetzt zuschlagen
• Signatur inhaltlich ändern (Person, Firma, Telefon identisch)

OUTPUT (nur JSON)
{{"subject":"...","body":"..."}}
subject: max 78 Zeichen, konkret, ohne Re:/Erinnerung
body: vollständige sendefertige E-Mail, Plain Text

VORLAGE
{draft}
"""


def build_custom_email_prompt_pl(
    draft: str,
    company_name: str,
    *,
    city_name: str = "",
    delivery_address: str = "",
) -> str:
    ctx_city = f"Miasto/inwestycja: {city_name}. " if city_name else ""
    ctx_addr = f"Adres dostawy (bez zmian): {delivery_address}. " if delivery_address else ""
    return f"""ROLLE
Jesteś redaktorem B2B dla oficjalnych zapytań ofertowych po polsku. Minimalna personalizacja.

ADRESAT
{company_name}
{ctx_city}{ctx_addr}

ZADANIE
Dostosuj szablon (1–2 zdania kontekstu). Popraw styl. ZACHOWAJ wszystkie fakty: ilości, daty, adresy, frakcje, telefony, podpis.

ZAKAZ
• Wymyślanie cen
• Słowa: gratis, promocja, pilne, kliknij
• Zmiana treści podpisu

OUTPUT (tylko JSON)
{{"subject":"...","body":"..."}}
subject: max 78 znaków, bez Re:/Przypomnienie
body: pełny mail gotowy do wysyłki, plain text

SZABLON
{draft}
"""
