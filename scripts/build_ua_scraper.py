# -*- coding: utf-8 -*-
"""Jednorazowy generator ua_materialy_scraper.py z de_gu_bauunternehmen_scraper.py."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
src = ROOT / "de_gu_bauunternehmen_scraper.py"
dst = ROOT / "ua_materialy_scraper.py"
text = src.read_text(encoding="utf-8")

replacements = [
    (
        'Serper API – DE bundesweit: Generalunternehmer',
        'Serper API – UA: hurtownie / składy / producenci materiałów budowlanych',
    ),
    (
        "E-mail MFG + PPTX nur in diesem Modul (send_email_de_gu).",
        "E-mail UA (ukraiński) w tym module (send_email_ua_materialy).",
    ),
    (
        'campaign_output_paths(_campaign, "de_gu_bauunternehmen")',
        'campaign_output_paths(_campaign, "ua_materialy")',
    ),
    ("from de_gu_keywords import", "from ua_oblast_keywords import"),
    ("from gu_bundesland_rotation import", "from ua_oblast_rotation import"),
    ("from retail_store_builder_filter import", "from ua_materialy_supplier_filter import"),
    (
        "import retail_store_builder_filter as _retail_store_builder_filter",
        "import ua_materialy_supplier_filter as _retail_store_builder_filter",
    ),
    (
        "from mfg_gu_inquiry_email_de import FIXED_GU_INQUIRY_DE, build_fixed_gu_inquiry_de",
        "from ua_materialy_inquiry_email_uk import FIXED_MATERIAL_INQUIRY_UK, build_fixed_material_inquiry_uk",
    ),
    (
        "from mfg_gu_email_attachment import (\n"
        "    GOOGLE_SLIDES_PRESENTATION_ID,\n"
        "    GOOGLE_SLIDES_URL,\n"
        "    ensure_mfg_email_attachment,\n"
        ")",
        "ENABLE_EMAIL_ATTACHMENT = False",
    ),
    (
        "from claude_page_verify import claude_verify_company_page",
        "from ua_claude_page_verify import claude_verify_company_page",
    ),
    (
        "from claude_prompts import build_row_cleanup_prompt",
        "from ua_claude_prompts import build_row_cleanup_prompt",
    ),
    (
        "# KONFIGURATION – DE GU bundesweit (Einzelhandelsbau)",
        "# KONFIGURATION – UA materiały budowlane (hurtownie / składy)",
    ),
    ('SERPER_COUNTRY = "de"', 'SERPER_COUNTRY = "ua"'),
    ('SERPER_LANGUAGE = "de"', 'SERPER_LANGUAGE = "uk"'),
    ('COUNTRY_RESTRICTION = "DE"', 'COUNTRY_RESTRICTION = "UA"'),
    ('CUSTOM_EMAIL_LANG = "de"', 'CUSTOM_EMAIL_LANG = "uk"'),
    ('CUSTOM_EMAIL_CITY = "Deutschland"', 'CUSTOM_EMAIL_CITY = "Україна"'),
    (
        'INQUIRY_REGION_DE = "Deutschland (bundesweit)"',
        'INQUIRY_REGION_UA = "Україна"',
    ),
    (
        'RETAIL_CHAINS_DE = "Aldi, Penny, Kaufland, Netto, Rewe,Edeka"',
        'MATERIAL_CATEGORIES_UA = "цемент, пісок, щебінь, цегла, блок, арматура, утеплювач"',
    ),
    (
        'DELIVERY_ADDRESS_DE = "Deutschland (bundesweit)"',
        'DELIVERY_ADDRESS_UA = "Україна"',
    ),
    ("REQUIRE_NAMED_RETAIL_CHAIN = True", "REQUIRE_NAMED_RETAIL_CHAIN = False"),
    ("REQUIRE_MARKET_PROJECTS_IN_PORTFOLIO = True", "REQUIRE_MARKET_PROJECTS_IN_PORTFOLIO = False"),
    ("REQUIRE_WEBSITE_REFERENCES_OR_PORTFOLIO = True", "REQUIRE_WEBSITE_REFERENCES_OR_PORTFOLIO = False"),
    ("REQUIRE_SMALL_FIRM = True", "REQUIRE_SMALL_FIRM = False"),
    ("FIXED_GU_INQUIRY_DE", "FIXED_MATERIAL_INQUIRY_UK"),
    ("build_fixed_gu_inquiry_de", "build_fixed_material_inquiry_uk"),
    ("FIXED_EMAIL_SUBJECT_DE", "FIXED_EMAIL_SUBJECT_UK"),
    (
        'EMAIL_SUBJECT_TEMPLATE = (\n'
        '    "Kooperationsanfrage / Fliesen- & Estricharbeiten für Lebensmittelmärkte "\n'
        '    "(REWE, ALDI, NETTO etc.)"\n'
        ")",
        'EMAIL_SUBJECT_TEMPLATE = "Запит щодо постачання будівельних матеріалів"',
    ),
    ("send_email_de_gu", "send_email_ua_materialy"),
    ("get_email_attachments_de_gu", "get_email_attachments_ua_materialy"),
    ("_build_de_gu_outgoing_email", "_build_ua_materialy_outgoing_email"),
    ("_send_de_gu_via_smtp", "_send_ua_materialy_via_smtp"),
    ("DE GU:", "UA materialy:"),
    ("DE Ost (GU Ladenbau)", "UA materiały budowlane"),
    ("mfg_gu_inquiry_email_de", "ua_materialy_inquiry_email_uk"),
    ("apply_gu_run_config_extras", "apply_ua_run_config_extras"),
    ("def apply_gu_run_config_extras", "def apply_ua_run_config_extras"),
    ("--rotate-bundesland", "--rotate-oblast"),
    ("rotate_bundesland", "rotate_oblast"),
    ('"Bundesland"', '"Oblast"'),
    ('"Handelsketten"', '"Kategorie_materialow"'),
]

for old, new in replacements:
    text = text.replace(old, new)

ua_oblasts = """UA_OBLASTS = [
    "Kyiv", "Kyivska", "Lvivska", "Odeska", "Kharkivska", "Dnipropetrovska",
    "Zaporizka", "Vinnytska", "Poltavska", "Cherkaska", "Zhytomyrska",
    "Rivnenska", "Volyn", "Ternopilska", "Ivano-Frankivska", "Chernivetska",
    "Zakarpatska", "Khmelnytska", "Chernihivska", "Sumska", "Mykolaivska",
    "Kirovohradska", "Khersonska", "Donetska", "Luhanska",
]"""
text = re.sub(r"GERMAN_STATES = \[.*?\]", ua_oblasts, text, count=1, flags=re.DOTALL)

text = text.replace("REGION_CENTER_LAT = 51.1657", "REGION_CENTER_LAT = 48.3794")
text = text.replace("REGION_CENTER_LON = 10.4515", "REGION_CENTER_LON = 31.1656")

text = re.sub(
    r"DE_COUNTRY_HINTS = \[.*?\]",
    'UA_COUNTRY_HINTS = [\n    "україна",\n    "ukraine",\n    "украина",\n    ".ua/",\n    "київ",\n    "kyiv",\n    "львів",\n    "lviv",\n    "одеса",\n    "odesa",\n    "харків",\n    "kharkiv",\n]',
    text,
    count=1,
    flags=re.DOTALL,
)
text = text.replace("DE_COUNTRY_HINTS", "UA_COUNTRY_HINTS")

text = re.sub(
    r"_FOREIGN_TLD_SUFFIXES = \(.*?\)",
    '_FOREIGN_TLD_SUFFIXES = (\n    ".ru",\n    ".by",\n    ".pl",\n    ".de",\n    ".ro",\n    ".md",\n)',
    text,
    count=1,
    flags=re.DOTALL,
)

text = text.replace("not in GERMAN_STATES", "not in UA_OBLASTS")
text = text.replace("in GERMAN_STATES", "in UA_OBLASTS")
text = text.replace("de_gu_bundeslaender_rotation.json", "ua_materialy_oblast_rotation.json")

old_attach_block = """    attach_paths = get_email_attachments_ua_materialy(logger)
    if not attach_paths:
        return (
            False,
            f"Brak załącznika PPTX (Google Slides {GOOGLE_SLIDES_PRESENTATION_ID}). "
            f"Udostępnij prezentację lub ustaw MFG_EMAIL_ATTACHMENT_PATH. {GOOGLE_SLIDES_URL}",
        )
    attach_path = Path(attach_paths[0])
    size_mb = attach_path.stat().st_size / (1024 * 1024)
    logger.info(
        "UA materialy: załącznik %s (%.1f MB)",
        attach_path.name,
        size_mb,
    )
    if size_mb > 15:
        logger.warning(
            "UA materialy: duży PPTX (%.1f MB) — serwer SMTP może odrzucić załącznik.",
            size_mb,
        )

    try:
        msg = _build_ua_materialy_outgoing_email(
            username,
            to_email,
            subject_clean,
            body_clean,
            cc=cc,
            attachment_path=attach_path,
        )"""

new_attach_block = """    attach_paths: list = []
    attach_path = None

    try:
        msg = _build_ua_materialy_outgoing_email(
            username,
            to_email,
            subject_clean,
            body_clean,
            cc=cc,
            attachment_path=attach_path,
        )"""

if old_attach_block in text:
    text = text.replace(old_attach_block, new_attach_block)

text = text.replace(
    'if "--bundesland" in sys.argv:',
    'if "--oblast" in sys.argv or "--bundesland" in sys.argv:',
)
text = text.replace(
    'i = sys.argv.index("--bundesland")',
    'i = sys.argv.index("--oblast") if "--oblast" in sys.argv else sys.argv.index("--bundesland")',
)
text = text.replace(
    'print(f"[TRYB] Aktywne Bundesländer: {',
    'print(f"[TRYB] Aktywne obwody: {',
)

dst.write_text(text, encoding="utf-8")
print(f"Wrote {dst} ({dst.stat().st_size} bytes)")
