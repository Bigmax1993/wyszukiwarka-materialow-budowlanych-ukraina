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

_REQUIRED_CHAINS = "aldi, rewe, edeka, lidl, netto, penny, kaufland"
PAGE_VERIFY_MAX_CHARS = 12000
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
    page_text: str, *, max_chars: int = PAGE_VERIFY_MAX_CHARS
) -> str:
    """Wichtige Zeilen (Referenzen, Ketten, Karriere) zuerst — innerhalb max_chars."""
    raw = (page_text or "").strip()
    if len(raw) <= max_chars:
        return raw
    lines = [ln.strip() for ln in re.split(r"[\n\r]+", raw) if ln.strip()]
    if not lines:
        return raw[:max_chars]
    priority: list[str] = []
    other: list[str] = []
    for ln in lines:
        low = ln.lower()
        if any(k in low for k in _PAGE_VERIFY_TEXT_PRIORITY):
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
) -> str:
    snippet = prioritize_page_text_for_verify(page_text or "", max_chars=max_chars)
    gu_kw = ", ".join(gu_required_keywords_sample())
    retail_kw = ", ".join(retail_context_keywords_sample())
    chain_kw = ", ".join(retail_chain_keywords_sample())
    neg_kw = ", ".join(negative_keywords_sample())
    small_kw = ", ".join(small_company_markers_sample())
    large_kw = ", ".join(large_company_markers_sample())
    return f"""ROLLE
Du bist Senior-Due-Diligence-Analyst für B2B-Outreach an kleine Bauunternehmen in Deutschland,
die Lebensmittelmärkte / Filialen NEU BAUEN oder UMBAUEN (Filialbau, Supermarktbau, Marktneubau).
KEIN Ziel: Einzelhandels-Märkte als Betreiber, Portale, Medien, reine Büro-/Wohn-Sanierung ohne Marktbezug.

WICHTIG — „Generalunternehmer" steht NICHT immer auf der Website!
Entscheidend sind PROJEKTNACHWEISE für Märkte/Filialen, nicht das Wort GU.

AUFGABE
Lies den Website-Auszug (inkl. Bildpfade, alt-Texte, Galerie-Beschriftungen). Passt die Firma?
Antworte NUR mit einem JSON-Objekt — kein Markdown, kein Kommentar.

WAS ZÄHLT ALS NACHWEIS (Referenzen / Portfolio — KEIN fester Tab nötig)
• Rubrik Referenzen, Portfolio, Realisierungen, Bauprojekte — aber auch ohne diese Überschrift:
• Fotos/Galerie von Märkten: Außenansicht, Innenraum, Baustelle, Eröffnung, Umbau
• Bild-URLs/alt-Texte: rewe-filiale.jpg, aldi-neubau, supermarkt-projekt, filialbau
• Projektbeschreibungen: „Neubau Rewe …", „Umbau Aldi …", „Filialbau für Lidl"
• Listen realisierter Filialen/Märkte mit Ortsnamen
Eine eigene Portfolio-Seite ist NICHT Pflicht — Fotos + kurzer Text reichen.

ENTSCHEIDUNGSBAUM (in dieser Reihenfolge)
1) primary_role = Betreiber/Händler/Medienportal → is_gu=false (z. B. Öffnungszeiten, Prospekt, Filialfinder)
2) Dominieren negative Signale (Vergabeportal, 11880, Wikipedia, Jobbörse) → is_gu=false
3) Kein Hinweis auf BAU/Auftragnehmer (nur Handel, Medien, Verwaltung) → is_gu=false
4) Baufirma ja, aber KEIN Markt-/Filial-Projektnachweis → has_retail_context=false
5) Projekte ja, aber nur Büro/Wohn/Gewerbe ohne Supermarkt/Discounter/Filiale → has_retail_context=false
6) Passt inhaltlich: is_gu=true, has_retail_context=true
7) matched_chains wenn benannte Kette als Projekt/Auftraggeber — sonst leer (siehe unten)
8) Größe prüfen → is_small_firm (siehe unten)

HANDELSKETTE / RETAIL-NACHWEIS (flexibel)
• Ideal: benannte Kette als Projekt/Auftraggeber ({_REQUIRED_CHAINS})
• Auch OK ohne Kette im Portfolio: GU/Bauunternehmen + Einzelhandel/Retail/Gewerbebau
  (z. B. „Einzelhandelsbau", „Retail-Projekte", Karriere: „Auftraggeber Netto")
• has_retail_context=true wenn Kette ODER klarer Retail-/Markt-Baubezug
• matched_chains: nur wenn Kette WÖRTLICH vorkommt — sonst []

FELD is_small_firm — DU ENTSCHEIDEST (Pflichtfeld)
Ziel: kleine / regionale Baufirma — KEIN Weltkonzern.
is_small_firm=true bei z. B.:
• Familienunternehmen, inhabergeführt, Meisterbetrieb, regional, Mittelstand, GmbH mit einem Standort
• Typisch < 250 Mitarbeiter — auch wenn „Groep"/„Gruppe"/Muttergesellschaft erwähnt wird
• Junges regionales GU-Team (z. B. gegründet 2019, Bad Bentheim) mit Retail-Projekten
is_small_firm=false bei z. B.:
• STRABAG, Hochtief, Goldbeck, Implenia, PORR, börsennotiert, > 500 MA, global player
• Dominieren nur Megaprojekte (Flughafen, Autobahn) ohne Retail/Einzelhandel
Unsicher bei regionaler GmbH mit GU + Einzelhandel/Retail → is_small_firm=true.

KLEIN-INDIZIEN: {small_kw}
GROSS-INDIZIEN: {large_kw}

FELD is_gu — Bedeutung
true = Bauauftragnehmer / GU / Baufirma (NICHT Einzelhandels-Betreiber).
Auch true bei: Generalunternehmer, GU, Bauunternehmen mit Gewerbe- UND Einzelhandelsbau.

FELD has_retail_context — Bedeutung
true = Markt-/Filial-/Einzelhandels-Bezug: Referenzen, Fotos, Auftraggeber, Karriere-Stellen.
false nur wenn: nur Wohn-/Bürobau ohne jeden Einzelhandels-/Retail-Bezug.

IM ZWEIFEL: FOR TRUE wenn Bau/GU + Einzelhandel/Retail — FOR FALSE nur bei klarem Betreiber/Portal.

HILFS-SCHLÜSSELWÖRTER (nicht alle müssen vorkommen)
[GU — optional]
{gu_kw}

[RETAIL / FILIALBAU / PROJEKTE]
{retail_kw}

[SIECI als Projekt]
{chain_kw}

[ODRZUĆ wenn dominiert]
{neg_kw}

BEISPIELE
✓ JA ohne Wort GU: „Filialbau seit 1990" + Galerie mit Rewe/Aldi-Fotos und „Neubau Filiale Dresden"
✓ JA: „Referenzprojekte: Kaufland Umbau Halle, Penny Neubau"
✓ JA: alt-Text „Innenansicht Rewe Markt nach Umbau" auf Startseite
✓ JA klein: „Familienunternehmen Filialbau" + 45 Mitarbeiter + Rewe-Referenz → is_small_firm=true
✓ JA (Wijco-Typ): „Generalunternehmer Gewerbe- und Einzelhandelsbau", Karriere: 
  „Auftraggeber Netto Marken-Discount", Teil der Groep aber regionale GmbH → 
  is_gu=true, has_retail_context=true, matched_chains=[netto], is_small_firm=true
✗ NEIN groß: STRABAG SE, weltweit 77.000 Mitarbeiter → is_small_firm=false
✗ NEIN: „REWE Markt — Öffnungszeiten, Prospekt" (Betreiber)
✗ NEIN: „Ladenbau Büros, Praxen, Hotels" ohne ein einziges Marktprojekt
✗ NEIN: Zeitungsartikel über Baustelle ohne Firmenwebsite der Baufirma

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

EINGABE
Firma: {company_name}
Webseite: {website}

AUSZUG
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
(Aldi, Rewe, Edeka, Lidl, Netto, Penny, Kaufland als Projekt-Referenz).
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
• handelsketten → nur Kleinbuchstaben, kommagetrennt: rewe, aldi, edeka, lidl, netto, penny, kaufland — oder ""
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
