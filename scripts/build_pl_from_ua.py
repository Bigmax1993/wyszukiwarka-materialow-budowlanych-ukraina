# -*- coding: utf-8 -*-
"""Generator modułów kampanii PL z forków UA."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

COMMON_REPLACEMENTS: list[tuple[str, str]] = [
    ("ua_oblast_keywords", "pl_wojewodztwo_keywords"),
    ("ua_oblast_rotation", "pl_wojewodztwo_rotation"),
    ("ua_materialy_supplier_filter", "pl_materialy_supplier_filter"),
    ("ua_materialy_inquiry_email_uk", "pl_materialy_inquiry_email_pl"),
    ("ua_campaign_keyword_profile", "pl_campaign_keyword_profile"),
    ("ua_claude_page_verify", "pl_claude_page_verify"),
    ("ua_claude_prompts", "pl_claude_prompts"),
    ("ua_claude_inquiry_email", "pl_claude_inquiry_email"),
    ("ua_page_verify", "pl_page_verify"),
    ("ua_materialy_scraper", "pl_materialy_scraper"),
    ("ua_materialy", "pl_materialy"),
    ("UA materialy", "PL materialy"),
    ("UA materiały", "PL materiały"),
    ("UA_OBLASTS", "PL_WOJEWODZTWA"),
    ("OBLAST_CONFIG", "WOJEWODZTWO_CONFIG"),
    ("ALL_OBLASTS", "ALL_WOJEWODZTWA"),
    ("DEFAULT_ACTIVE_OBLASTS", "DEFAULT_ACTIVE_WOJEWODZTWA"),
    ("CAMPAIGN_ACTIVE_OBLASTS", "CAMPAIGN_ACTIVE_WOJEWODZTWA"),
    ("OBLAST_ROTATION_ORDER", "WOJEWODZTWO_ROTATION_ORDER"),
    ("configure_campaign_oblasts", "configure_campaign_wojewodztwa"),
    ("resolve_active_oblasts", "resolve_active_wojewodztwa"),
    ("_normalize_oblast_key", "_normalize_wojewodztwo_key"),
    ("peek_next_oblast", "peek_next_wojewodztwo"),
    ("DEFAULT_MIN_CONTACTS_SINGLE_OBLAST", "DEFAULT_MIN_CONTACTS_SINGLE_WOJEWODZTWO"),
    ("ua_materialy_oblast_rotation.json", "pl_materialy_wojewodztwo_rotation.json"),
    ("UA_OBLAST_ROTATION_START", "PL_WOJEWODZTWO_ROTATION_START"),
    ("apply_ua_run_config_extras", "apply_pl_run_config_extras"),
    ("def apply_ua_run_config_extras", "def apply_pl_run_config_extras"),
    ("rotation_start_date", "rotation_start_date"),
    ("--rotate-oblast", "--rotate-wojewodztwo"),
    ("rotate_oblast", "rotate_wojewodztwo"),
    ("--oblast", "--wojewodztwo"),
    ("send_email_ua_materialy", "send_email_pl_materialy"),
    ("get_email_attachments_ua_materialy", "get_email_attachments_pl_materialy"),
    ("_build_ua_materialy_outgoing_email", "_build_pl_materialy_outgoing_email"),
    ("_send_ua_materialy_via_smtp", "_send_pl_materialy_via_smtp"),
    ("FIXED_MATERIAL_INQUIRY_UK", "FIXED_MATERIAL_INQUIRY_PL"),
    ("build_fixed_material_inquiry_uk", "build_fixed_material_inquiry_pl"),
    ("build_inquiry_signature_uk", "build_inquiry_signature_pl"),
    ("build_personalized_inquiry_email_prompt_uk", "build_personalized_inquiry_email_prompt_pl"),
    ("claude_generate_inquiry_email_ua", "claude_generate_inquiry_email_pl"),
    ('SERPER_COUNTRY = "ua"', 'SERPER_COUNTRY = "pl"'),
    ('SERPER_LANGUAGE = "uk"', 'SERPER_LANGUAGE = "pl"'),
    ('COUNTRY_RESTRICTION = "UA"', 'COUNTRY_RESTRICTION = "PL"'),
    ('CUSTOM_EMAIL_LANG = "uk"', 'CUSTOM_EMAIL_LANG = "pl"'),
    ('CUSTOM_EMAIL_CITY = "Україна"', 'CUSTOM_EMAIL_CITY = "Polska"'),
    ('INQUIRY_REGION_UA = "Україна"', 'INQUIRY_REGION_PL = "Polska"'),
    ('DELIVERY_ADDRESS_UA = "Україна"', 'DELIVERY_ADDRESS_PL = "Polska"'),
    ('MATERIAL_CATEGORIES_UA =', 'MATERIAL_CATEGORIES_PL ='),
    ("REGION_CENTER_LAT = 48.3794", "REGION_CENTER_LAT = 52.0693"),
    ("REGION_CENTER_LON = 31.1656", "REGION_CENTER_LON = 19.4803"),
    ('EMAIL_SUBJECT_TEMPLATE = "Запит щодо постачання будівельних матеріалів"', 'EMAIL_SUBJECT_TEMPLATE = "Zapytanie o dostawę materiałów budowlanych"'),
    ("not in UA_OBLASTS", "not in PL_WOJEWODZTWA"),
    ("in UA_OBLASTS", "in PL_WOJEWODZTWA"),
    ("UA_COUNTRY_HINTS", "PL_COUNTRY_HINTS"),
    ("UA_PLACE_MARKERS", "PL_PLACE_MARKERS"),
    ("UA_REGION_KEYWORDS", "PL_REGION_KEYWORDS"),
    ("UA_RURAL_HINTS", "PL_RURAL_HINTS"),
    ("obwód", "województwo"),
    ("obwody", "województwa"),
    ("Obwód", "Województwo"),
    ("cała Ukraina", "cała Polska"),
    ("obwodów", "województw"),
    ("obwodu", "województwa"),
    ("Rotacja obwodów", "Rotacja województw"),
    ("Aktywne obwody", "Aktywne województwa"),
    ("1 obwód", "1 województwo"),
    ('".ua"', '".pl"'),
    ('"olx.ua"', '"olx.pl"'),
    ('"prom.ua"', '"allegro.pl"'),
]

UK_TO_PL_TEXT: list[tuple[str, str]] = [
    ("україн", "polsk"),
    ("Україн", "Polsk"),
    ("Україна", "Polska"),
    ("ukraiński", "polski"),
    ("ukraińsku", "polsku"),
    ("ukraińskim", "polskim"),
    ("obwód", "województwo"),
    ("oblast", "województwo"),
    ("Постачальник", "Dostawca"),
    ("цемент, пісок", "cement, piasek"),
    ("будматеріали", "materiały budowlane"),
    ("будівельні", "budowlane"),
    ("Медіа", "Media"),
    ("Портал", "Portal"),
    ("Держустанова", "Urząd"),
    ("Банк", "Bank"),
    ("Архітектурне бюро", "Biuro architektoniczne"),
    ("Дизайн інтер'єру", "Wykończenia wnętrz"),
    ("Ремонт під ключ", "Remont pod klucz"),
    ("Підрядник без продажу", "Wykonawca bez sprzedaży"),
    ("Оголошення", "Ogłoszenie"),
    ("Інше", "Inne"),
]

FOREIGN_TLD = (
    '_FOREIGN_TLD_SUFFIXES = (\n'
    '    ".ua",\n'
    '    ".de",\n'
    '    ".ru",\n'
    '    ".by",\n'
    '    ".cz",\n'
    '    ".sk",\n'
    ')'
)

PL_WOJEWODZTWA_BLOCK = '''PL_WOJEWODZTWA = [
    "mazowieckie", "malopolskie", "slaskie", "wielkopolskie", "dolnoslaskie",
    "pomorskie", "lodzkie", "zachodniopomorskie", "lubelskie", "podkarpackie",
    "kujawsko-pomorskie", "warminsko-mazurskie", "swietokrzyskie", "podlaskie",
    "lubuskie", "opolskie",
]'''

PL_COUNTRY_HINTS = '''PL_COUNTRY_HINTS = [
    "polska",
    "poland",
    "polski",
    ".pl/",
    "warszawa",
    "kraków",
    "krakow",
    "wrocław",
    "wroclaw",
    "gdańsk",
    "gdansk",
    "poznań",
    "poznan",
    "łódź",
    "lodz",
]'''

WOJEWODZTWO_CONFIG_BLOCK = '''WOJEWODZTWO_CONFIG: dict[str, dict] = {
    "mazowieckie": {
        "short": "MZ",
        "cities": ("Warszawa", "Radom", "Płock", "Siedlce", "Ostrołęka", "Pruszków"),
    },
    "malopolskie": {
        "short": "MA",
        "cities": ("Kraków", "Tarnów", "Nowy Sącz", "Oświęcim", "Chrzanów", "Wieliczka"),
    },
    "slaskie": {
        "short": "SL",
        "cities": ("Katowice", "Częstochowa", "Sosnowiec", "Gliwice", "Zabrze", "Bielsko-Biała"),
    },
    "wielkopolskie": {
        "short": "WP",
        "cities": ("Poznań", "Kalisz", "Konin", "Piła", "Leszno", "Gniezno"),
    },
    "dolnoslaskie": {
        "short": "DS",
        "cities": ("Wrocław", "Wałbrzych", "Legnica", "Jelenia Góra", "Lubin", "Głogów"),
    },
    "pomorskie": {
        "short": "PM",
        "cities": ("Gdańsk", "Gdynia", "Słupsk", "Tczew", "Wejherowo", "Starogard Gdański"),
    },
    "lodzkie": {
        "short": "LD",
        "cities": ("Łódź", "Piotrków Trybunalski", "Pabianice", "Zgierz", "Skierniewice", "Kutno"),
    },
    "zachodniopomorskie": {
        "short": "ZP",
        "cities": ("Szczecin", "Koszalin", "Stargard", "Kołobrzeg", "Świnoujście", "Police"),
    },
    "lubelskie": {
        "short": "LU",
        "cities": ("Lublin", "Zamość", "Chełm", "Biała Podlaska", "Puławy", "Świdnik"),
    },
    "podkarpackie": {
        "short": "PK",
        "cities": ("Rzeszów", "Przemyśl", "Stalowa Wola", "Mielec", "Tarnobrzeg", "Krosno"),
    },
    "kujawsko-pomorskie": {
        "short": "KP",
        "cities": ("Bydgoszcz", "Toruń", "Włocławek", "Grudziądz", "Inowrocław", "Brodnica"),
    },
    "warminsko-mazurskie": {
        "short": "WN",
        "cities": ("Olsztyn", "Elbląg", "Ełk", "Iława", "Ostróda", "Giżycko"),
    },
    "swietokrzyskie": {
        "short": "SK",
        "cities": ("Kielce", "Ostrowiec Świętokrzyski", "Starachowice", "Sandomierz", "Końskie"),
    },
    "podlaskie": {
        "short": "PD",
        "cities": ("Białystok", "Suwałki", "Łomża", "Augustów", "Hajnówka", "Grajewo"),
    },
    "lubuskie": {
        "short": "LB",
        "cities": ("Zielona Góra", "Gorzów Wielkopolski", "Żary", "Nowa Sól", "Świebodzin"),
    },
    "opolskie": {
        "short": "OP",
        "cities": ("Opole", "Kędzierzyn-Koźle", "Nysa", "Brzeg", "Kluczbork", "Prudnik"),
    },
}'''

POLISH_KEYWORDS_HEADER = '''SUPPLIER_ROLE_KEYWORDS: tuple[str, ...] = (
    "materiały budowlane",
    "hurtownia budowlana",
    "skład budowlany",
    "hurtownia materiałów budowlanych",
    "dostawca materiałów budowlanych",
    "dystrybutor",
    "producent",
    "sprzedaż hurtowa",
    "sklep budowlany",
    "market budowlany",
    "baza materiałów budowlanych",
    "dostawa materiałów",
)

MATERIAL_CATEGORY_KEYWORDS: tuple[str, ...] = (
    "cement",
    "piasek",
    "żwir",
    "kruszywo",
    "cegła",
    "bloczek",
    "gazobeton",
    "styropian",
    "wełna mineralna",
    "płyta gipsowa",
    "armatura",
    "stal zbrojeniowa",
    "drewno",
    "płyta osb",
    "blacha",
    "dachówka",
    "farba",
    "tynk",
    "zaprawa",
    "beton",
    "wylewka",
    "płytki",
    "hydroizolacja",
    "styropian grafitowy",
)

MATERIAL_CATEGORIES_ROTATION = (
    "cement",
    "piasek",
    "żwir",
    "cegła",
    "bloczek",
    "armatura",
    "styropian",
    "płytki",
    "płyta gipsowa",
    "drewno",
    "stal",
    "dachówka",
)

CHAIN_SIMPLE_TERM_TEMPLATES = (
    "materiały budowlane {city} {material} hurt",
    "hurtownia budowlana {city} {material}",
    "skład budowlany {city} {material}",
    "sklep budowlany {city} {material}",
    "dostawca {material} {city}",
    "hurtownia {material} {city}",
    "baza materiałów budowlanych {city} {material}",
    "market budowlany {city} {material}",
)

TERM_TEMPLATES = (
    "materiały budowlane {city} {oblast} {material} dostawa",
    "hurtownia materiałów budowlanych {city} {material}",
    "producent {material} {city} {oblast}",
    "dystrybutor materiałów budowlanych {city} {material}",
    "sprzedaż hurtowa {material} {city}",
    "materiały budowlane {oblast} {city} {material}",
)

SERPER_NEGATIVE_TERMS = (
    "wiadomości",
    "blog",
    "forum",
    "oferty pracy",
    "praca",
    "urząd",
    "ministerstwo",
    "portal",
    "encyklopedia",
    "wikipedia",
    "olx ogłoszenie",
    "używane",
    "remont mieszkań",
    "wykończenia wnętrz",
    "biuro architektoniczne",
    "projektowanie domów",
    "bank",
    "ubezpieczenia",
    "kredyt",
    "salon samochodowy",
    "restauracja",
    "hotel",
    "turystyka",
)

PL_REGION_KEYWORDS = (
    "polska",
    "poland",
    "polski",
)

COUNTRYWIDE_MAX_DISCOVERY_TERMS = 1500

'''


def apply_replacements(text: str, extra: list[tuple[str, str]] | None = None) -> str:
    for old, new in COMMON_REPLACEMENTS + (extra or []):
        text = text.replace(old, new)
    for old, new in UK_TO_PL_TEXT:
        text = text.replace(old, new)
    return text


def fork_file(src_name: str, dst_name: str, *, post: callable | None = None) -> None:
    src = ROOT / src_name
    dst = ROOT / dst_name
    text = apply_replacements(src.read_text(encoding="utf-8"))
    if post:
        text = post(text)
    dst.write_text(text, encoding="utf-8")
    print(f"Wrote {dst_name} ({dst.stat().st_size} bytes)")


def build_keywords() -> None:
    src = ROOT / "ua_oblast_keywords.py"
    text = src.read_text(encoding="utf-8")
    # Replace header through OBLAST_CONFIG
    start = text.index("SUPPLIER_ROLE_KEYWORDS")
    end = text.index("ALL_OBLASTS")
    tail = text[end:]
    tail = apply_replacements(tail)
    tail = tail.replace("ALL_WOJEWODZTWA", "ALL_WOJEWODZTWA")
    tail = re.sub(
        r"ALL_WOJEWODZTWA: tuple\[str, \.\.\.\] = tuple\(WOJEWODZTWO_CONFIG\.keys\(\)\)",
        "ALL_WOJEWODZTWA: tuple[str, ...] = tuple(WOJEWODZTWO_CONFIG.keys())",
        tail,
        count=1,
    )
    tail = tail.replace("DEFAULT_ACTIVE_WOJEWODZTWA", "DEFAULT_ACTIVE_WOJEWODZTWA")
    tail = tail.replace("CAMPAIGN_ACTIVE_WOJEWODZTWA", "CAMPAIGN_ACTIVE_WOJEWODZTWA")
    tail = tail.replace("BUNDESLAND_CONFIG = WOJEWODZTWO_CONFIG", "BUNDESLAND_CONFIG = WOJEWODZTWO_CONFIG")
    tail = tail.replace("ALL_BUNDESLAENDER = ALL_WOJEWODZTWA", "ALL_BUNDESLAENDER = ALL_WOJEWODZTWA")
    tail = tail.replace("DEFAULT_ACTIVE_BUNDESLAENDER = DEFAULT_ACTIVE_WOJEWODZTWA", "DEFAULT_ACTIVE_BUNDESLAENDER = DEFAULT_ACTIVE_WOJEWODZTWA")
    tail = tail.replace("CAMPAIGN_ACTIVE_BUNDESLAENDER = CAMPAIGN_ACTIVE_WOJEWODZTWA", "CAMPAIGN_ACTIVE_BUNDESLAENDER = CAMPAIGN_ACTIVE_WOJEWODZTWA")
    tail = tail.replace("COUNTRYWIDE_MAX_DISCOVERY_TERMS = 2400", "COUNTRYWIDE_MAX_DISCOVERY_TERMS = 1500")
    tail = tail.replace('return "Україна"', 'return "Polska"')
    tail = tail.replace('return f"Україна {shorts}"', 'return f"Polska {shorts}"')
    tail = tail.replace("configure_campaign_wojewodztwa", "configure_campaign_wojewodztwa")
    # countrywide templates in build_discovery_terms
    tail = tail.replace(
        '"будматеріали Україна {material} опт"',
        '"materiały budowlane Polska {material} hurt"',
    )
    tail = tail.replace(
        '"оптовий склад будматеріалів Україна {material}"',
        '"hurtownia materiałów budowlanych Polska {material}"',
    )
    tail = tail.replace(
        '"постачальник {material} Україна"',
        '"dostawca {material} Polska"',
    )
    tail = tail.replace(
        '"будівельні матеріали Україна {material} доставка"',
        '"materiały budowlane Polska {material} dostawa"',
    )
    tail = tail.replace(
        '"будмаркет Україна {material}"',
        '"market budowlany Polska {material}"',
    )
    tail = re.sub(
        r"if len\(oblasts\) >= 10:",
        "if len(oblasts) >= 8:",
        tail,
        count=1,
    )
    # normalize aliases function body - replace Ukrainian aliases with Polish
    norm = '''def _normalize_wojewodztwo_key(name: str) -> str:
    n = (name or "").strip()
    aliases = {
        "mazowieckie": "mazowieckie",
        "mazowsze": "mazowieckie",
        "warszawa": "mazowieckie",
        "malopolskie": "malopolskie",
        "małopolskie": "malopolskie",
        "krakow": "malopolskie",
        "kraków": "malopolskie",
        "slaskie": "slaskie",
        "śląskie": "slaskie",
        "katowice": "slaskie",
        "wielkopolskie": "wielkopolskie",
        "poznan": "wielkopolskie",
        "poznań": "wielkopolskie",
        "dolnoslaskie": "dolnoslaskie",
        "dolnośląskie": "dolnoslaskie",
        "wroclaw": "dolnoslaskie",
        "wrocław": "dolnoslaskie",
    }
    low = n.lower()
    if low in aliases:
        return aliases[low]
    for key in WOJEWODZTWO_CONFIG:
        if key.lower() == low:
            return key
    return n
'''
    tail = re.sub(
        r"def _normalize_wojewodztwo_key\(name: str\) -> str:.*?return n\n",
        norm + "\n",
        tail,
        count=1,
        flags=re.DOTALL,
    )
    out = (
        "# -*- coding: utf-8 -*-\n"
        '"""\n'
        "Słowniki kampanii PL — hurtownie / składy / producenci materiałów budowlanych.\n"
        "Frazy Serper per województwo; rotacja kategorii materiałów.\n"
        '"""\n'
        "from __future__ import annotations\n\n"
        + POLISH_KEYWORDS_HEADER
        + "\n"
        + WOJEWODZTWO_CONFIG_BLOCK
        + "\n\n"
        + tail
    )
    out = apply_replacements(out)
    (ROOT / "pl_wojewodztwo_keywords.py").write_text(out, encoding="utf-8")
    print(f"Wrote pl_wojewodztwo_keywords.py ({(ROOT / 'pl_wojewodztwo_keywords.py').stat().st_size} bytes)")


def post_rotation(text: str) -> str:
    order = '''WOJEWODZTWO_ROTATION_ORDER: tuple[str, ...] = (
    "mazowieckie",
    "slaskie",
    "malopolskie",
    "wielkopolskie",
    "dolnoslaskie",
    "pomorskie",
    "lodzkie",
    "zachodniopomorskie",
    "lubelskie",
    "podkarpackie",
    "kujawsko-pomorskie",
    "warminsko-mazurskie",
    "swietokrzyskie",
    "podlaskie",
    "lubuskie",
    "opolskie",
)'''
    text = re.sub(
        r"WOJEWODZTWO_ROTATION_ORDER: tuple\[str, \.\.\.\] = \(.*?\)\nBUNDESLAND_ROTATION_ORDER",
        order + "\nBUNDESLAND_ROTATION_ORDER",
        text,
        count=1,
        flags=re.DOTALL,
    )
    text = text.replace("DEFAULT_ROTATION_START = date(2026, 7, 13)", "DEFAULT_ROTATION_START = date(2026, 7, 14)")
    text = text.replace('"oblast": oblast', '"wojewodztwo": wojewodztwo')
    text = text.replace("oblast: str", "wojewodztwo: str")
    text = text.replace("oblast = peek_next_wojewodztwo", "wojewodztwo = peek_next_wojewodztwo")
    text = text.replace("return oblast, state", "return wojewodztwo, state")
    text = text.replace("OBLAST_ROTATION_ORDER[idx] != oblast", "WOJEWODZTWO_ROTATION_ORDER[idx] != wojewodztwo")
    text = text.replace("oblast = WOJEWODZTWO_ROTATION_ORDER[idx]", "wojewodztwo = WOJEWODZTWO_ROTATION_ORDER[idx]")
    return text


def post_scraper(text: str) -> str:
    text = re.sub(
        r"UA_OBLASTS = \[.*?\]",
        PL_WOJEWODZTWA_BLOCK,
        text,
        count=1,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"UA_COUNTRY_HINTS = \[.*?\]",
        PL_COUNTRY_HINTS,
        text,
        count=1,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"_FOREIGN_TLD_SUFFIXES = \(.*?\)",
        FOREIGN_TLD,
        text,
        count=1,
        flags=re.DOTALL,
    )
    text = text.replace(
        'campaign_output_paths(_campaign, "pl_materialy")',
        'campaign_output_paths(_campaign, "pl_materialy")',
    )
    text = text.replace(
        'UA_OBLAST_ROTATION_START',
        'PL_WOJEWODZTWO_ROTATION_START',
    )
    return text


def post_supplier_filter(text: str) -> str:
    repl = [
        ("цемент", "cement"),
        ("пісок", "piasek"),
        ("щебінь", "żwir"),
        ("цегла", "cegła"),
        ("блок", "bloczek"),
        ("арматура", "armatura"),
        ("утеплювач", "styropian"),
        ("плитка", "płytki"),
        ("гіпсокартон", "płyta gipsowa"),
        ("дошка", "drewno"),
        ("металопрокат", "stal"),
        ("покрівля", "dachówka"),
        ("бетон", "beton"),
        ("гравій", "żwir"),
        ("будматеріали", "materiały budowlane"),
        ("будівельні матеріали", "materiały budowlane"),
        ("оптом", "hurt"),
        ("оптовий", "hurtownia"),
        ("склад", "skład budowlany"),
        ("постачальник", "dostawca"),
        ("дистриб'ютор", "dystrybutor"),
        ("виробник", "producent"),
        ("будмаркет", "market budowlany"),
        ("будівельна база", "baza materiałów budowlanych"),
        ("будівельний магазин", "sklep budowlany"),
        ("архітектурне бюро", "biuro architektoniczne"),
        ("проєктування", "projektowanie"),
        ("дизайн інтер'єру", "wykończenia wnętrz"),
        ("банк", "bank"),
        ("страхова", "ubezpieczenia"),
        ("новинний портал", "portal informacyjny"),
        ("енциклопедія", "encyklopedia"),
        ("державна установа", "urząd"),
        ("міністерство", "ministerstwo"),
        ("біржа праці", "urząd pracy"),
        ("вакансії", "oferty pracy"),
        ("туристична агенція", "biuro podróży"),
        ("ресторан", "restauracja"),
        ("готель", "hotel"),
        ("автосалон", "salon samochodowy"),
        ("оголошення", "ogłoszenie"),
        ("купити б/у", "kup używane"),
        ("вживаний", "używany"),
        ("барахолка", "bazar"),
        ("новини", "wiadomości"),
        ("портал", "portal"),
        ("видання", "wydawnictwo"),
        ("редакція", "redakcja"),
        ("медіа", "media"),
        ("Kampania UA:", "Kampania PL:"),
    ]
    for a, b in repl:
        text = text.replace(a, b)
    return text


def main() -> None:
    build_keywords()
    fork_file("ua_oblast_rotation.py", "pl_wojewodztwo_rotation.py", post=post_rotation)
    fork_file("ua_materialy_supplier_filter.py", "pl_materialy_supplier_filter.py", post=post_supplier_filter)
    fork_file("ua_campaign_keyword_profile.py", "pl_campaign_keyword_profile.py")
    fork_file("ua_page_verify.py", "pl_page_verify.py")
    fork_file("ua_claude_page_verify.py", "pl_claude_page_verify.py")
    fork_file("ua_claude_prompts.py", "pl_claude_prompts.py")
    fork_file("ua_claude_inquiry_email.py", "pl_claude_inquiry_email.py")
    fork_file("ua_materialy_scraper.py", "pl_materialy_scraper.py", post=post_scraper)
    print("Done.")


if __name__ == "__main__":
    main()
