# -*- coding: utf-8 -*-
"""
Słowniki GU / Filialbau — kampania bundesweit (całe Niemcy).
Frazy Serper per Bundesland; wspólne słowniki www z de_ost_keywords.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_here = Path(__file__).resolve().parent
_ost_kw_path = _here / "de_ost_keywords.py"
if not _ost_kw_path.is_file():
    _ost_kw_path = _here.parent / "Niemcy wschodnie sklepy" / "de_ost_keywords.py"
_spec = importlib.util.spec_from_file_location("_de_ost_keywords", _ost_kw_path)
_ost = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_ost)

GU_ROLE_KEYWORDS = _ost.GU_ROLE_KEYWORDS
RETAIL_CHAIN_KEYWORDS = _ost.RETAIL_CHAIN_KEYWORDS
REQUIRED_RETAIL_CHAIN_KEYWORDS = _ost.REQUIRED_RETAIL_CHAIN_KEYWORDS
RETAIL_BUILD_KEYWORDS = _ost.RETAIL_BUILD_KEYWORDS
RETAIL_TRADE_ACTIVITY_KEYWORDS = _ost.RETAIL_TRADE_ACTIVITY_KEYWORDS
RETAIL_HOCHBAU_CORE_KEYWORDS = _ost.RETAIL_HOCHBAU_CORE_KEYWORDS
RETAIL_REFERENCE_KEYWORDS = _ost.RETAIL_REFERENCE_KEYWORDS
RETAIL_URL_PRIORITY_KEYWORDS = _ost.RETAIL_URL_PRIORITY_KEYWORDS
IMPRESSUM_GUESS_PATHS = _ost.IMPRESSUM_GUESS_PATHS
RETAIL_CONTACT_LINK_KEYWORDS = _ost.RETAIL_CONTACT_LINK_KEYWORDS
SERPER_POSITIVE_TERMS = _ost.SERPER_POSITIVE_TERMS
SERPER_NEGATIVE_TERMS = _ost.SERPER_NEGATIVE_TERMS
LARGE_COMPANY_DOMAINS_EXTRA = _ost.LARGE_COMPANY_DOMAINS_EXTRA
LARGE_COMPANY_NAME_MARKERS_EXTRA = _ost.LARGE_COMPANY_NAME_MARKERS_EXTRA
SMALL_COMPANY_PAGE_MARKERS_EXTRA = _ost.SMALL_COMPANY_PAGE_MARKERS_EXTRA
SMALL_COMPANY_DISCOVERY_TERMS_EXTRA = _ost.SMALL_COMPANY_DISCOVERY_TERMS_EXTRA

# Geo wyłączone w scraperze — puste / ogólne (kompatybilność importów)
DE_OST_PLACE_MARKERS: tuple[str, ...] = ()
DE_OST_REGION_KEYWORDS = (
    "deutschland",
    "bundesrepublik",
    "bundesweit",
)
DE_OST_RURAL_HINTS = _ost.DE_OST_RURAL_HINTS

RETAIL_CHAINS_ROTATION = (
    "Aldi",
    "Rewe",
    "Edeka",
    "Netto",
    "Penny",
    "Kaufland",
    "Norma",
)

TERM_TEMPLATES = (
    "Generalunternehmer Filialbau {city} {chain} Referenzprojekte",
    "Generalunternehmer Ladenbau {city} {land} {chain} Neubau",
    "GU Hochbau Supermarktbau {city} {chain} regional",
    "Generalunternehmer Einzelhandelsbau {city} Familienunternehmen",
    "Generalunternehmer {city} Filialumbau {chain}",
    "GU Gewerbebau {city} Discounter {chain} Referenz",
)

# Krótsze frazy Serper — każda musi zawierać Generalunternehmer lub GU
SIMPLE_TERM_TEMPLATES = (
    "Generalunternehmer Filialbau {city}",
    "Generalunternehmer {city}",
    "GU Hochbau {city}",
    "Generalunternehmer Einzelhandel {city}",
    "Generalunternehmer Supermarktbau {city}",
    "GU Gewerbebau {city}",
    "Komplettgeneralunternehmer {city}",
    "Generalunternehmer Ladenbau {city}",
)

BUNDESLAND_CONFIG: dict[str, dict] = {
    "Nordrhein-Westfalen": {
        "short": "NRW",
        "cities": (
            "Düsseldorf",
            "Köln",
            "Dortmund",
            "Essen",
            "Duisburg",
            "Bochum",
            "Wuppertal",
            "Bielefeld",
            "Bonn",
            "Münster",
        ),
    },
    "Bayern": {
        "short": "BY",
        "cities": (
            "München",
            "Nürnberg",
            "Augsburg",
            "Regensburg",
            "Würzburg",
            "Ingolstadt",
            "Fürth",
            "Erlangen",
        ),
    },
    "Baden-Wuerttemberg": {
        "short": "BW",
        "cities": (
            "Stuttgart",
            "Mannheim",
            "Karlsruhe",
            "Freiburg",
            "Heidelberg",
            "Ulm",
            "Heilbronn",
            "Pforzheim",
        ),
    },
    "Niedersachsen": {
        "short": "NI",
        "cities": (
            "Hannover",
            "Braunschweig",
            "Oldenburg",
            "Osnabrück",
            "Wolfsburg",
            "Göttingen",
        ),
    },
    "Hessen": {
        "short": "HE",
        "cities": (
            "Frankfurt",
            "Wiesbaden",
            "Kassel",
            "Darmstadt",
            "Offenbach",
            "Fulda",
        ),
    },
    "Sachsen": {
        "short": "SN",
        "cities": (
            "Dresden",
            "Leipzig",
            "Chemnitz",
            "Zwickau",
            "Plauen",
            "Görlitz",
        ),
    },
    "Rheinland-Pfalz": {
        "short": "RP",
        "cities": (
            "Mainz",
            "Ludwigshafen",
            "Koblenz",
            "Trier",
            "Kaiserslautern",
        ),
    },
    "Berlin": {
        "short": "BE",
        "cities": ("Berlin", "Potsdam"),
    },
    "Brandenburg": {
        "short": "BB",
        "cities": ("Potsdam", "Cottbus", "Frankfurt Oder", "Brandenburg Havel"),
    },
    "Schleswig-Holstein": {
        "short": "SH",
        "cities": ("Kiel", "Lübeck", "Flensburg", "Neumünster"),
    },
    "Thueringen": {
        "short": "TH",
        "cities": ("Erfurt", "Jena", "Gera", "Weimar", "Gotha"),
    },
    "Sachsen-Anhalt": {
        "short": "ST",
        "cities": ("Magdeburg", "Halle", "Dessau", "Wittenberg"),
    },
    "Mecklenburg-Vorpommern": {
        "short": "MV",
        "cities": ("Rostock", "Schwerin", "Stralsund", "Neubrandenburg"),
    },
    "Hamburg": {
        "short": "HH",
        "cities": ("Hamburg",),
    },
    "Bremen": {
        "short": "HB",
        "cities": ("Bremen", "Bremerhaven"),
    },
    "Saarland": {
        "short": "SL",
        "cities": ("Saarbrücken", "Neunkirchen", "Homburg"),
    },
}

# Całe Niemcy (16 Bundesländer)
ALL_BUNDESLAENDER: tuple[str, ...] = tuple(BUNDESLAND_CONFIG.keys())
DEFAULT_ACTIVE_BUNDESLAENDER: list[str] = list(ALL_BUNDESLAENDER)

CAMPAIGN_ACTIVE_BUNDESLAENDER: list[str] = list(DEFAULT_ACTIVE_BUNDESLAENDER)

# Więcej fraz Serper przy kampanii bundesweit (unlimited API w pipeline GHA)
BUNDESWEIT_MAX_DISCOVERY_TERMS = 2400


def default_max_discovery_terms_for(active: list[str] | None = None) -> int:
    n = len(resolve_active_bundeslaender(active))
    if n <= 1:
        return 120
    if n <= 3:
        return 360
    return BUNDESWEIT_MAX_DISCOVERY_TERMS


def _normalize_land_key(name: str) -> str:
    n = (name or "").strip()
    aliases = {
        "nrw": "Nordrhein-Westfalen",
        "by": "Bayern",
        "bw": "Baden-Wuerttemberg",
        "baden-württemberg": "Baden-Wuerttemberg",
        "baden-wuerttemberg": "Baden-Wuerttemberg",
        "ni": "Niedersachsen",
        "he": "Hessen",
        "sn": "Sachsen",
        "rp": "Rheinland-Pfalz",
        "be": "Berlin",
        "bb": "Brandenburg",
        "sh": "Schleswig-Holstein",
        "th": "Thueringen",
        "thüringen": "Thueringen",
        "st": "Sachsen-Anhalt",
        "mv": "Mecklenburg-Vorpommern",
        "hh": "Hamburg",
        "hb": "Bremen",
        "sl": "Saarland",
    }
    low = n.lower()
    if low in aliases:
        return aliases[low]
    for key in BUNDESLAND_CONFIG:
        if key.lower() == low:
            return key
    return n


def resolve_active_bundeslaender(names: list[str] | None = None) -> list[str]:
    if not names:
        return list(CAMPAIGN_ACTIVE_BUNDESLAENDER)
    out: list[str] = []
    for raw in names:
        for part in str(raw).replace(";", ",").split(","):
            key = _normalize_land_key(part)
            if key in BUNDESLAND_CONFIG and key not in out:
                out.append(key)
    return out or list(DEFAULT_ACTIVE_BUNDESLAENDER)


def _append_unique_term(terms: list[str], seen: set[str], text: str, *, max_terms: int) -> bool:
    t = (text or "").strip()
    if not t or t in seen:
        return False
    seen.add(t)
    terms.append(t)
    return len(terms) >= max_terms


def build_discovery_terms(
    active: list[str] | None = None, *, max_terms: int | None = None
) -> list[str]:
    lands = resolve_active_bundeslaender(active)
    if max_terms is None:
        max_terms = default_max_discovery_terms_for(lands)
    seen: set[str] = set()
    terms: list[str] = []
    chain_i = 0
    for land in lands:
        cfg = BUNDESLAND_CONFIG[land]
        cities = cfg["cities"]
        for city in cities:
            for tmpl in SIMPLE_TERM_TEMPLATES:
                if _append_unique_term(
                    terms, seen, tmpl.format(city=city), max_terms=max_terms
                ):
                    return terms
        for city in cities:
            for tmpl in TERM_TEMPLATES:
                chain = RETAIL_CHAINS_ROTATION[chain_i % len(RETAIL_CHAINS_ROTATION)]
                chain_i += 1
                if _append_unique_term(
                    terms,
                    seen,
                    tmpl.format(city=city, land=land, chain=chain),
                    max_terms=max_terms,
                ):
                    return terms
    if len(lands) >= 10:
        for raw in (
            "Generalunternehmer Filialbau Deutschland Referenzprojekte",
            "GU Supermarktbau Deutschland Rewe Aldi",
            "Generalunternehmer Einzelhandel Deutschland Neubau",
            "Komplettgeneralunternehmer Filialbau bundesweit",
            "Generalunternehmer Ladenbau Deutschland regional",
        ):
            if _append_unique_term(terms, seen, raw, max_terms=max_terms):
                return terms
    return terms


def build_landkreis_discovery_terms(active: list[str] | None = None) -> list[str]:
    """Frazy z Landkreis / Kreis — czwarta fala discovery."""
    lands = resolve_active_bundeslaender(active)
    seen: set[str] = set()
    terms: list[str] = []
    for land in lands:
        short = BUNDESLAND_CONFIG[land]["short"]
        for city in BUNDESLAND_CONFIG[land]["cities"][:6]:
            for raw in (
                f"Generalunternehmer Filialbau Landkreis {city}",
                f"Generalunternehmer Ladenbau {city} Kreis {short}",
                f"GU Gewerbebau {city} Landkreis",
            ):
                _append_unique_term(terms, seen, raw, max_terms=10_000)
        _append_unique_term(
            terms,
            seen,
            f"Generalunternehmer Filialbau {land} Landkreis",
            max_terms=10_000,
        )
    return terms


def build_places_discovery_terms(active: list[str] | None = None) -> list[str]:
    """Krótkie frazy pod endpoint /places Serper (bez suffixu regionu)."""
    lands = resolve_active_bundeslaender(active)
    seen: set[str] = set()
    terms: list[str] = []
    for land in lands:
        for city in BUNDESLAND_CONFIG[land]["cities"][:8]:
            for raw in (
                f"Generalunternehmer Filialbau {city}",
                f"Generalunternehmer Ladenbau {city}",
                f"GU Hochbau {city}",
                f"Generalunternehmer {city}",
            ):
                _append_unique_term(terms, seen, raw, max_terms=10_000)
        _append_unique_term(
            terms,
            seen,
            f"Generalunternehmer Filialbau {land}",
            max_terms=10_000,
        )
    return terms


def build_broad_discovery_terms(active: list[str] | None = None) -> list[str]:
    """Bardzo krótkie frazy — trzecia fala gdy primary + fallback dają za mało firm."""
    lands = resolve_active_bundeslaender(active)
    seen: set[str] = set()
    terms: list[str] = []
    for land in lands:
        short = BUNDESLAND_CONFIG[land]["short"]
        for city in BUNDESLAND_CONFIG[land]["cities"]:
            for raw in (
                f"Generalunternehmer {city}",
                f"Generalunternehmer {city} Bau",
                f"GU Filialbau {city}",
                f"Generalunternehmer Ladenbau {city}",
            ):
                _append_unique_term(terms, seen, raw, max_terms=10_000)
        for raw in (
            f"Generalunternehmer Filialbau {land}",
            f"Generalunternehmer Ladenbau {land}",
            f"GU Filialbau {short}",
            f"GU Supermarktbau {land}",
            f"Generalunternehmer Einzelhandel {land}",
        ):
            _append_unique_term(terms, seen, raw, max_terms=10_000)
    return terms


def build_fallback_terms(active: list[str] | None = None) -> list[str]:
    lands = resolve_active_bundeslaender(active)
    fb: list[str] = []
    for land in lands:
        short = BUNDESLAND_CONFIG[land]["short"]
        fb.extend(
            [
                f"Generalunternehmer Filialbau {land}",
                f"Generalunternehmer Hochbau Einzelhandel {short}",
                f"Generalunternehmer Ladenbau {land} Referenz",
                f"GU Supermarktbau {land} regional",
            ]
        )
    fb.extend(
        [
            "Generalunternehmer Filialbau Deutschland Referenz",
            "GU Hochbau Discounter Neubau Deutschland",
            "Komplettgeneralunternehmer Einzelhandel Filialumbau",
            "Generalunternehmer Handelsimmobilie Aldi Rewe",
        ]
    )
    seen: set[str] = set()
    out: list[str] = []
    for t in fb:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def build_region_suffix(active: list[str] | None = None) -> str:
    """Krótki suffix — długie query Serper prawie zawsze zwraca 0 wyników."""
    lands = resolve_active_bundeslaender(active)
    if len(lands) <= 1:
        return "Deutschland"
    # Faza 3: bundesweit (≥4 landy) — tylko „Deutschland”, bez skrótów NRW/BY/…
    if len(lands) >= 4:
        return "Deutschland"
    shorts = " ".join(BUNDESLAND_CONFIG[l]["short"] for l in lands[:4])
    return f"Deutschland {shorts}"


def configure_campaign_bundeslaender(
    module,
    names: list[str],
    *,
    max_discovery_terms: int | None = None,
) -> list[str]:
    """Ustawia aktywne landy i przeładowuje listy Serper na module scrapera."""
    global CAMPAIGN_ACTIVE_BUNDESLAENDER
    active = resolve_active_bundeslaender(names)
    if max_discovery_terms is None:
        max_discovery_terms = default_max_discovery_terms_for(active)
    CAMPAIGN_ACTIVE_BUNDESLAENDER = active
    module.CAMPAIGN_ACTIVE_BUNDESLAENDER = active
    module.SERPER_DISCOVERY_TERMS = build_discovery_terms(
        active, max_terms=max_discovery_terms
    )
    module.SERPER_DISCOVERY_FALLBACK_TERMS = build_fallback_terms(active)
    module.SERPER_DISCOVERY_BROAD_TERMS = build_broad_discovery_terms(active)
    module.SERPER_DISCOVERY_LANDKREIS_TERMS = build_landkreis_discovery_terms(active)
    module.SERPER_DISCOVERY_PLACES_TERMS = build_places_discovery_terms(active)
    module.SERPER_DISCOVERY_REGION_SUFFIX = build_region_suffix(active)
    return active


# Eksport domyślny (fala 1)
SERPER_DISCOVERY_TERMS = build_discovery_terms()
SERPER_DISCOVERY_FALLBACK_TERMS = build_fallback_terms()
SERPER_DISCOVERY_BROAD_TERMS = build_broad_discovery_terms()
SERPER_DISCOVERY_LANDKREIS_TERMS = build_landkreis_discovery_terms()
SERPER_DISCOVERY_PLACES_TERMS = build_places_discovery_terms()
SERPER_DISCOVERY_REGION_SUFFIX = build_region_suffix()
