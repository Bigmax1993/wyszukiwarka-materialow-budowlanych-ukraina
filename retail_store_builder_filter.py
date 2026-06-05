# -*- coding: utf-8 -*-
"""
Kampania DE Ost: Generalunternehmer (GU) / Bauunternehmen, które:
- stawiają sklepy / filie (Neubau, Filialbau), lub
- robią przebudowy / modernizacje marketów (Umbau, Revitalisierung).
Nie: sieci handlowe jako operator, urzędy, portale, czysta Bausanierung bez EH.
"""
from __future__ import annotations

from commercial_contact_filter import (
    is_non_commercial_contact,
    is_valid_commercial_company_contact,
)

RETAIL_OPERATOR_DOMAIN_MARKERS = (
    "shop.rewe",
    "rewe-markt",
    "rewe.de/filial",
    "filialfinder",
    "aldi-sued.de",
    "aldi-nord.de",
    "aldi.de",
    "penny.de",
    "kaufland.de",
    "lidl.de",
    "netto-online.de",
    "edeka.de",
    "rossmann.de",
    "dm.de",
    "tegut.de",
    "norma-online",
)

RETAIL_OPERATOR_PAGE_MARKERS = (
    "öffnungszeiten",
    "oeffnungszeiten",
    "wochenangebot",
    "prospekt",
    "filialfinder",
    "marktsuche",
    "jetzt einkaufen",
    "online bestellen",
    "lebensmittel online",
)

RETAIL_STORE_CONTEXT_MARKERS = (
    "filial",
    "laden",
    " markt",
    "markt ",
    "supermarkt",
    "discounter",
    "einzelhandel",
    "verbrauchermarkt",
    "nahversorger",
    "handelsimmobil",
    "lebensmittelmarkt",
    "food retail",
)

# Neubau / realizacja obiektów handlowych
RETAIL_STORE_BUILD_MARKERS = (
    "filialbau",
    "ladenbau",
    "marktbau",
    "supermarktbau",
    "supermarkt-neubau",
    "supermarktneubau",
    "einzelhandelsbau",
    "handelsbau",
    "filialneubau",
    "filialgebäude",
    "filialgebaude",
    "filialstandort",
    "einzelhandelsimmobilie",
    "handelsimmobilie",
    "handelsimmobilien",
    "handelsprojekt",
    "einzelhandelsprojekt",
    "filialprojekt",
    "discounterbau",
    "marktneubau",
    "markterweiterung",
    "ladenerweiterung",
)

# Przebudowa / modernizacja marketów i filii
RETAIL_STORE_UMBAU_MARKERS = (
    "filialumbau",
    "marktumbau",
    "supermarktumbau",
    "filialmodernisierung",
    "marktmodernisierung",
    "filialrevitalisierung",
    "marktrevitalisierung",
    "filialsanierung",
    "marktsanierung",
    "ladenumbau",
    "komplettumbau",
    "bestandsumbau",
    "filialumbau",
    "umbau supermarkt",
    "umbau discounter",
    "modernisierung supermarkt",
    "modernisierung filiale",
    "revitalisierung filiale",
    "revitalisierung markt",
    "umbau lebensmittelmarkt",
    "erneuerung filiale",
)

GU_BUILDER_MARKERS = (
    "generalunternehmer",
    "generalunternehmen",
    "komplettgeneralunternehmer",
    "hauptauftragnehmer",
    "totalunternehmer",
    "generalübernehmer",
    "generaluebernehmer",
    "gu-leistung",
    " gu ",
    "bauunternehmen",
    "bauunternehmung",
)

FILIALBAU_SPECIALIST_MARKERS = (
    "filialbau",
    "ladenbau",
    "marktbau",
    "supermarktbau",
    "einzelhandelsbau",
    "handelsbau",
    "handelsimmobilien",
)

# Galerie / zdjęcia projektów (bez osobnej sekcji „Portfolio”)
MARKET_PHOTO_GALLERY_MARKERS = (
    "bildergalerie",
    "fotogalerie",
    "projektbilder",
    "bauabbildungen",
    "impressionen",
    "einblicke",
    "foto",
    "fotos",
    "bild ",
    "bilder",
    "abbildung",
    "lightbox",
    "bildergalerie",
    "projektgalerie",
    "baustellenfotos",
    "baustellenbilder",
)

# Sekcja Referenzen / Portfolio (opcjonalna — wystarczą też zdjęcia/alt marketów)
PORTFOLIO_SECTION_MARKERS = (
    "referenzen",
    "referenzprojekt",
    "referenzprojekte",
    "referenzliste",
    "referenzobjekte",
    "portfolio",
    "projektübersicht",
    "projektuebersicht",
    "projektbeispiele",
    "unsere projekte",
    "bauprojekte",
    "objektübersicht",
    "objektuebersicht",
    "case study",
    "baustellenberichte",
    "realisierungen",
    "projektgalerie",
    "projektliste",
)

# Sieci / obiekty handlowe w portfolio (Pflicht: projekty MARKETÓW)
RETAIL_CHAIN_IN_PORTFOLIO_MARKERS = (
    "aldi nord",
    "aldi süd",
    "aldi sued",
    "aldi",
    "rewe",
    "kaufland",
    "lidl",
    "penny",
    "netto",
    "edeka",
    "norma",
    "tegut",
    "marktkauf",
    "nahkauf",
    "globus",
    "famila",
)

MARKET_PROJECT_IN_PORTFOLIO_MARKERS = (
    "supermarktprojekt",
    "marktprojekt",
    "filialprojekt",
    "einzelhandelsprojekt",
    "discounterprojekt",
    "referenzprojekt supermarkt",
    "referenzprojekt filiale",
    "referenzprojekt markt",
    "portfolio supermarkt",
    "portfolio filiale",
    "portfolio markt",
    "projekte supermarkt",
    "projekte filiale",
    "projekte discounter",
    "projekte einzelhandel",
    "referenz supermarkt",
    "referenz filiale",
    "referenz markt",
    "realisierte filialen",
    "realisierte märkte",
    "realisierte maerkte",
    "filialneubau",
    "marktneubau",
    "filialumbau",
    "marktumbau",
    "supermarktbau",
    "marktbau",
    "lebensmittelmarkt",
    "verbrauchermarkt",
    "nahversorger",
)

MEDIA_PUBLISHER_DOMAIN_MARKERS = (
    "hi-heute.de",
    "funkemedien",
    "verlag",
    "redaktion.",
    "business-news",
    "fachzeitung",
    "fachmedien",
    "presseportal",
    "nachrichten.",
    "news-medien",
    "magazin.",
    "branchennews",
    "branchenportal",
)

MEDIA_PUBLISHER_NAME_MARKERS = (
    "verlag ",
    " verlag",
    "redaktion",
    "fachmedium",
    "fachzeitschrift",
    "nachrichten",
    "news group",
    "business news",
    "business media",
    "pressemitteilung",
    "fachportal",
)

MEDIA_PUBLISHER_URL_PATH_MARKERS = (
    "/news/",
    "/nachrichten/",
    "/artikel/",
    "/newsletter/",
    "/magazin/",
    "/supermarkte_und_discounter",
)

PURE_RENOVATION_WITHOUT_STORE_BUILD = (
    "altbausanierung",
    "wohnsanierung",
    "denkmalsanierung",
    "komplettsanierung wohn",
    "wohnungsbau",
    "wohnungsmodernisierung",
)


def _blob(*parts: str) -> str:
    return " ".join((p or "").strip() for p in parts if (p or "").strip()).lower()


def _has_retail_store_context(low: str) -> bool:
    return any(m in low for m in RETAIL_STORE_CONTEXT_MARKERS)


def is_gu_or_retail_build_specialist(text: str) -> bool:
    low = (text or "").lower()
    if any(m in low for m in GU_BUILDER_MARKERS):
        return True
    return any(m in low for m in FILIALBAU_SPECIALIST_MARKERS)


def is_media_publisher_contact(
    *,
    url: str = "",
    email: str = "",
    name: str = "",
    text: str = "",
) -> bool:
    """True = medium / wydawca / portal branżowy, nie Bauunternehmen."""
    low = _blob(name, url, email, text)
    if any(m in low for m in MEDIA_PUBLISHER_NAME_MARKERS):
        return True
    url_low = (url or "").lower()
    if any(m in url_low for m in MEDIA_PUBLISHER_DOMAIN_MARKERS):
        return True
    if any(m in url_low for m in MEDIA_PUBLISHER_URL_PATH_MARKERS):
        return True
    email_low = (email or "").strip().lower()
    if email_low.startswith("redaktion@"):
        return True
    return False


def is_retail_store_operator_contact(
    *,
    url: str = "",
    email: str = "",
    text: str = "",
) -> bool:
    """True = operator sklepu, nie GU."""
    low = _blob(url, email, text)
    if any(m in low for m in RETAIL_OPERATOR_DOMAIN_MARKERS):
        if not any(
            b in low
            for b in (
                *RETAIL_STORE_BUILD_MARKERS,
                *RETAIL_STORE_UMBAU_MARKERS,
                *GU_BUILDER_MARKERS,
                *FILIALBAU_SPECIALIST_MARKERS,
            )
        ):
            return True
    if sum(1 for m in RETAIL_OPERATOR_PAGE_MARKERS if m in low) >= 2:
        if not any(
            b in low
            for b in (*RETAIL_STORE_BUILD_MARKERS, *RETAIL_STORE_UMBAU_MARKERS)
        ):
            return True
    return False


def _has_portfolio_section(low: str) -> bool:
    if _portfolio_negates_market_projects(low):
        return False
    return any(m in low for m in PORTFOLIO_SECTION_MARKERS)


def portfolio_negates_market_projects(text: str) -> bool:
    """„keine Supermarktprojekte”, „ohne Filialbau-Referenzen” itp."""
    low = (text or "").lower()
    return _portfolio_negates_market_projects(low)


def _portfolio_negates_market_projects(low: str) -> bool:
    """Jawna deklaracja braku projektów marketów — nie mylić z brakiem galerii www."""
    return any(
        x in low
        for x in (
            "keine supermarkt",
            "kein supermarkt",
            "ohne supermarkt",
            "nicht supermarkt",
            "keine filial",
            "kein filial",
            "ohne filial",
            "keine marktprojekte",
            "keine supermarktprojekte",
            "ohne einzelhandel",
            "keine einzelhandel",
        )
    )


def _has_market_photo_gallery_context(low: str) -> bool:
    """Zdjęcia / galeria z marketami (bez nagłówka Portfolio)."""
    if _portfolio_negates_market_projects(low):
        return False
    if not any(m in low for m in MARKET_PHOTO_GALLERY_MARKERS):
        return False
    return _has_retail_store_context(low) or any(
        chain in low for chain in RETAIL_CHAIN_IN_PORTFOLIO_MARKERS
    )


def _has_market_projects_evidence(low: str) -> bool:
    """
    Dowód projektów marketów na stronie: referencje, portfolio LUB zdjęcia/alt/src
    (np. Fotogalerie Rewe, Bild Supermarkt Neubau) — bez wymogu sekcji Portfolio.
    """
    if _portfolio_negates_market_projects(low):
        if not any(
            chain in low
            for chain in RETAIL_CHAIN_IN_PORTFOLIO_MARKERS
            if len(chain) >= 4
        ):
            return False
    if any(m in low for m in MARKET_PROJECT_IN_PORTFOLIO_MARKERS):
        return True
    for chain in sorted(RETAIL_CHAIN_IN_PORTFOLIO_MARKERS, key=len, reverse=True):
        if chain in low and (
            _has_portfolio_section(low)
            or "referenzen" in low
            or "referenzprojekt" in low
            or _has_market_photo_gallery_context(low)
            or is_gu_or_retail_build_specialist(low)
        ):
            return True
    if _has_market_photo_gallery_context(low):
        return True
    if _has_retail_store_context(low) and any(
        m in low
        for m in (
            "referenzprojekt",
            "referenzprojekte",
            "einzelhandelsprojekt",
            "filialprojekt",
            "marktprojekt",
            "supermarktprojekt",
            "discounterprojekt",
        )
    ):
        return True
    if _has_portfolio_section(low) and _has_retail_store_context(low):
        if ("portfolio" in low or "unsere projekte" in low or "bauprojekte" in low) and (
            "supermarkt" in low
            or "filial" in low
            or "discounter" in low
            or "einzelhandel" in low
            or "lebensmittelmarkt" in low
            or "verbrauchermarkt" in low
        ):
            return not _portfolio_negates_market_projects(low)
    return False


def has_market_project_evidence_on_website(text: str) -> bool:
    """Projekty niemieckich marketów: tekst, referencje lub zdjęcia (alt/src)."""
    return _has_market_projects_evidence((text or "").lower())


def has_retail_references_or_portfolio(text: str) -> bool:
    """Alias — ten sam warunek co has_market_project_evidence_on_website."""
    return has_market_project_evidence_on_website(text)


has_market_store_projects_portfolio = has_market_project_evidence_on_website


def mentions_retail_store_build_activity_core(text: str) -> bool:
    """GU / Filialbau + Neubau/Umbau marketów (bez wymogu Referenzen)."""
    low = (text or "").lower()
    if any(m in low for m in PURE_RENOVATION_WITHOUT_STORE_BUILD):
        if not _has_retail_store_context(low):
            return False
    if "bausanierung" in low and not _has_retail_store_context(low):
        if not any(m in low for m in FILIALBAU_SPECIALIST_MARKERS):
            return False
    if not is_gu_or_retail_build_specialist(low):
        return False
    if not _has_retail_store_context(low):
        return False
    has_neubau = any(m in low for m in RETAIL_STORE_BUILD_MARKERS)
    has_umbau = any(m in low for m in RETAIL_STORE_UMBAU_MARKERS)
    if "umbau" in low or "modernisierung" in low or "revitalisierung" in low:
        if _has_retail_store_context(low):
            has_umbau = True
    if has_neubau or has_umbau:
        return True
    return any(m in low for m in GU_BUILDER_MARKERS) and (
        "neubau" in low or "realis" in low or "erricht" in low
    )


def mentions_retail_store_build_activity(text: str) -> bool:
    """GU / Filialbau + Neubau/Umbau + opcjonalnie dowód projektów (Referenzen/Portfolio)."""
    low = (text or "").lower()
    if not mentions_retail_store_build_activity_core(low):
        return False
    if portfolio_negates_market_projects(low):
        return False
    if has_retail_references_or_portfolio(low):
        return True
    return mentions_retail_store_build_activity_core(low)


def is_loose_serper_discovery_candidate(
    *,
    email: str = "",
    url: str = "",
    name: str = "",
    text: str = "",
) -> bool:
    """
    Lżejszy filtr na etapie Serper (tytuł/snippet).
    Wymaga GU/Filialbau + kontekst EH; bez wymogu portfolio (to sprawdza www).
    """
    combined = _blob(name, url, email, text)
    if is_non_commercial_contact(email=email, url=url, name=name):
        return False
    if is_media_publisher_contact(email=email, url=url, name=name, text=combined):
        return False
    if is_retail_store_operator_contact(url=url, email=email, text=combined):
        return False
    if not is_valid_commercial_company_contact(email=email, url=url, name=name):
        return False
    return mentions_retail_store_build_activity_core(combined)


def is_valid_retail_store_builder_contact(
    *,
    email: str = "",
    url: str = "",
    name: str = "",
    text: str = "",
) -> bool:
    """GU / Bauunternehmen budujące lub przebudowujące sklepy i markety."""
    combined = _blob(name, url, email, text)
    if is_non_commercial_contact(email=email, url=url, name=name):
        return False
    if is_media_publisher_contact(email=email, url=url, name=name, text=combined):
        return False
    if is_retail_store_operator_contact(url=url, email=email, text=combined):
        return False
    if not is_valid_commercial_company_contact(email=email, url=url, name=name):
        return False
    if portfolio_negates_market_projects(combined):
        return False
    return mentions_retail_store_build_activity_core(combined)


def is_cache_contact_not_store_builder(place_url: str, info: dict | None) -> bool:
    if not isinstance(info, dict):
        return True
    email = (info.get("email_target") or "").strip()
    if not email:
        found = (info.get("emails_found") or "").strip()
        if found:
            email = found.split(",")[0].strip()
    url = (place_url or info.get("official_website") or "").strip()
    name = (
        info.get("company_name_clean")
        or info.get("company_name")
        or info.get("company_name_raw")
        or ""
    ).strip()
    extra = " ".join(
        str(info.get(k) or "")
        for k in (
            "verification_reason",
            "page_snippet",
            "serper_title",
            "serper_snippet",
            "retail_chains",
            "retail_chains_found",
        )
    )
    return not is_valid_retail_store_builder_contact(
        email=email, url=url, name=name, text=extra
    )
