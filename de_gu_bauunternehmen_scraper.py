# -*- coding: utf-8 -*-
"""
Serper API – DE bundesweit: Generalunternehmer (GU), którzy stawiają sklepy/markety (Neubau, Filialbau)
lub robią przebudowy/umbau i modernizację filii (Rewe, Aldi, Kaufland, Netto, Penny, Edeka).
Nicht: Einzelhandels-Märkte als Betreiber, keine Urzędy/Portale.
E-mail MFG + PPTX nur in diesem Modul (send_email_de_gu).
Discovery i kontakty: Serper + requests + BeautifulSoup. www: Gemini czyści tekst (firma, e-mail, tel.), potem luźny regex. Przed Excel: Gemini czyści wiersze.
Bez Selenium / Google Maps. Baner cookie: Playwright (tylko „Akceptuj”).
Jupyter Lab: komórka 1 = %pip install …, komórka 2 = ten plik, komórka 3 = run_in_jupyter(…).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_campaign = Path(__file__).resolve().parent
CAMPAIGN_DIR = _campaign
_repo = _campaign
for _p in (_campaign / "libs", _campaign):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import kanbud_bootstrap as _kanbud_bootstrap

_kanbud_bootstrap.ensure_import_paths(_campaign)

from campaign_data_paths import campaign_output_paths

_paths = campaign_output_paths(_campaign, "de_gu_bauunternehmen")
_DATA_ROOT = _paths["data_root"]

from scraper_web_config import (
    ENABLE_GEMINI_CONTACT_EMAIL,
    ENABLE_PLAYWRIGHT_COOKIE_CONSENT,
)

# Excel: Gemini bereinigt Nazwa/Adres/Telefon/www/Bundesland vor dem Export (www-Verify bleibt regelbasiert)
ENABLE_GEMINI_ROW_CLEANUP = False
# Kontakte www: zuerst Gemini (Firma, E-Mail, Telefon), danach lockeres Regex
ENABLE_GEMINI_CONTACT_TEXT_CLEANUP = False
ENABLE_GEMINI_EMAIL_TEXT_CLEANUP = ENABLE_GEMINI_CONTACT_TEXT_CLEANUP  # Alias
GEMINI_CONTACT_TEXT_MAX_INPUT_CHARS = 10_000
GEMINI_EMAIL_TEXT_MAX_INPUT_CHARS = GEMINI_CONTACT_TEXT_MAX_INPUT_CHARS
from playwright_cookie_consent import apply_playwright_cookie_fallback
from de_gu_keywords import (
    DE_OST_PLACE_MARKERS,
    DE_OST_REGION_KEYWORDS,
    DE_OST_RURAL_HINTS,
    LARGE_COMPANY_DOMAINS_EXTRA,
    LARGE_COMPANY_NAME_MARKERS_EXTRA,
    RETAIL_BUILD_KEYWORDS,
    RETAIL_CHAIN_KEYWORDS,
    RETAIL_HOCHBAU_CORE_KEYWORDS,
    RETAIL_TRADE_ACTIVITY_KEYWORDS,
    IMPRESSUM_GUESS_PATHS,
    RETAIL_CONTACT_LINK_KEYWORDS,
    GU_ROLE_KEYWORDS,
    RETAIL_REFERENCE_KEYWORDS,
    RETAIL_URL_PRIORITY_KEYWORDS,
    SERPER_DISCOVERY_FALLBACK_TERMS,
    SERPER_DISCOVERY_REGION_SUFFIX,
    SERPER_DISCOVERY_TERMS,
    configure_campaign_bundeslaender,
    DEFAULT_ACTIVE_BUNDESLAENDER,
    CAMPAIGN_ACTIVE_BUNDESLAENDER as _KW_ACTIVE_BL,
    SERPER_NEGATIVE_TERMS,
    SERPER_POSITIVE_TERMS,
    SMALL_COMPANY_DISCOVERY_TERMS_EXTRA,
    SMALL_COMPANY_PAGE_MARKERS_EXTRA,
)

CAMPAIGN_ACTIVE_BUNDESLAENDER = list(_KW_ACTIVE_BL)


def apply_gu_run_config_extras(module, data: dict) -> None:
    """run_config.json: active_bundeslaender, min_contacts_target."""
    if data.get("active_bundeslaender"):
        lands = data["active_bundeslaender"]
        if isinstance(lands, str):
            lands = [lands]
        configure_campaign_bundeslaender(module, list(lands))
    if data.get("min_contacts_target") is not None:
        try:
            module.MIN_CONTACTS_TARGET = int(data["min_contacts_target"])
        except (TypeError, ValueError):
            pass


import csv
import hashlib
import json
import logging
import math
import random
import re
import subprocess
import time
from datetime import date, datetime
from urllib.parse import unquote, urljoin, urlparse

from polish_text import (
    normalize_unicode_text,
    sanitize_email_body,
    sanitize_special_text,
    setup_script_logging,
)
from scraper_env import (
    ENV_GEMINI_MODEL,
    ENV_GEMINI_MODELS,
    ENV_GMAIL_APP_PASSWORD,
    ENV_GMAIL_SENDER_NAME,
    ENV_GMAIL_USER,
    get_env_value,
    get_google_ai_studio_api_key,
    get_serper_api_key,
)
from scraper_email_replies import (
    ReplySyncConfig,
    mark_email_sent,
    merge_export_row,
    write_excel_with_reply_styles,
)
from de_contractor_exclusions import (
    contact_info_excluded,
    is_excluded_kontrahent,
)
from commercial_contact_filter import (
    filter_commercial_emails,
    is_junk_scraped_email,
    is_cache_contact_institution,
    is_cache_serper_entry_institution,
    is_non_commercial_contact,
    is_non_commercial_email,
    is_non_commercial_name,
    is_non_commercial_website,
    is_valid_commercial_company_contact,
)
from retail_store_builder_filter import (
    has_retail_references_or_portfolio,
    is_cache_contact_not_store_builder,
    is_retail_store_operator_contact,
    is_valid_retail_store_builder_contact,
    mentions_retail_store_build_activity,
    mentions_retail_store_build_activity_core,
)

# Przy zapisie cache: usuń urzędy/instytucje z contacts (+ serper/gemini powiązane)
ENABLE_CACHE_PURGE_INSTITUTIONS = True
from email_targeting import (
    AGGREGATOR_EMAIL_DOMAINS,
    MIN_EMAIL_SCORE_FOR_SEND,
    get_registrable_domain,
    is_unsuitable_inquiry_email,
    needs_gemini_email_arbitration,
    pick_best_email_for_inquiry,
    rank_email_candidates,
    score_email_candidate,
    validate_gemini_email_choice,
)

import requests
from bs4 import BeautifulSoup  # pyright: ignore[reportMissingModuleSource]

# =========================
# KONFIGURATION – DE GU bundesweit (Einzelhandelsbau)
# =========================
# Wyniki: Google Drive (KANBUD_GOOGLE_DRIVE_GU_PATH) lub folder kampanii — patrz campaign_data_paths.py
OUTPUT_DIR = _paths["output_dir"]
OUTPUT_FILE = _paths["output_file"]
CACHE_FILE = _paths["cache_file"]
LOG_FILE = _paths["log_file"]

# Serper – frazy i słowniki: de_gu_keywords.py (GU Hochbau Einzelhandel)
MIN_CONTACTS_TARGET = 150

# Geo: bundesweit (Filter PLZ/Distanz aus; center nur für Hilfsfunktionen)
REGION_CENTER_LAT = 51.1657
REGION_CENTER_LON = 10.4515
MAX_DISTANCE_FROM_REGION_KM = 9999
# Grobe Bounding-Box Deutschland (optional)
DE_DE_BBOX_LAT_MIN = 47.25
DE_DE_BBOX_LAT_MAX = 55.10
DE_DE_BBOX_LON_MIN = 5.85
DE_DE_BBOX_LON_MAX = 15.05

AUTO_ENRICH_CONTACTS = True
# True: Serper/www nie pomijają URL-i już w contacts JSON — zawsze ponowne wzbogacanie
DISCOVERY_IGNORE_CONTACT_CACHE = True
# True: do Excela także firmy bez e-mail (po www-verify / Filialbau)
EXPORT_PIPELINE_ROWS_WITHOUT_EMAIL = True
STEP_LOG_WITH_TIMESTAMP = True

SERPER_API_URL = "https://google.serper.dev/search"
SERPER_COUNTRY = "de"
SERPER_LANGUAGE = "de"
SERPER_TIMEOUT = 20
SERPER_DAILY_LIMIT = 300
FORCE_SERPER_LOOKUP = True
SERPER_DISCOVERY_RESULTS_PER_TERM = 30
COUNTRY_RESTRICTION = "DE"
ENABLE_REGION_PLZ_FILTER = False
ENABLE_DISTANCE_FROM_REGION_KM = False
ENABLE_PLZ_PREFIX_REGION_MATCH = False
REQUEST_TIMEOUT = 20
MAX_CONTACT_LINKS = 6
MAX_IMPRESSUM_GUESS_FETCH = 3
HTTP_RETRY_ATTEMPTS = 3
HTTP_BACKOFF_SECONDS = 1.5
GEMINI_MODEL = get_env_value(ENV_GEMINI_MODEL, "gemini-2.0-flash")
GEMINI_MODELS = get_env_value(
    ENV_GEMINI_MODELS,
    "gemini-2.5-flash-lite,gemini-2.0-flash-lite",
).strip()
GEMINI_INTER_MODEL_DELAY_SECONDS = 15
GEMINI_MIN_SECONDS_BETWEEN_CALLS = 4
GEMINI_RATE_LIMIT_COOLDOWN_SECONDS = 3600
PAGE_SNIPPET_MAX_CHARS = 3500

ENABLE_AUTO_EMAIL = True
# Własny szablon z GUI (Gemini dopracowuje per firma); nie dotyczy przypomnień
CUSTOM_EMAIL_DRAFT = ""
USE_CUSTOM_EMAIL_TEMPLATE = False
CUSTOM_EMAIL_LANG = "de"
CUSTOM_EMAIL_CITY = "Deutschland"
CUSTOM_EMAIL_CONTEXT: dict = {}
EMAIL_SUBJECT_TEMPLATE = (
    "Kooperationsanfrage / Fliesen- & Estricharbeiten für Lebensmittelmärkte "
    "(REWE, ALDI, NETTO etc.)"
)
# Obligatorischer Betreff (word-for-word; bez zmian przez Gemini)
FIXED_EMAIL_SUBJECT_DE = EMAIL_SUBJECT_TEMPLATE
EMAIL_SIGNATURE = (
    "Mit freundlichen Grüßen\n\n"
    "Maksym Swinczak\n\n"
    "MFG Moderner Fliesenboden GmbH\n\n"
    "Tel.: +49 1522 3655 399"
)
BACKGROUND_ONLY_DEFAULT = True
DAILY_EMAIL_LIMIT = 300
EMAIL_PER_DOMAIN_DAILY_LIMIT = 2
from scraper_schedule_config import load_send_window_config, is_within_send_window as _schedule_within_send_window

_SEND_WINDOW_CFG = load_send_window_config()
SEND_WINDOW_START_HOUR = _SEND_WINDOW_CFG.start_hour
SEND_WINDOW_END_HOUR = _SEND_WINDOW_CFG.end_hour
SEND_WINDOW_DISABLED = _SEND_WINDOW_CFG.disabled
SUBJECT_VARIANTS = [FIXED_EMAIL_SUBJECT_DE]
PROMPT_VARIANTS = [
    "Formell und sachlich, wie eine normale B2B-Anfrage.",
    "Kurz und natürlich – Kooperation GU / Estrich und Fliesen.",
    "Professionell-freundlich, ohne übertriebene Floskeln.",
]
EMAIL_SEND_DELAY_MIN_SECONDS = 22
EMAIL_SEND_DELAY_MAX_SECONDS = 58
EMAIL_SPAMMY_TERMS = [
    "gratis",
    "darmowy",
    "promocja",
    "rabat",
    "pilne",
    "kliknij",
    "super okazja",
    "wyprzedaż",
    "kostenlos",
    "sonderangebot",
]
SERPER_BAD_DOMAINS = [
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "gelbeseiten.",
    "11880.com",
    "11880.",
    "wikipedia.org",
    "vergabemarktplatz",
    "stadt.de",
    "gemeinde.",
    "landkreis",
    "ihk.",
    "ihk.de",
    "hwk.",
    "bund.de",
    "visitberlin",
    "thueringen-entdecken",
    "forst.thueringen",
    "standort-sachsen",
    "wirtschaftsfoerderung",
    "senatskanzlei",
    "leipzig.de",
    "dgnb.de",
    "nexxt-change",
    "arbeitsagentur",
    "uni-",
    ".uni.",
    "hochschule",
    "gruenderzentrum",
    "gründerzentrum",
    "ibau.",
    "ibau.de",
    "tgzp.",
    "tgzp.de",
    "shop.rewe",
    "filialfinder",
    "aldi-sued.de",
    "aldi-nord.de",
    "penny.de",
    "kaufland.de",
    "lidl.de",
    "netto-online",
]
NON_DE_FOREIGN_HINTS = [
    "polska",
    "poland",
    ".pl/",
    "österreich",
    "austria",
    "schweiz",
    "switzerland",
    "france",
    "italy",
    "netherlands",
    "nederland",
    "czech",
    "česko",
    "cesko",
    ".cz/",
]
# Geo / Serper – de_gu_keywords.py
DE_COUNTRY_HINTS = [
    "deutschland",
    "germany",
    "bundesrepublik",
    ".de/",
    *DE_OST_PLACE_MARKERS,
    *DE_OST_RURAL_HINTS,
    *DE_OST_REGION_KEYWORDS,
]
DE_EAST_PLZ_PREFIXES = frozenset({
    "01", "02", "03", "04", "06", "07", "08", "09",
    "14", "15", "16", "17", "18", "19",
    "37", "38", "39", "98", "99",
})
SUPPRESSED_EMAIL_LOCALPARTS = {
    "noreply",
    "no-reply",
    "do-not-reply",
    "donotreply",
    "mailer-daemon",
    "postmaster",
}
EXPORT_COLUMNS = [
    "Firmenname",
    "Adresse",
    "Bundesland",
    "Telefon",
    "E-Mail",
    "Webseite",
    "Handelsketten",
    "WWW_geprueft",
    "Kleinunternehmen",
]
GERMAN_STATES = [
    "Baden-Wuerttemberg",
    "Bayern",
    "Berlin",
    "Brandenburg",
    "Bremen",
    "Hamburg",
    "Hessen",
    "Mecklenburg-Vorpommern",
    "Niedersachsen",
    "Nordrhein-Westfalen",
    "Rheinland-Pfalz",
    "Saarland",
    "Sachsen",
    "Sachsen-Anhalt",
    "Schleswig-Holstein",
    "Thueringen",
]

# Kontext Anfrage (Referenz im Code; Mailtext = fester Block unten)
INQUIRY_REGION_DE = "Deutschland (bundesweit)"
RETAIL_CHAINS_DE = "Aldi, Penny, Kaufland, Netto, Rewe,Edeka"
DELIVERY_ADDRESS_DE = "Deutschland (bundesweit)"

# Weryfikacja www: GU/Filialbau + Neubau/Umbau + dowód projektów marketów (tekst/zdjęcia)
REQUIRE_WEBSITE_RETAIL_VERIFICATION = True
REQUIRE_WEBSITE_REFERENCES_OR_PORTFOLIO = True
REQUIRE_MARKET_PROJECTS_IN_PORTFOLIO = True
ENABLE_GEMINI_RETAIL_VERIFICATION = False
MAX_PAGES_FOR_RETAIL_VERIFICATION = 4
LARGE_COMPANY_DOMAINS = frozenset(
    {
        "strabag.com",
        "hochtief.de",
        "zech-group.com",
        "bilfinger.com",
        "porr-group.com",
        "wolffmueller.de",
        "diringer.de",
        "goldbeck.de",
        "implenia.com",
        "bauholding-strabag",
        "turnerconstruction",
        "skanska.",
        "bouygues",
    }
) | LARGE_COMPANY_DOMAINS_EXTRA
LARGE_COMPANY_NAME_MARKERS = (
    "strabag",
    "hochtief",
    "bilfinger",
    "porr ",
    "porr.",
    "goldbeck",
    "implenia",
    "zech group",
    "zech bau",
    "wolff & müller",
    "wolff und mueller",
    "diringer",
    "konzerngesellschaft",
    "konzern ",
    "ag holding",
    " se ",
    " gmbh & co. kg",  # alone not enough — combined with other signals
    "europäischer marktführer",
    "weltmarktführer",
    *LARGE_COMPANY_NAME_MARKERS_EXTRA,
)
LARGE_COMPANY_PAGE_MARKERS = (
    "weltweit tätig",
    "weltweit",
    "international tätig",
    "konzern",
    "börsennotiert",
    "aktionär",
    "mitarbeiter weltweit",
    "über 1.000 mitarbeiter",
    "über 1000 mitarbeiter",
    "mehr als 500 mitarbeiter",
    "tausend mitarbeiter",
    "global player",
    "tochtergesellschaft der",
)
SMALL_COMPANY_PAGE_MARKERS = (
    "familienunternehmen",
    "familienbetrieb",
    "inhabergeführt",
    "inhabergefuehrt",
    "meisterbetrieb",
    "mittelständ",
    "mittelstaend",
    "regional tätig",
    "regional taetig",
    "vor ort",
    "kleinunternehmen",
    "handwerks",
    *SMALL_COMPANY_PAGE_MARKERS_EXTRA,
)
SMALL_COMPANY_DISCOVERY_TERMS = (
    "mittelstand",
    "familienunternehmen",
    "regional",
    "meisterbetrieb",
    "klein",
    "inhabergeführt",
    *SMALL_COMPANY_DISCOVERY_TERMS_EXTRA,
)


from mfg_gu_inquiry_email_de import FIXED_GU_INQUIRY_DE, build_fixed_gu_inquiry_de
from mfg_gu_email_attachment import (
    GOOGLE_SLIDES_PRESENTATION_ID,
    GOOGLE_SLIDES_URL,
    ensure_mfg_email_attachment,
)
_OST_GU_SMTP_DEFAULT_HOST = "serwer.home.pl"
_OST_GU_SMTP_PORT_SSL = 465
_OST_GU_SMTP_PORT_STARTTLS = 587


def _ost_gu_truthy(raw: str) -> bool:
    return str(raw or "").strip().lower() in ("1", "true", "yes", "tak", "on")


def _ost_gu_split_recipients(raw: str) -> list[str]:
    if not raw:
        return []
    if str(raw).strip().lower() in ("0", "off", "false", "no", "nie"):
        return []
    parts = re.split(r"[,;]+", raw)
    return [p.strip() for p in parts if p.strip()]


def _ost_gu_smtp_host() -> str:
    from scraper_env import ENV_SMTP_HOST, get_env_value, get_mail_user

    host = get_env_value(ENV_SMTP_HOST).strip()
    if host:
        return host
    addr = (get_mail_user() or "").strip().lower()
    if "@gmail.com" in addr or "@googlemail.com" in addr:
        return "smtp.gmail.com"
    return _OST_GU_SMTP_DEFAULT_HOST


def _ost_gu_smtp_port() -> int:
    from scraper_env import ENV_SMTP_PORT, ENV_SMTP_SSL, get_env_value

    raw = get_env_value(ENV_SMTP_PORT).strip()
    if raw.isdigit():
        return int(raw)
    if _ost_gu_truthy(get_env_value(ENV_SMTP_SSL)):
        return _OST_GU_SMTP_PORT_SSL
    return _OST_GU_SMTP_PORT_STARTTLS


def _ost_gu_smtp_use_ssl() -> bool:
    from scraper_env import ENV_SMTP_SSL, get_env_value

    if get_env_value(ENV_SMTP_SSL).strip():
        return _ost_gu_truthy(get_env_value(ENV_SMTP_SSL))
    return _ost_gu_smtp_port() == _OST_GU_SMTP_PORT_SSL


def _ost_gu_yagmail_client():
    import yagmail  # pyright: ignore[reportMissingImports]

    from scraper_env import get_mail_password, get_mail_user

    username = get_mail_user()
    password = get_mail_password()
    if not (username and password):
        raise ValueError("brak MAIL_USER / MAIL_PASSWORD")
    host = _ost_gu_smtp_host()
    if not host:
        return yagmail.SMTP(user=username, password=password)
    port = _ost_gu_smtp_port()
    use_ssl = _ost_gu_smtp_use_ssl()
    return yagmail.SMTP(
        user=username,
        password=password,
        host=host,
        port=port,
        smtp_ssl=use_ssl,
        smtp_starttls=not use_ssl,
    )


def get_email_attachments_de_gu(logger: logging.Logger | None = None) -> list[str]:
    """Załącznik PPTX ze Slides — zawsze wymagany przy wysyłce."""
    path = ensure_mfg_email_attachment(CAMPAIGN_DIR, logger)
    if path and path.is_file():
        return [str(path.resolve())]
    return []


def _build_de_gu_outgoing_email(
    username: str,
    to_email: str,
    subject: str,
    body_plain: str,
    *,
    cc: list[str],
    attachment_path: Path | None,
) -> "EmailMessage":
    import mimetypes
    from email.message import EmailMessage

    from scraper_env import get_mail_sender_name

    msg = EmailMessage()
    sender_name = " ".join((get_mail_sender_name() or "").replace("\n", " ").split()).strip()
    if sender_name:
        msg["From"] = f"{sender_name} <{username}>"
    else:
        msg["From"] = username
    msg["To"] = to_email
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    msg.set_content(body_plain, subtype="plain", charset="utf-8")
    if attachment_path and attachment_path.is_file():
        data = attachment_path.read_bytes()
        ctype, _enc = mimetypes.guess_type(str(attachment_path))
        if ctype and "/" in ctype:
            maintype, subtype = ctype.split("/", 1)
        else:
            maintype, subtype = (
                "application",
                "vnd.openxmlformats-officedocument.presentationml.presentation",
            )
        msg.add_attachment(
            data,
            maintype=maintype,
            subtype=subtype,
            filename=attachment_path.name,
        )
    return msg


def _send_de_gu_via_smtp(
    msg: "EmailMessage",
    *,
    username: str,
    password: str,
    to_email: str,
    cc: list[str],
    bcc: list[str],
    logger: logging.Logger,
) -> None:
    import smtplib

    recipients: list[str] = [to_email]
    for addr in cc + bcc:
        if addr and addr.lower() not in {x.lower() for x in recipients}:
            recipients.append(addr)
    host = _ost_gu_smtp_host()
    port = _ost_gu_smtp_port()
    use_ssl = _ost_gu_smtp_use_ssl()
    try:
        smtp_timeout = int((os.environ.get("SMTP_TIMEOUT") or "300").strip())
    except (TypeError, ValueError):
        smtp_timeout = 300
    smtp_timeout = max(60, min(smtp_timeout, 600))
    if use_ssl:
        with smtplib.SMTP_SSL(host, port, timeout=smtp_timeout) as smtp:
            smtp.login(username, password)
            smtp.send_message(msg, from_addr=username, to_addrs=recipients)
    else:
        with smtplib.SMTP(host, port, timeout=smtp_timeout) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(username, password)
            smtp.send_message(msg, from_addr=username, to_addrs=recipients)
    logger.info(
        "DE Ost GU: SMTP send_message OK → %s (odbiorcy SMTP: %s)",
        host,
        len(recipients),
    )


def console_step(message: str) -> None:
    if STEP_LOG_WITH_TIMESTAMP:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] [SCHRITT] {message}", flush=True)
    else:
        print(f"[SCHRITT] {message}", flush=True)


def is_running_in_jupyter() -> bool:
    try:
        from IPython.core.getipython import get_ipython

        shell = get_ipython()
        if shell is None:
            return False
        return shell.__class__.__name__ == "ZMQInteractiveShell"
    except Exception:
        return False


def wait_for_user_confirmation(message: str, jupyter_mode: bool = False) -> None:
    print(message)
    if jupyter_mode:
        print("In Jupyter: Beliebige Eingabe und Enter zum Fortfahren.")
    try:
        input("> ")
    except EOFError:
        print("Kein interaktives stdin. Warte 15 Sekunden und fahre fort.")
        time.sleep(15)


def setup_logging() -> logging.Logger:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return setup_script_logging("de_gu_bauunternehmen_scraper", LOG_FILE)


def save_csv(rows, path: Path) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fields = [
        "fraza",
        "nazwa",
        "ocena",
        "liczba_opinii",
        "kategoria",
        "adres",
        "full_address",
        "status",
        "telefon",
        "www",
        "url",
        "lat_center",
        "lon_center",
    ]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def save_excel(rows, path: Path, logger: logging.Logger, cache=None) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        rows_for_excel = rows
        if (
            logger is not None
            and cache is not None
            and ENABLE_GEMINI_ROW_CLEANUP
        ):
            console_step(
                f"Gemini: Bereinigung vor Excel ({len(rows)} Zeilen)…"
            )
            rows_for_excel = [
                enrich_row_with_gemini_cleanup(dict(r), logger, cache)
                for r in rows
            ]
        export_rows = build_export_rows(
            rows_for_excel, logger=logger, cache=cache
        )
        state_rows = build_bundesland_rows(rows_for_excel)
        if cache is None:
            cache = {}
        cfg = ReplySyncConfig(
            cache_path=CACHE_FILE,
            xlsx_path=path,
            lang="de",
            campaign_id="de_gu_bauunternehmen",
        )
        try:
            write_excel_with_reply_styles(
                path,
                {"Kontakte": export_rows, "Wojewodztwa": state_rows},
                cache,
                cfg,
                logger,
            )
        except PermissionError:
            alt = path.with_name(f"{path.stem}_export{path.suffix}")
            logger.warning(
                "Excel gesperrt (%s) – speichere nach: %s", path, alt
            )
            print(
                f"[EXCEL] Plik otwarty w Excelu — zapisano kopię: {alt}"
            )
            cfg_alt = ReplySyncConfig(
                cache_path=CACHE_FILE,
                xlsx_path=alt,
                lang="de",
                campaign_id="de_gu_bauunternehmen",
            )
            write_excel_with_reply_styles(
                alt,
                {"Kontakte": export_rows, "Wojewodztwa": state_rows},
                cache,
                cfg_alt,
                logger,
            )
    except ImportError as e:
        logger.error(
            "pandas/openpyxl fehlen. Installieren: pip install pandas openpyxl"
        )
        raise e


def extract_bundesland(row: dict) -> str:
    explicit = (row.get("bundesland") or "").strip()
    if explicit:
        return explicit
    text = " ".join(
        x for x in [(row.get("full_address") or ""), (row.get("adres") or "")] if x
    ).lower()
    for state in GERMAN_STATES:
        if state.lower() in text:
            return state
    mapping = (
        ("brandenburg", "Brandenburg"),
        ("sachsen-anhalt", "Sachsen-Anhalt"),
        ("sachsen", "Sachsen"),
        ("thüringen", "Thueringen"),
        ("thueringen", "Thueringen"),
    )
    for key, val in mapping:
        if key in text:
            return val
    plz_list = extract_plz_from_text(text)
    if plz_list:
        prefix = plz_list[0][:2]
        plz_state = {
            "01": "Sachsen",
            "02": "Sachsen",
            "03": "Brandenburg",
            "04": "Sachsen",
            "06": "Sachsen-Anhalt",
            "07": "Sachsen",
            "08": "Sachsen",
            "09": "Sachsen",
            "14": "Brandenburg",
            "15": "Brandenburg",
            "16": "Brandenburg",
            "17": "Brandenburg",
            "18": "Brandenburg",
            "19": "Brandenburg",
            "37": "Thueringen",
            "38": "Sachsen-Anhalt",
            "39": "Sachsen-Anhalt",
            "98": "Thueringen",
            "99": "Thueringen",
        }
        if prefix in plz_state:
            return plz_state[prefix]
    return ""


def sanitize_log_url(url: str) -> str:
    if not url:
        return url
    return re.sub(r"key=[^&\s]+", "key=***", url)


def _is_rate_limit_error(err: Exception) -> bool:
    text = str(err).lower()
    if "429" in text or "too many requests" in text or "resource exhausted" in text:
        return True
    status = getattr(getattr(err, "response", None), "status_code", None)
    return status == 429


def is_gemini_rate_limited(cache: dict | None) -> bool:
    if not cache:
        return False
    until = float(cache.get("gemini_rate_limit_until", 0) or 0)
    return until > time.time()


def mark_gemini_rate_limited(
    cache: dict | None, logger: logging.Logger, cooldown_seconds: int | None = None
) -> None:
    if cache is None:
        return
    seconds = int(cooldown_seconds or GEMINI_RATE_LIMIT_COOLDOWN_SECONDS)
    cache["gemini_rate_limit_until"] = time.time() + seconds
    logger.warning(
        f"Gemini Rate-Limit: Pause {seconds}s (keine weiteren API-Aufrufe bis Reset)."
    )


def wait_for_gemini_slot(cache: dict | None) -> None:
    if cache is None:
        return
    last = float(cache.get("gemini_last_call_at", 0) or 0)
    wait = GEMINI_MIN_SECONDS_BETWEEN_CALLS - (time.time() - last)
    if wait > 0:
        time.sleep(wait)


def touch_gemini_call(cache: dict | None) -> None:
    if cache is not None:
        cache["gemini_last_call_at"] = time.time()


_COMPANY_LEGAL_FORM_PATTERN = (
    r"(?:GmbH|UG(?:\s*\(haftungsbeschränkt\))?|AG|GbR|e\.?\s*K\.?|KG|OHG|PartG|Co\.\s*KG|mbH|SE|SE\s*&\s*Co\.\s*KG)"
)

# Harte Ablehnung für Excel/Gemini — kein Firmenname (PDF, Portale, Städte, SEO, Software …)
_COMPANY_NAME_HARD_REJECT_MARKERS = (
    "[pdf]",
    "pdf]",
    "pdf-",
    "pdf ",
    "pdf.",
    "xchange",
    "pdf-xchange",
    "tracker software",
    "öffentlich nicht",
    "nichtöffentlich",
    "vergabemarktplatz",
    "ausschreibung",
    "vergabe",
    "11880",
    "gelbeseiten",
    "firmenabc",
    "wikipedia",
    "nexxt-change",
    "visitberlin",
    "stadt leipzig",
    "dezernat",
    "senatskanzlei",
    "wirtschaftsförderung",
    "ihk ",
    "handelskammer",
    "top 100",
    "top 10",
    "10 beste",
    "katalog",
    "referenzen ::",
    "referenzen:",
    "gewerbebau",
    "gewerbestandort",
    "gewerbefläch",
    "generalunternehmer",
    "bau von gebäuden",
    "unternehmen in ",
    "unternehmen kaufen",
    "öffentliche ausschreib",
    "mitgliedsunternehmen",
    "akteure",
    "kaufangebote",
    "haus der ",
    "wirtschaftsstandort",
    "hauptstadtregion",
    "mittelstand",
    "jobs bei",
    "stellenangebot",
    "newsletter",
    "presse@",
    "http://",
    "https://",
    ".de/pdfs/",
    "/pdfs/",
    "seite 1 von",
    "anlage 2",
    "auswirkungsanalyse",
    "widget/de",
    "planungsplan",
    "vermarktungsplan",
    "adobe",
    "microsoft",
    "word ",
    "excel ",
)

_COMPANY_NAME_SOFT_REJECT_IF_NO_LEGAL_FORM = (
    "erfurt",
    "leipzig",
    "potsdam",
    "cottbus",
    "chemnitz",
    "dresden",
    "halle",
    "brandenburg",
    "thüringen",
    "sachsen",
    "berlin",
    "aldi in ",
    "penny in ",
    "kaufland in ",
    "rewe markt",
    "neuer penny",
    "neubau-rewe",
    "filiale",
    "markt für",
    "baut markt",
    "investieren in",
    "go-lausitz",
)


def _company_name_has_legal_form(name: str) -> bool:
    return bool(re.search(_COMPANY_LEGAL_FORM_PATTERN, name or "", re.IGNORECASE))


def is_rejected_company_name_for_export(
    name: str, website: str = "", email: str = ""
) -> bool:
    """True = kein gültiger GU-Firmenname für Excel/Outreach."""
    if is_excluded_kontrahent(name=name, url=website, email=email)[0]:
        return True
    text = " ".join((name or "").split()).strip()
    if not text or len(text) < 4:
        return True
    low = text.lower()
    if re.match(r"^[\W\d_]+$", text):
        return True
    if any(m in low for m in _COMPANY_NAME_HARD_REJECT_MARKERS):
        return True
    if (website or "").lower().find("/pdfs/") >= 0 or (website or "").lower().endswith(".pdf"):
        return True
    email_low = (email or "").lower()
    if email_low and any(
        x in email_low
        for x in (
            "pdf-xchange",
            "xchange",
            "vergabe",
            "wfs.saxony",
            "visitberlin",
            "leipzig.de",
            "senatskanzlei",
            "forst.thueringen",
            "funkemedien",
            "th24.de",
            "rewe-group.com",
        )
    ):
        return True
    if not _company_name_has_legal_form(text):
        if any(m in low for m in _COMPANY_NAME_SOFT_REJECT_IF_NO_LEGAL_FORM):
            return True
        if len(text.split()) <= 2 and not re.search(r"[&\.\-]", text):
            return True
    if text.count(":") >= 2 or text.startswith("["):
        return True
    return False


def finalize_company_name_for_export(
    gemini_name: str,
    *,
    fallback_raw: str,
    website: str = "",
    email: str = "",
) -> str:
    """Nach Gemini: nur Name+Rechtsform, sonst Impressum/Domain-Fallback."""
    website = website_base_url(website) if website else ""
    candidates: list[str] = []
    if should_prefer_domain_company_name(fallback_raw, website):
        candidates.append(derive_name_from_website(website))
    candidates.extend(
        (
            sanitize_special_text(gemini_name or ""),
            clean_company_name(fallback_raw, website),
            derive_name_from_website(website),
        )
    )
    for candidate in candidates:
        name = " ".join((candidate or "").split()).strip(" :|–—")
        if not name or is_rejected_company_name_for_export(name, website, email):
            continue
        if _company_name_has_legal_form(name):
            return name
    return ""


def build_gemini_row_cleanup_prompt(
    *,
    company: str,
    address: str,
    phone: str,
    email: str,
    website: str,
    states: str,
) -> str:
    return f"""Du bist ein EXTREM strenger Datenprüfer für B2B-Outreach an Generalunternehmer (GU) /
Bauunternehmen, die Lebensmittelmärkte und Filialen NEU BAUEN oder UMBAUEN. Auf der Website muss ein
Nachweis von MARKT-Projekten sichtbar sein: Referenzen/Portfolio ODER Fotos/Galerie (z. B. Aldi, Rewe,
Supermarkt, Filiale) — eine eigene Rubrik „Portfolio“ ist nicht zwingend.
Keine Einzelhandels-Märkte als Betreiber.
Deine einzige Aufgabe: Felder bereinigen.

═══ AUSGABE ═══
Gib AUSSCHLIESSLICH ein einziges gültiges JSON-Objekt zurück (kein Markdown, kein Kommentar).
Schema exakt:
{{"company_name_clean":"","address":"","phone":"","website":"","bundesland":""}}

═══ company_name_clean — HÖCHSTE PRIORITÄT (KILLER-REGELN) ═══
Zulässig NUR: offizieller Firmenname + Rechtsform in EINER Zeile.
Beispiele OK: "Max Wiessner Baugeschäft GmbH", "Müller Ladenbau GmbH", "SuS Bau GmbH" (mit Filialbau-Kontext).
NICHT OK: reine Bausanierung ohne Filialbau, REWE/Aldi-Markt als Betreiber, keine Bau-GU.
Format: <Name> <Rechtsform> — Rechtsform MUSS vorkommen: GmbH, UG, AG, GbR, e.K., KG, OHG, PartG, Co. KG, SE.

STRENG VERBOTEN — bei jedem Treffer company_name_clean = "" (leerer String):
• PDF/Dokumente: alles mit [PDF], PDF, Dokument, Bebauungsplan, Anlage, Auswirkungsanalyse, Seite X von Y
• Software/IT (NIEMALS als Bauunternehmen): PDF-XChange, PDF XChange, Tracker, Adobe, Microsoft, xchange, shop@pdf-*
• Portale/Kataloge/News ohne GU: Vergabemarktplatz, Ausschreibung, 11880, GelbeSeiten, Wikipedia, Nexxt-Change,
  "Top 100", "10 beste", Referenzen-Listen, Katalog, Mitgliedsunternehmen, IHK-Listen, Stadtverwaltung, Dezernat
• Nur Stadt/Region/Projekt: "Erfurt", "Leipzig", "Potsdam", "Gewerbebau", "Generalunternehmer", "Gewerbeflächen",
  "ALDI in Borna", "Penny Neubau", "Kaufland in …", Zeitungsüberschriften, Bauprojekt-Titel ohne Firma
• URLs, E-Mail-Adressen, Emojis, Marketing-Slogans, Doppelpunkte am Ende ("Firma XYZ:")
• Branchenportale, Wirtschaftsförderung, Tourismus (visitberlin, thueringen-entdecken, forst.thueringen …)

Wenn der Eingabe-Name Müll ist, aber Website/Impressum-Kontext eindeutig eine echte Baufirma mit Rechtsform erlauben —
nur dann den echten Namen aus dem Kontext ableiten. NIEMALS erfinden.
Wenn unsicher oder keine Rechtsform ableitbar: company_name_clean = "".

═══ Weitere Felder ═══
• address: Straße + PLZ + Ort (Deutschland) oder ""
• phone: eine deutsche Rufnummer (+49/0…) oder ""
• website: kanonische Firmen-https-URL (kein Verzeichnis, kein PDF-Link) oder ""
• bundesland: genau ein Wert aus [{states}] oder ""
• E-Mail aus Eingabe NICHT ändern/übernehmen (nur zur Plausibilitätsprüfung).

═══ Eingabe ═══
name={company}
address={address}
phone={phone}
website={website}
email_nur_info={email}
"""


def gemini_fallback_enrichment(
    row: dict, company: str, address: str, phone: str, email: str, website: str
) -> dict:
    bundesland = extract_bundesland(row)
    return {
        "company_name_clean": company,
        "address": address,
        "phone": phone,
        "email": email,
        "website": website,
        "bundesland": bundesland,
        "_fallback": True,
    }


def apply_gemini_enrichment_to_row(row: dict, gemini_result: dict) -> None:
    """Gemini czyści nazwę/adres/telefon — e-mail zostaje z pick_best / gemini_pick kontaktów."""
    company = gemini_result.get("company_name_clean") or row.get("nazwa") or ""
    row["company_name_clean"] = company
    row["nazwa"] = company
    row["adres"] = gemini_result.get("address", row.get("adres", ""))
    row["telefon"] = gemini_result.get("phone", row.get("telefon", ""))
    row["official_website"] = gemini_result.get("website", row.get("official_website", ""))
    row["bundesland"] = gemini_result.get("bundesland", row.get("bundesland", ""))


def enrich_row_with_gemini_cleanup(row: dict, logger: logging.Logger, cache: dict) -> dict:
    gemini_cache = cache.setdefault("gemini_row_enrichment", {})
    cache_key = (
        (row.get("url") or "").strip()
        or f"{(row.get('nazwa') or '').strip()}|{(row.get('www') or '').strip()}"
    )
    address = sanitize_special_text(row.get("full_address") or row.get("adres") or "")
    phone = sanitize_special_text(row.get("phones_found") or row.get("telefon") or "")
    # E-mail nie przechodzi przez sanitize_special_text (usuwałby znaki / łamał listę)
    email = (row.get("email_target") or "").strip()
    website = sanitize_special_text(row.get("official_website") or row.get("www") or "")
    company = sanitize_special_text(
        row.get("company_name_clean") or row.get("nazwa") or row.get("company_name_raw") or ""
    )
    if cache_key and cache_key in gemini_cache:
        apply_gemini_enrichment_to_row(row, gemini_cache[cache_key])
        return row

    row["company_name_clean"] = company
    row["nazwa"] = company
    row["adres"] = address
    row["telefon"] = phone
    row["official_website"] = website

    if not ENABLE_GEMINI_ROW_CLEANUP:
        row["bundesland"] = extract_bundesland(row)
        return row

    api_key = get_google_ai_studio_api_key()
    if not api_key or is_gemini_rate_limited(cache):
        fallback = gemini_fallback_enrichment(row, company, address, phone, email, website)
        apply_gemini_enrichment_to_row(row, fallback)
        if cache_key:
            gemini_cache[cache_key] = fallback
        return row

    states = ", ".join(GERMAN_STATES)
    prompt = build_gemini_row_cleanup_prompt(
        company=company,
        address=address,
        phone=phone,
        email=email,
        website=website,
        states=states,
    )
    try:
        text, used_model = gemini_generate_text(prompt, logger, api_key, cache=cache)
        console_step(f"Gemini-Bereinigung Modell: {used_model}")
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        parsed = json.loads(match.group(0) if match else text)
        cleaned_name = finalize_company_name_for_export(
            parsed.get("company_name_clean", ""),
            fallback_raw=company,
            website=website,
            email=email,
        )
        gemini_result = {
            "company_name_clean": cleaned_name,
            "address": sanitize_special_text(parsed.get("address", address)) or address,
            "phone": sanitize_special_text(parsed.get("phone", phone)) or phone,
            "website": sanitize_special_text(parsed.get("website", website)) or website,
            "bundesland": sanitize_special_text(parsed.get("bundesland", "")),
        }
        if gemini_result["bundesland"] not in GERMAN_STATES:
            gemini_result["bundesland"] = extract_bundesland(row)
        apply_gemini_enrichment_to_row(row, gemini_result)
        if cache_key:
            gemini_cache[cache_key] = gemini_result
    except Exception as e:
        logger.warning(f"Gemini / województwo fallback ({cache_key}): {e}")
        fallback = gemini_fallback_enrichment(row, company, address, phone, email, website)
        apply_gemini_enrichment_to_row(row, fallback)
        if cache_key:
            gemini_cache[cache_key] = fallback
    return row


def _contact_context_text(row: dict) -> str:
    return " ".join(
        str(row.get(k) or "")
        for k in (
            "verification_reason",
            "page_snippet",
            "retail_chains_found",
            "kategoria",
            "nazwa",
        )
    )


def is_row_eligible_for_excel_export(row: dict) -> bool:
    """Firma do arkusza Kontakte — z mailem lub bez (gdy zweryfikowany Filialbau)."""
    name = (row.get("company_name_clean") or row.get("nazwa") or "").strip()
    url = (row.get("url") or row.get("www") or row.get("official_website") or "").strip()
    if name.lower() == "nieznana firma" and not url:
        return False
    email = (row.get("email_target") or "").strip()
    text = _contact_context_text(row)
    if is_excluded_kontrahent(name=name, url=url, email=email)[0]:
        return False
    if is_non_commercial_contact(email=email, url=url, name=name):
        return False
    if is_retail_store_operator_contact(url=url, email=email, text=text):
        return False
    if email:
        return not is_blocked_non_commercial_row(row)
    if not EXPORT_PIPELINE_ROWS_WITHOUT_EMAIL:
        return False
    if row.get("retail_verified") and has_retail_references_or_portfolio(text):
        return True
    return is_valid_retail_store_builder_contact(
        email="", url=url, name=name, text=text
    )


def build_export_rows(rows, logger=None, cache=None):
    export_rows = []
    for row in rows:
        row = normalize_row_company_name(row)
        if not is_row_eligible_for_excel_export(row):
            continue
        email = (row.get("email_target") or "").strip()
        if not email:
            found_list = [
                x.strip()
                for x in (row.get("emails_found") or "").split(",")
                if x.strip() and "@" in x
            ]
            if found_list:
                email, _ = pick_best_email_for_inquiry(
                    found_list,
                    row.get("official_website") or row.get("www") or "",
                )
        if not ENABLE_GEMINI_ROW_CLEANUP:
            row["adres"] = sanitize_special_text(
                row.get("full_address") or row.get("adres") or ""
            )
            row["telefon"] = sanitize_special_text(
                row.get("phones_found") or row.get("telefon") or ""
            )
            row["bundesland"] = extract_bundesland(row)
        website = (row.get("official_website") or row.get("www") or "").strip()
        address = (row.get("full_address") or row.get("adres") or "").strip()
        phone = (row.get("phones_found") or row.get("telefon") or "").strip()
        if "," in phone:
            phone = phone.split(",", 1)[0].strip()
        base = {
            "Nazwa firmy": (
                row.get("company_name_clean") or row.get("nazwa") or ""
            ).strip(),
            "Adres": address,
            "Bundesland": (row.get("bundesland") or extract_bundesland(row)).strip(),
            "Telefon": phone,
            "E-mail": email,
            "Strona www": website,
            "URL": (row.get("url") or "").strip(),
            "Handelsketten": (row.get("retail_chains_found") or "").strip(),
            "WWW_geprueft": "ja" if row.get("retail_verified") else "nein",
            "Kleinunternehmen": "ja" if row.get("is_small_firm") else "nein",
        }
        if cache is not None and email:
            base = merge_export_row(base, cache, email, lang="de")
        export_rows.append(base)
    if logger is not None:
        with_mail = sum(1 for r in export_rows if (r.get("E-mail") or "").strip())
        logger.info(
            "Excel Kontakte: %s wierszy (%s z e-mailem, %s bez) z %s w pipeline",
            len(export_rows),
            with_mail,
            len(export_rows) - with_mail,
            len(rows),
        )
    return export_rows


def build_bundesland_rows(rows):
    state_rows = []
    seen = set()
    for row in rows:
        row = normalize_row_company_name(row)
        row_url = (row.get("url") or "").strip()
        row_name = (row.get("company_name_clean") or row.get("nazwa") or "").strip()
        if row_name.lower() == "nieznana firma" and not row_url:
            continue
        row_state = (row.get("bundesland") or extract_bundesland(row)).strip()
        row_address = sanitize_special_text(row.get("full_address") or row.get("adres") or "")
        row_website = sanitize_special_text(
            row.get("official_website") or row.get("www") or ""
        )
        dedupe_key = row_url or f"{row_name}|{row_state}|{row_address}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        state_rows.append(
            {
                "Nazwa firmy": row_name,
                "Bundesland": row_state,
                "Adres": row_address,
                "Strona www": row_website,
                "URL": row_url,
            }
        )
    return state_rows


def persist_progress(all_rows, cache, logger: logging.Logger, reason: str = "") -> None:
    if reason:
        console_step(f"Zwischenstand speichern: {reason}")
    else:
        console_step("Zwischenstand speichern")
    save_excel(all_rows, OUTPUT_FILE, logger, cache=cache)
    save_cache(cache, logger)


EXCEL_IMPORT_COLUMNS = {
    "Nazwa firmy": "nazwa",
    "Adres": "adres",
    "Bundesland": "bundesland",
    "Telefon": "telefon",
    "E-mail": "email_target",
    "Strona www": "www",
    "URL": "url",
}


def row_from_excel_record(rec: dict) -> dict:
    """Mapuje polskie nagłówki z Excela na pola wewnętrzne scrapera."""
    row: dict = {}
    for col_pl, field in EXCEL_IMPORT_COLUMNS.items():
        for key in (col_pl, field):
            val = rec.get(key)
            if val is not None and str(val).strip():
                row[field] = normalize_unicode_text(val)
                break
    name = (row.get("nazwa") or "").strip()
    if name:
        row["company_name_raw"] = name
        row["company_name_clean"] = name
    if row.get("adres"):
        row["full_address"] = row["adres"]
    if row.get("telefon"):
        row["phones_found"] = row["telefon"]
    if row.get("www"):
        row["official_website"] = row["www"]
    return row


def load_existing_csv(path: Path, logger: logging.Logger):
    rows = []
    seen_urls = set()
    if not path.exists():
        return rows, seen_urls
    logger.info(f"Lade CSV: {path}")
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for r in reader:
            rows.append(r)
            if "url" in r and r["url"]:
                seen_urls.add(r["url"])
    logger.info(f"CSV geladen: {len(rows)} Zeilen, URLs={len(seen_urls)}")
    return rows, seen_urls


def load_existing_output(path: Path, logger: logging.Logger):
    if path.suffix.lower() != ".xlsx":
        return load_existing_csv(path, logger)
    rows = []
    seen_urls = set()
    if not path.exists():
        return rows, seen_urls
    logger.info(f"Lade XLSX: {path}")
    try:
        import pandas as pd  # pyright: ignore[reportMissingImports]

        try:
            df = pd.read_excel(path, sheet_name="Kontakte")
        except Exception:
            df = pd.read_excel(path)
        raw_records = df.fillna("").to_dict(orient="records")
        rows = []
        for rec in raw_records:
            row = row_from_excel_record(rec)
            if not row:
                continue
            name = (row.get("nazwa") or row.get("company_name_clean") or "").strip()
            if name.lower() == "nieznana firma" and not row.get("url"):
                continue
            rows.append(row)
            url = (row.get("url") or "").strip()
            if url:
                seen_urls.add(url)
        logger.info(f"XLSX geladen: {len(rows)} Zeilen, URLs={len(seen_urls)}")
    except Exception as e:
        logger.warning(f"XLSX-Ladefehler ({e}) – starte leer.")
    return rows, seen_urls


def _empty_cache() -> dict:
    return {
        "places": {},
        "contacts": {},
        "serper": {},
        "serper_daily": {},
        "email_daily": {},
        "email_sent_targets": {},
        "email_domain_daily": {},
        "email_suppression": {},
        "gemini_row_enrichment": {},
        "gemini_contact_text_clean": {},
        "gemini_email_text_clean": {},
        "gemini_disabled_models": {},
    }


def build_discovery_seen_urls(all_rows: list[dict], cache: dict) -> set[str]:
    """URL-e już w pipeline (Excel/wiersze). Opcjonalnie + contacts z JSON."""
    seen = {str(r.get("url") or "").strip() for r in all_rows if (r.get("url") or "").strip()}
    if not DISCOVERY_IGNORE_CONTACT_CACHE:
        for u in (cache.get("contacts") or {}):
            if u:
                seen.add(str(u).strip())
    return seen


def index_all_rows_by_url(all_rows: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in all_rows:
        url = str(row.get("url") or "").strip()
        if url:
            out[url] = row
    return out


def row_from_cache_contact(place_url: str, info: dict) -> dict | None:
    """Jeden rekord contacts JSON → wiersz pipeline (także bez e-mail)."""
    if not isinstance(info, dict):
        return None
    name = (
        info.get("company_name_clean")
        or info.get("company_name")
        or info.get("company_name_raw")
        or ""
    ).strip()
    email = (info.get("email_target") or "").strip()
    row_probe = {
        "url": place_url,
        "www": info.get("official_website") or place_url,
        "official_website": info.get("official_website") or place_url,
        "nazwa": name,
        "company_name_clean": name,
        "email_target": email,
        "emails_found": info.get("emails_found") or "",
        "retail_verified": info.get("retail_verified", False),
        "verification_reason": info.get("verification_reason") or "",
        "page_snippet": info.get("page_snippet") or "",
        "retail_chains_found": info.get("retail_chains_found") or "",
    }
    if not is_row_eligible_for_excel_export(row_probe):
        return None
    phone = (info.get("phones_found") or "").strip()
    if "," in phone:
        phone = phone.split(",", 1)[0].strip()
    return normalize_row_company_name(
        {
            **row_probe,
            "company_name_raw": info.get("company_name_raw") or name,
            "full_address": info.get("full_address") or "",
            "adres": info.get("full_address") or "",
            "telefon": phone,
            "phones_found": info.get("phones_found") or phone,
            "bundesland": info.get("bundesland") or "",
            "email_status": (info.get("email_status") or "").strip(),
            "contact_sources": info.get("contact_sources") or "",
            "is_small_firm": info.get("is_small_firm", True),
            "contact_quality_score": int(info.get("contact_quality_score", 0) or 0),
        }
    )


def build_all_rows_from_cache(cache: dict) -> list[dict]:
    """Rekonstruiert Pipeline-Zeilen aus contacts (mit und ohne E-Mail)."""
    rows: list[dict] = []
    for place_url, info in (cache.get("contacts") or {}).items():
        row = row_from_cache_contact(place_url, info)
        if row:
            rows.append(row)
    return rows


def merge_cache_contacts_into_pipeline(all_rows: list[dict], cache: dict) -> int:
    """Dopisuje/aktualizuje w pipeline wszystkie contacts z JSON (także bez maila)."""
    by_url = index_all_rows_by_url(all_rows)
    added = 0
    for place_url, info in (cache.get("contacts") or {}).items():
        row = row_from_cache_contact(place_url, info)
        if not row:
            continue
        url = row.get("url") or place_url
        if url in by_url:
            by_url[url].update(row)
        else:
            all_rows.append(row)
            by_url[url] = row
            added += 1
    return added


def load_cache(logger: logging.Logger) -> dict:
    if not CACHE_FILE.exists():
        logger.info("Kein Cache JSON – neuer Start.")
        return _empty_cache()
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
        for k in (
            "places",
            "contacts",
            "serper",
            "serper_daily",
            "email_daily",
            "email_sent_targets",
            "email_domain_daily",
            "email_suppression",
            "gemini_row_enrichment",
            "gemini_disabled_models",
        ):
            if k not in cache:
                cache[k] = {}
        logger.info(
            "Cache geladen: places=%s, contacts=%s",
            len(cache.get("places", {})),
            len(cache.get("contacts", {})),
        )
        if ENABLE_CACHE_PURGE_INSTITUTIONS:
            removed = purge_institutions_from_cache(cache, logger)
            if removed:
                save_cache(cache, logger)
        return cache
    except Exception as e:
        logger.warning(f"Cache-Ladefehler ({e}) – neuer Cache.")
        return _empty_cache()


def purge_institutions_from_cache(
    cache: dict, logger: logging.Logger | None = None
) -> int:
    """
    Usuwa z cache JSON wpisy urzędów/instytucji (contacts, serper, enrichment).
    Zwraca liczbę usuniętyych rekordów contacts.
    """
    contacts = cache.setdefault("contacts", {})
    if not isinstance(contacts, dict):
        cache["contacts"] = {}
        contacts = cache["contacts"]
    removed_urls: list[str] = []
    removed_emails: set[str] = set()
    for place_url in list(contacts.keys()):
        info = contacts.get(place_url)
        if (
            contact_info_excluded(info, place_url)
            or is_cache_contact_institution(place_url, info)
            or is_cache_contact_not_store_builder(place_url, info)
        ):
            removed_urls.append(place_url)
            if isinstance(info, dict):
                et = (info.get("email_target") or "").strip().lower()
                if et:
                    removed_emails.add(et)
                for part in (info.get("emails_found") or "").split(","):
                    p = part.strip().lower()
                    if p and "@" in p:
                        removed_emails.add(p)
            contacts.pop(place_url, None)

    serper = cache.get("serper") or {}
    if isinstance(serper, dict):
        for key in list(serper.keys()):
            if is_cache_serper_entry_institution(serper.get(key)):
                serper.pop(key, None)

    for url in removed_urls:
        for bucket in (
            "gemini_row_enrichment",
            "gemini_contact_text_clean",
            "gemini_email_text_clean",
        ):
            sub = cache.get(bucket)
            if not isinstance(sub, dict):
                continue
            for key in list(sub.keys()):
                if url in key or key in url:
                    sub.pop(key, None)
        # Stare kopie enrichment po URL jako klucz
        row_enrich = cache.get("gemini_row_enrichment")
        if isinstance(row_enrich, dict):
            row_enrich.pop(url, None)

    suppression = cache.get("email_suppression") or {}
    if isinstance(suppression, dict):
        for email in list(suppression.keys()):
            if is_non_commercial_email(email) or email in removed_emails:
                suppression.pop(email, None)
    sent_targets = cache.get("email_sent_targets") or {}
    if isinstance(sent_targets, dict):
        for day in list(sent_targets.keys()):
            targets = sent_targets.get(day)
            if not isinstance(targets, list):
                continue
            sent_targets[day] = [
                t for t in targets if (t or "").lower() not in removed_emails
            ]

    if logger and removed_urls:
        logger.info(
            "Cache: usunięto %s wpisów (urzędy / nie budują sklepów) z contacts (pozostało %s)",
            len(removed_urls),
            len(contacts),
        )
        print(
            f"[CACHE] Usunięto {len(removed_urls)} wpisów (urzędy / nie Filialbau) z JSON "
            f"(contacts: {len(contacts)})."
        )
    return len(removed_urls)


def save_cache(cache: dict, logger: logging.Logger) -> None:
    try:
        if ENABLE_CACHE_PURGE_INSTITUTIONS:
            purge_institutions_from_cache(cache, logger)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        logger.info(
            "Cache gespeichert: "
            f"places={len(cache.get('places', {}))}, "
            f"contacts={len(cache.get('contacts', {}))}, "
            f"serper={len(cache.get('serper', {}))}"
        )
    except Exception as e:
        logger.error(f"Cache-Schreibfehler: {e}")


def contact_validation_fields(
    info: dict | None, place_url: str = ""
) -> tuple[str, str, str, str]:
    """Spójny kontekst dla is_valid_retail_store_builder_contact (kolejka + wysyłka)."""
    if not isinstance(info, dict):
        info = {}
    email = (info.get("email_target") or "").strip()
    url = (info.get("official_website") or place_url or "").strip()
    name = (
        info.get("company_name_clean")
        or info.get("company_name")
        or info.get("company_name_raw")
        or ""
    ).strip()
    text = " ".join(
        str(info.get(k) or "")
        for k in (
            "verification_reason",
            "page_snippet",
            "retail_chains",
            "retail_chains_found",
            "serper_title",
            "serper_snippet",
        )
    )
    return email, url, name, text


def build_email_jobs_from_cache_json(
    logger: logging.Logger, *, force_resend: bool = False
):
    console_step("E-Mail-Warteschlange aus Cache JSON")
    if not CACHE_FILE.exists():
        logger.info("Kein Cache JSON – keine Mails.")
        return []
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.warning(f"Cache JSON Lesefehler: {e}")
        return []
    contacts = data.get("contacts", {}) if isinstance(data, dict) else {}
    jobs = []
    for place_url, info in contacts.items():
        if not isinstance(info, dict):
            continue
        email_target = (info.get("email_target") or "").strip()
        email_status = (info.get("email_status") or "").strip().lower()
        if not email_target:
            continue
        if contact_info_excluded(info, place_url):
            continue
        _em, _url, _name, _text = contact_validation_fields(info, place_url)
        if not is_valid_retail_store_builder_contact(
            email=email_target,
            url=_url,
            name=_name,
            text=_text,
        ):
            continue
        if email_status == "sent" and not force_resend:
            continue
        jobs.append(
            {
                "place_url": place_url,
                "email_target": email_target,
                "company_name": info.get("company_name", "Firma"),
                "contact_quality_score": int(info.get("contact_quality_score", 0) or 0),
            }
        )
    logger.info(f"Mail-Jobs aus JSON: {len(jobs)}")
    return jobs


def get_remaining_daily_email_limit(cache: dict):
    today = date.today().isoformat()
    daily = cache.setdefault("email_daily", {})
    sent_today = int(daily.get(today, 0))
    remaining = max(0, DAILY_EMAIL_LIMIT - sent_today)
    console_step(
        f"E-Mail-Limit {today}: gesendet={sent_today}, rest={remaining}, max={DAILY_EMAIL_LIMIT}"
    )
    return today, sent_today, remaining


def increase_daily_email_counter(cache: dict, increment: int = 1) -> None:
    today = date.today().isoformat()
    daily = cache.setdefault("email_daily", {})
    daily[today] = int(daily.get(today, 0)) + int(increment)


def get_email_domain(email_target: str) -> str:
    if "@" not in (email_target or ""):
        return ""
    return email_target.split("@", 1)[1].strip().lower()


def get_email_local_part(email_target: str) -> str:
    if "@" not in (email_target or ""):
        return ""
    return email_target.split("@", 1)[0].strip().lower()


def is_email_role_based_or_system(email_target: str) -> bool:
    if get_email_local_part(email_target) in SUPPRESSED_EMAIL_LOCALPARTS:
        return True
    if is_non_commercial_email(email_target):
        return True
    return is_unsuitable_inquiry_email(email_target)


def is_blocked_non_commercial_row(row: dict) -> bool:
    """Nie firma budująca sklepy (GU/Filialbau) — nie do zbierania, Excela ani wysyłki."""
    email = (row.get("email_target") or row.get("emails_found") or "").split(",")[0].strip()
    url = row.get("url") or row.get("www") or row.get("official_website") or ""
    name = row.get("company_name_clean") or row.get("nazwa") or row.get("company_name") or ""
    extra = " ".join(
        str(row.get(k) or "")
        for k in ("verification_reason", "page_snippet", "handelsketten", "retail_chains")
    )
    return not is_valid_retail_store_builder_contact(
        email=email, url=url, name=name, text=extra
    )


def is_within_send_window() -> bool:
    return _schedule_within_send_window(_SEND_WINDOW_CFG)


def get_domain_remaining_daily_limit(cache: dict, domain: str):
    today = date.today().isoformat()
    domain_daily = cache.setdefault("email_domain_daily", {}).setdefault(today, {})
    sent_for_domain = int(domain_daily.get(domain, 0))
    remaining = max(0, EMAIL_PER_DOMAIN_DAILY_LIMIT - sent_for_domain)
    return today, sent_for_domain, remaining


def increase_domain_daily_counter(cache: dict, domain: str, increment: int = 1) -> None:
    if not domain:
        return
    today = date.today().isoformat()
    domain_daily = cache.setdefault("email_domain_daily", {}).setdefault(today, {})
    domain_daily[domain] = int(domain_daily.get(domain, 0)) + int(increment)


def is_suppressed_target(cache: dict, email_target: str) -> bool:
    suppression = cache.setdefault("email_suppression", {})
    return email_target.lower() in suppression


def mark_suppressed_target(cache: dict, email_target: str, reason: str) -> None:
    if not email_target:
        return
    suppression = cache.setdefault("email_suppression", {})
    suppression[email_target.lower()] = {"reason": reason, "date": date.today().isoformat()}


def is_soft_bounce_or_spam_error(error_text: str) -> bool:
    lowered = (error_text or "").lower()
    if not lowered:
        return False
    markers = [
        "5.7.1",
        "likely unsolicited",
        "unsolicited mail",
        "message blocked",
        "blocked by policy",
        "mail rejected",
        "spam",
        "temporarily deferred",
        "try again later",
    ]
    return any(marker in lowered for marker in markers)


def sleep_between_emails(logger: logging.Logger, target_email: str) -> None:
    delay = round(random.uniform(EMAIL_SEND_DELAY_MIN_SECONDS, EMAIL_SEND_DELAY_MAX_SECONDS), 1)
    console_step(f"Anti-Spam Pause vor nächster Mail ({target_email}): {delay}s")
    logger.info(f"Email jitter sleep={delay}s target={target_email}")
    time.sleep(delay)


def sanitize_generated_email(subject: str, body: str, company_name: str):
    clean_subject = (subject or "").strip()
    clean_body = (body or "").strip()
    if not clean_subject:
        clean_subject = choose_subject_variant(company_name)
    clean_subject = re.sub(r"\+?\d[\d\s()./-]{5,}\d", "", clean_subject)
    clean_subject = clean_subject.replace("!", "").replace("?", "")
    clean_subject = clean_subject[:95].strip(" -")
    lowered_subject = clean_subject.lower()
    if any(term in lowered_subject for term in EMAIL_SPAMMY_TERMS):
        clean_subject = choose_subject_variant(company_name)
    lowered_body = clean_body.lower()
    for term in EMAIL_SPAMMY_TERMS:
        if term in lowered_body:
            clean_body = re.sub(term, "", clean_body, flags=re.IGNORECASE)
    clean_body = re.sub(r"\n{3,}", "\n\n", clean_body).strip()
    return clean_subject, clean_body


def sanitize_sender_name(sender_name: str) -> str:
    text = (sender_name or "").strip()
    if not text:
        return "Maksym Swinczak, MFG Modernerfliesenboden GmbH"
    text = re.sub(r"\b(tel|telefon)\b.*$", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"https?://\S+|\bwww\.\S+|\S+@\S+", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"\+?\d[\d\s()./-]{5,}\d", "", text).strip()
    text = re.sub(r"\s+", " ", text).strip(" ,;-")
    if not text:
        return "Maksym Swinczak, MFG Modernerfliesenboden GmbH"
    m = re.search(r"\bGmbH\b", text, flags=re.IGNORECASE)
    if m:
        text = text[: m.end()].strip(" ,;-")
    return text


def was_email_target_sent_today(cache: dict, email_target: str) -> bool:
    if not email_target:
        return False
    today = date.today().isoformat()
    sent_targets = cache.setdefault("email_sent_targets", {}).setdefault(today, [])
    return email_target.lower() in {x.lower() for x in sent_targets}


def mark_email_target_sent_today(cache: dict, email_target: str) -> None:
    if not email_target:
        return
    today = date.today().isoformat()
    sent_targets = cache.setdefault("email_sent_targets", {}).setdefault(today, [])
    lowered = email_target.lower()
    if lowered not in {x.lower() for x in sent_targets}:
        sent_targets.append(lowered)


def get_remaining_daily_serper_limit(cache: dict):
    today = date.today().isoformat()
    daily = cache.setdefault("serper_daily", {})
    used_today = int(daily.get(today, 0))
    remaining = max(0, SERPER_DAILY_LIMIT - used_today)
    console_step(
        f"Serper-Limit {today}: genutzt={used_today}, rest={remaining}, max={SERPER_DAILY_LIMIT}"
    )
    return today, used_today, remaining


def increase_daily_serper_counter(cache: dict, increment: int = 1) -> None:
    today = date.today().isoformat()
    daily = cache.setdefault("serper_daily", {})
    daily[today] = int(daily.get(today, 0)) + int(increment)


def is_serper_limit_reached_today(cache: dict) -> bool:
    today, _, remaining = get_remaining_daily_serper_limit(cache)
    flags = cache.setdefault("serper_limit_reached", {})
    if flags.get(today):
        return True
    if remaining <= 0:
        flags[today] = True
        return True
    return False


def mark_serper_limit_reached_today(cache: dict) -> None:
    today = date.today().isoformat()
    flags = cache.setdefault("serper_limit_reached", {})
    flags[today] = True


def request_with_retry(
    method,
    url: str,
    logger: logging.Logger,
    *,
    retry_on_rate_limit: bool = True,
    waf_skip: bool = False,
    **kwargs,
):
    from http_page_guard import PageAccessBlocked, is_waf_blocked, waf_block_reason

    last_err = None
    safe_url = sanitize_log_url(url)
    for attempt in range(1, HTTP_RETRY_ATTEMPTS + 1):
        try:
            response = method(url, **kwargs)
            if waf_skip and is_waf_blocked(response=response):
                reason = waf_block_reason(response=response)
                logger.info(
                    "WAF/Cloudflare — pomijam (bez retry): %s [%s]",
                    safe_url,
                    reason,
                )
                raise PageAccessBlocked(f"{safe_url}: {reason}")
            response.raise_for_status()
            if waf_skip:
                body = getattr(response, "text", "") or ""
                if is_waf_blocked(response=response, html=body):
                    reason = waf_block_reason(response=response, html=body)
                    logger.info(
                        "WAF/Cloudflare (treść) — pomijam: %s [%s]",
                        safe_url,
                        reason,
                    )
                    raise PageAccessBlocked(f"{safe_url}: {reason}")
            return response
        except PageAccessBlocked:
            raise
        except Exception as e:
            last_err = e
            if waf_skip and is_waf_blocked(exc=e):
                reason = waf_block_reason(exc=e)
                logger.info(
                    "WAF/Cloudflare — pomijam (bez retry): %s [%s]",
                    safe_url,
                    reason,
                )
                raise PageAccessBlocked(f"{safe_url}: {reason}") from e
            console_step(f"HTTP Retry {attempt}/{HTTP_RETRY_ATTEMPTS} {safe_url}: {e}")
            if _is_rate_limit_error(e) and not retry_on_rate_limit:
                break
            if attempt < HTTP_RETRY_ATTEMPTS:
                backoff = HTTP_BACKOFF_SECONDS * attempt
                if _is_rate_limit_error(e):
                    backoff = max(backoff, 30 * attempt)
                time.sleep(backoff)
    logger.warning(f"HTTP endgültig fehlgeschlagen: {safe_url}: {last_err}")
    if last_err is not None:
        raise last_err
    raise RuntimeError("request_with_retry ohne Antwort")


def choose_subject_variant(company_name: str) -> str:
    _ = company_name
    return FIXED_EMAIL_SUBJECT_DE


def choose_prompt_variant(company_name: str) -> str:
    idx = abs(hash((company_name or "") + "_prompt")) % len(PROMPT_VARIANTS)
    return PROMPT_VARIANTS[idx]


def _domain_from_url(url: str) -> str:
    try:
        host = (urlparse(normalize_website(url)).netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


def is_likely_large_company(
    company_name: str = "",
    website: str = "",
    page_text: str = "",
    serper_blob: str = "",
) -> tuple[bool, str]:
    """True = duży koncern / do odrzucenia."""
    blob = " ".join(
        [company_name or "", website or "", page_text or "", serper_blob or ""]
    ).lower()
    domain = _domain_from_url(website)
    for blocked in LARGE_COMPANY_DOMAINS:
        if blocked in domain or blocked in blob:
            return True, f"grosses_unternehmen_domain:{blocked}"
    for marker in LARGE_COMPANY_NAME_MARKERS:
        if marker in blob:
            if marker.strip() in (" se ", " gmbh & co. kg"):
                if any(
                    x in blob
                    for x in ("konzern", "weltweit", "börsennotiert", "holding")
                ):
                    return True, f"grosses_unternehmen_name:{marker.strip()}"
            else:
                return True, f"grosses_unternehmen_name:{marker}"
    large_page_hits = sum(1 for m in LARGE_COMPANY_PAGE_MARKERS if m in blob)
    small_hits = sum(1 for m in SMALL_COMPANY_PAGE_MARKERS if m in blob)
    if large_page_hits >= 2 and small_hits == 0:
        return True, "grosses_unternehmen_seite"
    if large_page_hits >= 3:
        return True, "grosses_unternehmen_seite_stark"
    return False, ""


def detect_retail_chains_in_text(text: str) -> list[str]:
    low = (text or "").lower()
    return [c for c in RETAIL_CHAIN_KEYWORDS if c in low]


def page_mentions_retail_store_projects(text: str) -> tuple[bool, list[str], str]:
    """
    GU/Filialbau (Neubau/Umbau Märkte) + dowód projektów marketów (Referenzen, Portfolio oder Fotos).
    """
    low = (text or "").lower()
    if is_retail_store_operator_contact(text=low):
        return False, [], "einzelhandel_betrieb_kein_bau"
    if not mentions_retail_store_build_activity_core(low):
        return False, [], "kein_gu_filialbau_kontext"
    if REQUIRE_MARKET_PROJECTS_IN_PORTFOLIO and not has_retail_references_or_portfolio(
        low
    ):
        return False, [], "kein_markt_nachweis"

    chains = detect_retail_chains_in_text(low)
    has_build = any(k in low for k in RETAIL_BUILD_KEYWORDS)
    has_ref = has_retail_references_or_portfolio(low)
    has_trade = any(k in low for k in RETAIL_TRADE_ACTIVITY_KEYWORDS)
    has_gu_bau = any(k in low for k in GU_ROLE_KEYWORDS) or "bauunternehmen" in low
    has_umbau = any(
        k in low
        for k in (
            "umbau",
            "modernisierung",
            "revitalisierung",
            "filialumbau",
            "marktumbau",
            "filialsanierung",
        )
    )

    if has_ref and chains and has_build:
        return True, chains, "kette_referenz_ladenbau"
    if has_ref and chains:
        return True, chains, "kette_und_referenz"
    if has_ref and has_umbau and has_trade:
        return True, chains, "referenz_filialumbau"
    if has_ref and has_build and has_gu_bau:
        return True, chains, "referenz_gu_filialbau"
    if has_ref and has_trade:
        return True, chains, "referenz_einzelhandel"
    if has_ref and has_build:
        return True, chains, "referenz_ladenbau"
    return False, chains, "keine_referenzen_portfolio"


def sort_verification_urls(urls: list[str]) -> list[str]:
    def key(u: str) -> tuple[int, str]:
        low = u.lower()
        if any(x in low for x in RETAIL_URL_PRIORITY_KEYWORDS):
            return (0, low)
        if any(x in low for x in ("ueber-uns", "über-uns", "unternehmen", "about")):
            return (1, low)
        if _is_impressum_url(low):
            return (1, low)
        if any(x in low for x in ("kontakt", "contact", "impressum")):
            return (2, low)
        return (3, low)

    return sorted(urls, key=key)


def gather_website_text_for_verification(
    website: str, logger: logging.Logger
) -> tuple[str, list[str]]:
    """Pobiera tekst ze strony głównej i kilku podstron (referenzen/projekte) — przed kontaktami."""
    website = normalize_website(website)
    if not website:
        return "", []
    console_step(f"WWW-Prüfung (GU Filialbau/Umbau Markt): {website}")
    home = parse_contacts_from_page(website, logger)
    parts = [home.get("page_text") or ""]
    visited = {website}
    extra_urls = sort_verification_urls(home.get("contact_urls") or [])
    for u in extra_urls:
        if len(visited) >= MAX_PAGES_FOR_RETAIL_VERIFICATION:
            break
        if u in visited:
            continue
        visited.add(u)
        sub = parse_contacts_from_page(u, logger)
        if sub.get("page_text"):
            parts.append(sub["page_text"])
    return " ".join(parts), list(visited)


def gemini_verify_retail_small_company(
    company_name: str,
    website: str,
    page_text: str,
    logger: logging.Logger,
    cache: dict | None,
    *,
    cache_key: str = "",
) -> dict:
    """Gemini: czy firma to mały/średni GU z referencjami sklepów dyskontowych."""
    out = {
        "verified": False,
        "is_small_firm": False,
        "retail_chains": [],
        "reason": "gemini_off",
    }
    if not ENABLE_GEMINI_RETAIL_VERIFICATION:
        return out
    api_key = get_google_ai_studio_api_key()
    if not api_key or is_gemini_rate_limited(cache):
        return out

    verify_cache = (cache or {}).setdefault("gemini_retail_verify", {})
    if cache_key and cache_key in verify_cache:
        return dict(verify_cache[cache_key])

    snippet = _truncate_page_snippet(page_text, max_chars=5000)
    chains_list = ", ".join(RETAIL_CHAIN_KEYWORDS)
    prompt = (
        "Du bist Analyst für B2B-Bau. Prüfe den Website-Auszug.\n"
        "Fragen:\n"
        f"1) Baut/realisiert die Firma Filialen oder Märkte von Discountern/Supermärkten "
        f"({chains_list}) als Bauunternehmen oder Generalunternehmer?\n"
        "2) Ist es eher ein kleines oder mittelständisches regionales Unternehmen "
        "(KEIN internationaler Konzern wie STRABAG, Hochtief, Bilfinger)?\n"
        "Antwort NUR als JSON:\n"
        '{"verified":true/false,"is_small_firm":true/false,'
        '"retail_chains":["aldi",...],"reason":"kurz DE"}\n'
        "verified=true nur wenn klare Hinweise auf Ladenbau/Filialbau/Referenzprojekte "
        "für genannte Handelsketten.\n"
        f"Firma: {company_name}\nWebseite: {website}\n\nAuszug:\n{snippet or '(leer)'}"
    )
    try:
        text, used_model = gemini_generate_text(prompt, logger, api_key, cache=cache)
        console_step(f"Gemini WWW-Prüfung Ladenbau, Modell: {used_model}")
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        parsed = json.loads(match.group(0) if match else text)
        out = {
            "verified": bool(parsed.get("verified")),
            "is_small_firm": bool(parsed.get("is_small_firm")),
            "retail_chains": [
                str(c).lower()
                for c in (parsed.get("retail_chains") or [])
                if str(c).strip()
            ],
            "reason": str(parsed.get("reason") or "gemini"),
        }
        if cache_key:
            verify_cache[cache_key] = out
    except Exception as e:
        logger.warning(f"Gemini WWW-Prüfung: {e}")
        out["reason"] = f"gemini_error:{e}"
    return out


def verify_company_on_website(
    company_name: str,
    website: str,
    logger: logging.Logger,
    cache: dict | None,
    *,
    serper_blob: str = "",
    cache_key: str = "",
) -> dict:
    """
    Wchodzi na stronę, sprawdza mała firma + sklepy dyskontowe.
    Zwraca m.in. verified, retail_chains, verification_reason.
    """
    page_text, pages_checked = gather_website_text_for_verification(website, logger)
    blob = " ".join([page_text, serper_blob])
    large, large_reason = is_likely_large_company(
        company_name, website, page_text, serper_blob
    )
    if large:
        return {
            "verified": False,
            "is_small_firm": False,
            "retail_chains": [],
            "verification_reason": large_reason,
            "verification_method": "rules",
            "pages_checked": pages_checked,
            "page_snippet": _truncate_page_snippet(page_text),
        }

    rules_ok, chains, rules_reason = page_mentions_retail_store_projects(page_text)
    small_hint = any(m in blob.lower() for m in SMALL_COMPANY_PAGE_MARKERS)
    is_small = small_hint or not large

    if rules_ok and is_small:
        return {
            "verified": True,
            "is_small_firm": True,
            "retail_chains": chains,
            "verification_reason": rules_reason,
            "verification_method": "bs4_rules",
            "pages_checked": pages_checked,
            "page_snippet": _truncate_page_snippet(page_text),
        }

    if not rules_ok and serper_blob.strip():
        rules_ok2, chains2, rules_reason2 = page_mentions_retail_store_projects(
            serper_blob
        )
        if rules_ok2 and is_small:
            return {
                "verified": True,
                "is_small_firm": True,
                "retail_chains": chains2,
                "verification_reason": f"serper_snippet:{rules_reason2}",
                "verification_method": "bs4_rules",
                "pages_checked": pages_checked,
                "page_snippet": _truncate_page_snippet(page_text),
            }
        chains = chains or chains2
        rules_reason = rules_reason2 if not rules_ok else rules_reason

    reason = rules_reason if not rules_ok else (large_reason or "nicht_klein")
    if not is_small:
        reason = large_reason or "nicht_klein"
    return {
        "verified": False,
        "is_small_firm": is_small,
        "retail_chains": chains,
        "verification_reason": reason,
        "verification_method": "bs4_rules",
        "pages_checked": pages_checked,
        "page_snippet": _truncate_page_snippet(page_text),
    }


def score_serper_candidate(link: str, title: str = "", snippet: str = "", company_name: str = "") -> int:
    text = " ".join([link or "", title or "", snippet or ""]).lower()
    score = 0
    if not link:
        return -999
    if any(bad in text for bad in SERPER_BAD_DOMAINS):
        score -= 120
    if "impressum" in text or "kontakt" in text or "contact" in text:
        score += 22
    for term in SERPER_POSITIVE_TERMS:
        if term in text:
            score += 8
    for term in SERPER_NEGATIVE_TERMS:
        if term in text:
            score -= 35
    if company_name:
        tokens = [t for t in re.split(r"\W+", company_name.lower()) if len(t) >= 4]
        score += sum(12 for t in tokens if t in text)
    for term in SMALL_COMPANY_DISCOVERY_TERMS:
        if term in text:
            score += 10
    if is_likely_large_company(company_name, link, text)[0]:
        score -= 200
    if not is_valid_retail_store_builder_contact(
        url=link, name=title or company_name, email="", text=text
    ):
        score -= 400
    if link.startswith("https://"):
        score += 5
    if "/maps/" in link:
        score -= 80
    return score


def is_germany_de_candidate(link: str, title: str = "", snippet: str = "") -> bool:
    if COUNTRY_RESTRICTION != "DE":
        return True
    dom = get_registrable_domain(link or "")
    if dom in AGGREGATOR_EMAIL_DOMAINS:
        return False
    text = " ".join([link or "", title or "", snippet or ""]).lower()
    if any(x in text for x in NON_DE_FOREIGN_HINTS):
        return False
    if ".de/" in text or text.endswith(".de"):
        return True
    if any(x in text for x in DE_COUNTRY_HINTS):
        return True
    return True


def compute_contact_quality_score(row: dict) -> int:
    score = 0
    if row.get("email_target"):
        score += 45
        email_sc = int(row.get("email_target_score", 0) or 0)
        score += min(25, max(0, email_sc // 2))
    if row.get("phones_found"):
        score += 20
    if row.get("official_website"):
        score += 20
    if row.get("full_address") or row.get("adres"):
        score += 10
    serper_score = int(row.get("serper_source_score", 0) or 0)
    score += min(15, max(0, serper_score // 5))
    return score


def normalize_website(url: str) -> str:
    if not url:
        return ""
    u = url.strip()
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    return u


def derive_name_from_website(website: str) -> str:
    normalized = normalize_website(website)
    if not normalized:
        return ""
    try:
        host = (urlparse(normalized).netloc or "").lower()
    except Exception:
        return ""
    if host.startswith("www."):
        host = host[4:]
    if not host:
        return ""
    root = host.split(".")[0]
    root = re.sub(r"[^a-z0-9-]+", " ", root, flags=re.IGNORECASE)
    root = root.replace("-", " ")
    root = " ".join(root.split()).strip()
    if not root:
        return ""
    return " ".join(part.capitalize() for part in root.split())


_RETAIL_CHAIN_IN_NAME = (
    "edeka",
    "rewe",
    "netto",
    "aldi",
    "penny",
    "lidl",
    "kaufland",
    "marktkauf",
)
_GENERIC_DOMAIN_ROOTS = frozenset(
    {"google", "facebook", "linkedin", "xing", "wikipedia", "youtube"}
)


def website_base_url(url: str) -> str:
    """Kanoniczna domena firmy: https://nazwa.de (bez ścieżki /referenz/…)."""
    domain = _domain_from_url(url)
    return f"https://{domain}" if domain else normalize_website(url)


def _name_aligns_with_domain(name: str, website: str) -> bool:
    domain_name = derive_name_from_website(website).lower()
    if not domain_name:
        return False
    name_low = (name or "").lower()
    for token in domain_name.split():
        if len(token) >= 4 and token in name_low:
            return True
    domain_root = (_domain_from_url(website) or "").split(".")[0]
    compact_name = re.sub(r"[^a-z0-9]", "", name_low)
    compact_root = re.sub(r"[^a-z0-9]", "", domain_root.lower())
    return len(compact_root) >= 4 and compact_root in compact_name


def should_prefer_domain_company_name(raw_name: str, website: str) -> bool:
    """True = nazwa z www.firma.de zamiast tytułu artykułu / nazwy marketu."""
    raw = " ".join((raw_name or "").split()).strip()
    domain_name = derive_name_from_website(website)
    if not domain_name:
        return False
    domain_root = (_domain_from_url(website) or "").split(".")[0].lower()
    if domain_root in _GENERIC_DOMAIN_ROOTS:
        return False
    if not raw:
        return True
    if _name_aligns_with_domain(raw, website):
        return False
    low = raw.lower()
    if low.startswith(("by ", "von ")):
        return True
    if "," in raw and any(m in low for m in _RETAIL_CHAIN_IN_NAME):
        return True
    if any(m in low for m in _RETAIL_CHAIN_IN_NAME) and not any(
        m in domain_root for m in _RETAIL_CHAIN_IN_NAME
    ):
        return True
    if not _company_name_has_legal_form(raw) and len(raw.split()) >= 3:
        return True
    return False


def clean_company_name(name: str, website: str = "") -> str:
    website = website_base_url(website) if website else ""
    raw = " ".join((name or "").split()).strip(" -|–—")
    text = raw
    if text:
        text = re.split(r"\s+[|–—-]\s+", text, maxsplit=1)[0].strip()
        text = re.sub(
            r"\s+(startseite|homepage|home|wikipedia|firmenliste|hersteller)\s*$",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
    if text and website and should_prefer_domain_company_name(text, website):
        domain_name = derive_name_from_website(website)
        if domain_name:
            return domain_name
    if not text:
        text = derive_name_from_website(website)
    return text or "Unbekanntes Unternehmen"


def normalize_row_company_name(row: dict) -> dict:
    raw_name = (row.get("nazwa") or row.get("company_name_raw") or "").strip()
    website_hint = website_base_url(
        row.get("official_website") or row.get("www") or row.get("url") or ""
    )
    clean_name = clean_company_name(raw_name, website_hint)
    row["company_name_raw"] = raw_name
    row["company_name_clean"] = clean_name
    row["nazwa"] = clean_name
    return row


def ensure_ssl_cert_env(logger=None) -> None:
    if os.getenv("SSL_CERT_FILE"):
        return
    try:
        import certifi

        cert_path = (certifi.where() or "").strip()
        if not cert_path:
            return
        os.environ["SSL_CERT_FILE"] = cert_path
        os.environ.setdefault("REQUESTS_CA_BUNDLE", cert_path)
        msg = f"SSL_CERT_FILE gesetzt (certifi): {cert_path}"
        if logger:
            logger.info(msg)
        else:
            console_step(msg)
    except Exception as e:
        if logger:
            logger.warning(f"certifi SSL nicht gesetzt: {e}")


def get_gemini_model_candidates() -> list[str]:
    models = []
    for raw in (GEMINI_MODELS or "").split(","):
        model = raw.strip()
        if model and model not in models:
            models.append(model)
    if not models and GEMINI_MODEL:
        models.append(GEMINI_MODEL)
    return models


def get_disabled_gemini_models(cache: dict | None) -> set[str]:
    if cache is None:
        return set()
    disabled = cache.setdefault("gemini_disabled_models", {})
    return {m for m, meta in disabled.items() if isinstance(meta, dict) and meta.get("disabled")}


def mark_gemini_model_disabled(cache: dict | None, model: str, reason: str) -> None:
    if cache is None or not model:
        return
    disabled = cache.setdefault("gemini_disabled_models", {})
    disabled[model] = {"disabled": True, "reason": reason, "date": date.today().isoformat()}


def gemini_generate_text(prompt: str, logger: logging.Logger, api_key: str, cache=None):
    if is_gemini_rate_limited(cache):
        raise RuntimeError("Gemini API pausiert (Rate-Limit-Cooldown aktiv).")
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    last_err = None
    disabled_models = get_disabled_gemini_models(cache)
    seen_active_model = False
    for model in get_gemini_model_candidates():
        if model in disabled_models:
            continue
        if seen_active_model:
            console_step(
                f"Gemini: Pause {GEMINI_INTER_MODEL_DELAY_SECONDS}s vor nächstem Modell ({model})"
            )
            time.sleep(GEMINI_INTER_MODEL_DELAY_SECONDS)
        seen_active_model = True
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )
        try:
            wait_for_gemini_slot(cache)
            touch_gemini_call(cache)
            resp = request_with_retry(
                requests.post,
                endpoint,
                logger,
                json=payload,
                timeout=REQUEST_TIMEOUT,
                retry_on_rate_limit=False,
            )
            data = resp.json()
            text = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )
            if text:
                return text, model
        except Exception as e:
            last_err = e
            logger.warning(f"Gemini Modell {model} fehlgeschlagen: {e}")
            err_text = str(e).lower()
            if "404" in err_text or "not found" in err_text:
                mark_gemini_model_disabled(cache, model, str(e))
            if _is_rate_limit_error(e):
                mark_gemini_rate_limited(cache, logger)
                break
            continue
    raise last_err or RuntimeError("Keine Gemini-Antwort für alle Modelle.")


def prepare_text_for_email_extraction(text: str) -> str:
    """Obfuskation DE/PL: (at), punkt/dot, Leerzeichen um @ → normalisieren."""
    if not text:
        return ""
    t = unquote(text)
    t = t.replace("%40", "@").replace("&#64;", "@").replace("&commat;", "@")
    for pat in (
        r"\(\s*at\s*\)",
        r"\[\s*at\s*\]",
        r"\{\s*at\s*\}",
        r"\(\s*ät\s*\)",
        r"\(\s*a\s*t\s*\)",
        r"<\s*at\s*>",
        r"/\s*at\s*/",
    ):
        t = re.sub(pat, "@", t, flags=re.IGNORECASE)
    t = re.sub(
        r"\b([A-Za-z0-9._%+\-]{1,96})\s*(?:at|ät|a\s*t)\s*([A-Za-z0-9.\-]{1,240})\b",
        r"\1@\2",
        t,
        flags=re.IGNORECASE,
    )
    for dot_pat in (
        r"\(\s*dot\s*\)",
        r"\[\s*dot\s*\]",
        r"\(\s*punkt\s*\)",
        r"\[\s*punkt\s*\]",
        r"\s+dot\s+",
        r"\s+punkt\s+",
    ):
        t = re.sub(dot_pat, ".", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*@\s*", "@", t)
    t = re.sub(r"([A-Za-z0-9])\s+\.\s+([A-Za-z0-9])", r"\1.\2", t)
    t = re.sub(r"\.{2,}", ".", t)
    return t


_RELAXED_EMAIL_REGEXES = (
    # Standard + zweite TLD (z. B. co.uk)
    re.compile(
        r"[A-Za-z0-9][A-Za-z0-9._%+\-]*@"
        r"[A-Za-z0-9][A-Za-z0-9.\-]*\.[A-Za-z]{2,}(?:\.[A-Za-z]{2,})?",
        re.IGNORECASE,
    ),
    # Kurze TLD / IDN-ähnlich (mind. 2 Zeichen nach letztem Punkt)
    re.compile(
        r"[A-Za-z0-9][A-Za-z0-9._%+\-]*@[A-Za-z0-9][A-Za-z0-9.\-]*\.[A-Za-z0-9\-]{2,24}",
        re.IGNORECASE,
    ),
    # Sehr locker: alles mit @ und mindestens einem Punkt in der Domain
    re.compile(
        r"[A-Za-z0-9][\w.%+\-]{0,96}@[A-Za-z0-9][\w.\-]{0,240}\.[A-Za-z0-9]{2,24}",
        re.IGNORECASE,
    ),
)

_FAKE_EMAIL_SUFFIXES = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".css",
    ".js",
    ".woff",
    ".woff2",
)


def _normalize_relaxed_email(raw: str) -> str:
    low = unquote((raw or "").strip()).lower()
    low = low.replace("%40", "@")
    low = re.sub(r"^mailto:\s*", "", low)
    low = low.split("?")[0].split("#")[0]
    low = low.strip(".,;:()[]{}<>\"'`")
    if "@" not in low:
        return ""
    local, _, domain = low.partition("@")
    local, domain = local.strip(), domain.strip().rstrip(".")
    if not local or not domain or "." not in domain:
        return ""
    if any(domain.endswith(suf) for suf in _FAKE_EMAIL_SUFFIXES):
        return ""
    if len(local) > 96 or len(domain) > 253:
        return ""
    return f"{local}@{domain}"


def _extract_emails_with_relaxed_regex(text: str) -> list[str]:
    if not text:
        return []
    prepared = prepare_text_for_email_extraction(text)
    seen: list[str] = []
    for rx in _RELAXED_EMAIL_REGEXES:
        for match in rx.findall(prepared):
            norm = _normalize_relaxed_email(match)
            if norm and norm not in seen:
                seen.append(norm)
    return seen


def gemini_clean_text_for_contact_extraction(
    text: str,
    page_url: str,
    logger: logging.Logger,
    cache: dict | None,
) -> str:
    """
    Gemini normalisiert Kontakt-Text (Firma, E-Mails, Telefon) vor dem Regex.
    Nichts erfinden — nur Entschleierung und Lesbarkeit aus dem Eingabetext.
    """
    if not ENABLE_GEMINI_CONTACT_TEXT_CLEANUP or not (text or "").strip():
        return ""
    api_key = get_google_ai_studio_api_key()
    if not api_key or is_gemini_rate_limited(cache):
        return ""
    snippet = re.sub(r"\s+", " ", text.strip())
    if len(snippet) > GEMINI_CONTACT_TEXT_MAX_INPUT_CHARS:
        snippet = snippet[: GEMINI_CONTACT_TEXT_MAX_INPUT_CHARS - 3] + "..."
    cache_bucket = (cache or {}).setdefault("gemini_contact_text_clean", {})
    legacy = (cache or {}).get("gemini_email_text_clean") or {}
    digest = hashlib.sha256(f"{page_url}|{snippet[:1200]}".encode("utf-8")).hexdigest()[:24]
    if digest in cache_bucket:
        return cache_bucket[digest] or ""
    if digest in legacy:
        cache_bucket[digest] = legacy[digest]
        return legacy[digest] or ""
    prompt = (
        "Du bereinigst einen Webseiten-Auszug (Bau/GU, Kontakt/Impressum). NUR diese Zeilen, nichts erfinden.\n"
        "Firma: NUR echter Firmenname + Rechtsform (GmbH/UG/AG/…). "
        "LEER lassen bei PDF, PDF-XChange/Software, Vergabemarktplatz, [PDF], reinen Städten, "
        "News-Überschriften, Katalogen, ALDI/Penny-Projekttiteln ohne Baufirma.\n"
        "E-Mail: alle Adressen mit @, Semikolon-getrennt.\n"
        "Telefon: deutsche Nummern (+49/0…), Semikolon-getrennt.\n"
        f"URL: {page_url or 'unbekannt'}\n"
        f"Text:\n{snippet}"
    )
    try:
        cleaned, used_model = gemini_generate_text(prompt, logger, api_key, cache=cache)
        cleaned = (cleaned or "").strip()
        console_step(f"Gemini Kontakt-Textbereinigung: {used_model}")
        cache_bucket[digest] = cleaned
        return cleaned
    except Exception as e:
        logger.warning(f"Gemini Kontakt-Textbereinigung fehlgeschlagen ({page_url}): {e}")
        cache_bucket[digest] = ""
        return ""


def gemini_clean_text_for_email_extraction(
    text: str,
    page_url: str,
    logger: logging.Logger,
    cache: dict | None,
) -> str:
    """Alias — ein Aufruf für Firma, E-Mail und Telefon."""
    return gemini_clean_text_for_contact_extraction(text, page_url, logger, cache)


def _resolve_contact_source_text(
    text: str,
    *,
    logger: logging.Logger | None = None,
    cache: dict | None = None,
    page_url: str = "",
    gemini_buf: dict | None = None,
) -> str:
    """Ein Gemini-Lauf pro Seite; Ergebnis für E-Mail-, Telefon- und Firmen-Regex."""
    if not text:
        return ""
    if gemini_buf is not None and "resolved" in gemini_buf:
        return gemini_buf["resolved"]
    source = text
    if ENABLE_GEMINI_CONTACT_TEXT_CLEANUP and logger is not None:
        gemini_text = gemini_clean_text_for_contact_extraction(
            text, page_url, logger, cache
        )
        if gemini_text:
            source = gemini_text
    if gemini_buf is not None:
        gemini_buf["resolved"] = source
    return source


def find_emails_in_text(
    text: str,
    *,
    logger: logging.Logger | None = None,
    cache: dict | None = None,
    page_url: str = "",
    gemini_buf: dict | None = None,
) -> list[str]:
    """
    Pipeline: Gemini bereinigt Text → maximal lockeres Regex.
    mailto:-Links werden separat in parse_contacts_from_html ergänzt.
    """
    if not text:
        return []
    source = _resolve_contact_source_text(
        text, logger=logger, cache=cache, page_url=page_url, gemini_buf=gemini_buf
    )
    found = _extract_emails_with_relaxed_regex(source)
    if not found:
        for e in _extract_emails_with_relaxed_regex(text):
            if e not in found:
                found.append(e)
    return filter_commercial_emails(found)


_COMPANY_LEGAL_SUFFIX = (
    r"(?:GmbH|UG(?:\s*\(haftungsbeschränkt\))?|AG|GbR|e\.?\s*K\.?|KG|OHG|PartG|mbH|Co\.\s*KG)"
)
_RELAXED_COMPANY_REGEXES = (
    re.compile(
        rf"([A-ZÄÖÜ0-9][\wäöüßÄÖÜ&\.\-'„“ ]{{1,100}}?\s+{_COMPANY_LEGAL_SUFFIX})\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:Firma|FIRMA|Unternehmen|Company)\s*:\s*([^\n;|]+)",
        re.IGNORECASE,
    ),
)

_RELAXED_PHONE_REGEXES = (
    re.compile(r"\+49[\s(]?\d{2,5}[\s)./-]*\d[\d\s()./-]{4,18}"),
    re.compile(r"0049[\s(]?\d{2,5}[\s)./-]*\d[\d\s()./-]{4,18}"),
    re.compile(r"(?<!\d)0\d{2,5}[\s/.-]?\d[\d\s()./-]{4,18}(?!\d)"),
    re.compile(r"(?:\+?\d[\d\s()./-]{6,}\d)"),
)

_PHONE_SKIP_DIGIT_PREFIXES = ("19", "20")  # Jahreszahlen


def _normalize_relaxed_phone(raw: str) -> str:
    normalized = " ".join((raw or "").split()).strip(".,;:()[]")
    digits = re.sub(r"\D", "", normalized)
    if len(digits) < 7:
        return ""
    if len(digits) in (4, 8) and digits.startswith(_PHONE_SKIP_DIGIT_PREFIXES):
        return ""
    if digits.startswith("49") and len(digits) < 10:
        return ""
    if digits.startswith("0049"):
        digits = "49" + digits[4:]
    if digits.startswith("49") and not normalized.startswith("+"):
        rest = digits[2:]
        if len(rest) >= 9:
            normalized = f"+49 {rest[:3]} {rest[3:]}".strip()
    return normalized


def _extract_phones_with_relaxed_regex(text: str) -> list[str]:
    if not text:
        return []
    prepared = prepare_text_for_email_extraction(text)
    seen: list[str] = []
    for rx in _RELAXED_PHONE_REGEXES:
        for match in rx.findall(prepared):
            norm = _normalize_relaxed_phone(match)
            if norm and norm not in seen:
                seen.append(norm)
    gemini_lines = re.findall(
        r"(?:Telefon|Tel\.?|PHONE)\s*:\s*([^\n]+)", prepared, flags=re.IGNORECASE
    )
    for line in gemini_lines:
        for part in re.split(r"[;,|]", line):
            norm = _normalize_relaxed_phone(part)
            if norm and norm not in seen:
                seen.append(norm)
    return seen


def _pick_best_company_name(
    candidates: list[str], website: str = "", email: str = ""
) -> str:
    cleaned: list[str] = []
    for raw in candidates:
        name = clean_company_name(raw, website)
        if not name or name.lower() == "unbekanntes unternehmen":
            continue
        if is_rejected_company_name_for_export(name, website, email):
            continue
        if name not in cleaned:
            cleaned.append(name)
    if not cleaned:
        return ""

    def score(name: str) -> int:
        s = 0
        low = name.lower()
        if re.search(_COMPANY_LEGAL_SUFFIX, name, re.IGNORECASE):
            s += 40
        if 8 <= len(name) <= 80:
            s += 10
        if website:
            host = get_registrable_domain(website).split(".")[0]
            if host and host in low:
                s += 25
        if any(x in low for x in ("11880", "gelbeseiten", "wikipedia", "beste ", "top 10")):
            s -= 50
        return s

    cleaned.sort(key=score, reverse=True)
    return cleaned[0]


def _extract_company_names_with_relaxed_regex(text: str, website: str = "") -> list[str]:
    if not text:
        return []
    prepared = re.sub(r"\s+", " ", text.strip())
    found: list[str] = []
    for rx in _RELAXED_COMPANY_REGEXES:
        for match in rx.findall(prepared):
            name = " ".join(str(match).split()).strip(" -|–—:;")
            if name and name not in found:
                found.append(name)
    return found


def find_company_names_in_text(
    text: str,
    *,
    logger: logging.Logger | None = None,
    cache: dict | None = None,
    page_url: str = "",
    website: str = "",
    gemini_buf: dict | None = None,
) -> list[str]:
    """Gemini → Regex; liefert Kandidaten für den Firmennamen."""
    if not text:
        return []
    source = _resolve_contact_source_text(
        text, logger=logger, cache=cache, page_url=page_url, gemini_buf=gemini_buf
    )
    found = _extract_company_names_with_relaxed_regex(source, website)
    if not found:
        for name in _extract_company_names_with_relaxed_regex(text, website):
            if name not in found:
                found.append(name)
    return found


def find_company_name_in_text(
    text: str,
    *,
    logger: logging.Logger | None = None,
    cache: dict | None = None,
    page_url: str = "",
    website: str = "",
    gemini_buf: dict | None = None,
) -> str:
    candidates = find_company_names_in_text(
        text,
        logger=logger,
        cache=cache,
        page_url=page_url,
        website=website,
        gemini_buf=gemini_buf,
    )
    return _pick_best_company_name(candidates, website, "")


def find_phones_in_text(
    text: str,
    *,
    logger: logging.Logger | None = None,
    cache: dict | None = None,
    page_url: str = "",
    gemini_buf: dict | None = None,
) -> list[str]:
    """Pipeline: Gemini bereinigt Text → maximal lockeres Regex."""
    if not text:
        return []
    source = _resolve_contact_source_text(
        text, logger=logger, cache=cache, page_url=page_url, gemini_buf=gemini_buf
    )
    found = _extract_phones_with_relaxed_regex(source)
    if not found:
        for p in _extract_phones_with_relaxed_regex(text):
            if p not in found:
                found.append(p)
    return found


def _extract_company_names_from_html(soup: BeautifulSoup, base_url: str) -> list[str]:
    names: list[str] = []
    if soup.title and soup.title.string:
        names.append(soup.title.string.strip())
    for prop in ("og:site_name", "og:title"):
        tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        if tag and tag.get("content"):
            names.append(tag["content"].strip())
    for h1 in soup.find_all("h1", limit=3):
        t = h1.get_text(" ", strip=True)
        if t:
            names.append(t)
    return names


def normalize_phone_for_compare(phone: str) -> str:
    return re.sub(r"\D", "", phone or "")


def build_company_query_from_row(row: dict) -> str:
    name = (row.get("nazwa") or "").strip()
    if name:
        return name
    category = (row.get("kategoria") or "").strip()
    address = (row.get("full_address") or row.get("adres") or "").strip()
    query = " ".join(x for x in [category, address] if x).strip()
    if query:
        return query
    place_url = (row.get("url") or "").strip()
    if "/maps/place/" in place_url:
        try:
            slug = place_url.split("/maps/place/", 1)[1].split("/", 1)[0]
            slug = slug.replace("+", " ").replace("%20", " ").strip()
            if slug:
                return slug
        except Exception:
            pass
    return ""


def reconcile_contact_sources(row: dict, collected: dict) -> dict:
    maps_phone = (row.get("telefon") or "").strip()
    maps_website = normalize_website(row.get("www", ""))
    website = normalize_website(collected.get("website", ""))
    website_phones = collected.get("phones", []) or []
    maps_phone_norm = normalize_phone_for_compare(maps_phone)
    website_phone_norms = {normalize_phone_for_compare(p) for p in website_phones if p}
    same_phone = bool(maps_phone_norm and maps_phone_norm in website_phone_norms)
    same_website = bool(maps_website and website and maps_website == website)
    if same_phone or same_website:
        row["telefon"] = website_phones[0] if website_phones else ""
        row["www"] = website or row.get("www", "")
        row["contact_source"] = "serper_bs4"
        row["maps_contact_rejected"] = "yes"
    else:
        row["contact_source"] = "maps_or_mixed"
        row["maps_contact_rejected"] = "no"
    if not row.get("telefon") and website_phones:
        row["telefon"] = website_phones[0]
    if not row.get("www") and website:
        row["www"] = website
    website_for_name = website_base_url(
        website or row.get("official_website") or row.get("www") or ""
    )
    if website_for_name:
        row["www"] = website_for_name
        row["official_website"] = website_for_name
    current = (row.get("company_name_clean") or row.get("nazwa") or "").strip()
    if website_for_name and should_prefer_domain_company_name(current, website_for_name):
        domain_clean = derive_name_from_website(website_for_name)
        if domain_clean:
            if not row.get("company_name_raw"):
                row["company_name_raw"] = current
            row["company_name_clean"] = domain_clean
            row["nazwa"] = domain_clean
    else:
        www_company = (collected.get("company_name") or "").strip()
        if www_company:
            weak = (
                not current
                or current.lower() in ("nieznana firma", "unbekanntes unternehmen")
                or len(current) < 6
                or any(
                    x in current.lower() for x in ("http://", "https://", "pdf", "11880")
                )
            )
            if weak or (
                re.search(_COMPANY_LEGAL_SUFFIX, www_company, re.IGNORECASE)
                and not re.search(_COMPANY_LEGAL_SUFFIX, current, re.IGNORECASE)
            ):
                clean = clean_company_name(
                    www_company, website_for_name or website or row.get("www") or ""
                )
                row["company_name_clean"] = clean
                row["nazwa"] = clean
                if not row.get("company_name_raw"):
                    row["company_name_raw"] = current or www_company
    return row


def search_official_website_with_serper(company_name: str, address: str, logger: logging.Logger, cache: dict) -> str:
    query = (company_name or "").strip()
    if not query:
        console_step("Serper übersprungen: leere Anfrage")
        return ""
    serper_cache = cache.setdefault("serper", {})
    if query in serper_cache:
        console_step("Serper Cache Treffer")
        cached = serper_cache[query]
        if isinstance(cached, dict):
            return cached.get("url", "")
        return cached or ""

    api_key = get_serper_api_key()
    if not api_key:
        logger.warning("Kein SERPER_API_KEY.")
        serper_cache[query] = ""
        return ""
    if is_serper_limit_reached_today(cache):
        serper_cache[query] = ""
        return ""
    today, used_today, remaining = get_remaining_daily_serper_limit(cache)
    if remaining <= 0:
        mark_serper_limit_reached_today(cache)
        serper_cache[query] = ""
        return ""

    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "gl": SERPER_COUNTRY, "hl": SERPER_LANGUAGE, "num": 5}
    try:
        console_step(f"Serper Anfrage: {query}")
        increase_daily_serper_counter(cache, 1)
        resp = request_with_retry(
            requests.post,
            SERPER_API_URL,
            logger,
            headers=headers,
            json=payload,
            timeout=SERPER_TIMEOUT,
        )
        data = resp.json()
    except Exception as e:
        logger.warning(f"Serper Fehler '{query}': {e}")
        serper_cache[query] = ""
        return ""

    candidates = []
    for k in ("organic", "places"):
        for item in data.get(k, []) or []:
            link = item.get("link") or item.get("website") or ""
            if link:
                candidates.append(
                    {
                        "link": link,
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                    }
                )
    best_score = 0
    if candidates:
        scored = [
            (
                score_serper_candidate(
                    c.get("link", ""),
                    c.get("title", ""),
                    c.get("snippet", ""),
                    company_name,
                ),
                c,
            )
            for c in candidates[:5]
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_candidate = scored[0]
        result = normalize_website(best_candidate.get("link", ""))
    else:
        result = ""
    serper_cache[query] = {"url": result, "score": best_score}
    return result


def extract_plz_from_text(text: str) -> list[str]:
    if not text:
        return []
    found = re.findall(r"\b(\d{2})[- ]?(\d{3})\b", text)
    out: list[str] = []
    for a, b in found:
        code = f"{a}{b}"
        if code not in out:
            out.append(code)
    return out


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def _normalize_plz_code(plz: str) -> str:
    digits = re.sub(r"\D", "", plz or "")
    if len(digits) == 5:
        return digits
    return ""


def plz_centroid_approx(plz: str) -> tuple[float, float] | None:
    """PLZ-Schwerpunkt (Präfix) – Filter Ostdeutschland."""
    p = _normalize_plz_code(plz)
    if not p or len(p) != 5:
        return None
    prefix = p[:2]
    suffix = int(p[2:])
    bases = {
        "01": (51.050, 13.737),  # Dresden
        "02": (51.152, 14.987),  # Görlitz
        "03": (51.760, 14.334),  # Cottbus
        "04": (51.340, 12.374),  # Leipzig
        "06": (51.482, 11.969),  # Halle
        "07": (50.928, 11.589),  # Jena
        "08": (50.827, 12.921),  # Chemnitz
        "09": (50.610, 12.495),  # Zwickau
        "14": (52.391, 13.066),  # Potsdam
        "15": (52.347, 14.550),  # Frankfurt Oder
        "16": (52.756, 13.030),  # Oranienburg
        "17": (53.629, 13.047),  # Neubrandenburg (nördl. BB)
        "18": (54.088, 12.140),  # Rostock Umkreis / nördl. BB Grenze
        "19": (53.635, 11.397),  # Schwerin Umkreis
        "37": (51.050, 10.715),  # Erfurt süd
        "38": (52.131, 11.627),  # Magdeburg
        "39": (52.272, 11.854),  # Magdeburg Ost
        "98": (50.978, 11.029),  # Erfurt
        "99": (50.684, 10.927),  # Suhl / Südthüringen
    }
    if prefix in bases:
        lat, lon = bases[prefix]
        return (lat, lon)
    return None


def plz_within_region_km(plz: str, max_km: float | None = None) -> bool:
    """PLZ w BB/SN/TH – bei ENABLE_PLZ_PREFIX_REGION_MATCH ohne Leipziger Radius (Dörfer)."""
    max_km = MAX_DISTANCE_FROM_REGION_KM if max_km is None else max_km
    p = _normalize_plz_code(plz)
    if not p:
        return False
    if p[:2] not in DE_EAST_PLZ_PREFIXES:
        return False
    if ENABLE_PLZ_PREFIX_REGION_MATCH:
        return True
    c = plz_centroid_approx(plz)
    if not c:
        return False
    return (
        haversine_km(REGION_CENTER_LAT, REGION_CENTER_LON, c[0], c[1]) <= max_km
    )


def _coords_in_de_de_bbox(lat: float, lon: float) -> bool:
    return (
        DE_DE_BBOX_LAT_MIN <= lat <= DE_DE_BBOX_LAT_MAX
        and DE_DE_BBOX_LON_MIN <= lon <= DE_DE_BBOX_LON_MAX
    )


def location_within_region_km(
    text: str = "",
    lat: float | None = None,
    lon: float | None = None,
    max_km: float | None = None,
) -> bool:
    """BB/SN/TH: PLZ-Präfix, Kleinstädte/Dörfer im Text, oder Koordinaten in Ost-BBox."""
    if not ENABLE_DISTANCE_FROM_REGION_KM and not ENABLE_REGION_PLZ_FILTER:
        return True
    max_km = MAX_DISTANCE_FROM_REGION_KM if max_km is None else max_km

    blob = (text or "").strip()
    blob_low = blob.lower()
    plzs = extract_plz_from_text(blob)
    if plzs and any(plz_within_region_km(p, max_km=max_km) for p in plzs):
        return True

    far_markers = (
        "münchen",
        "muenchen",
        "hamburg",
        "köln",
        "koeln",
        "frankfurt",
        "stuttgart",
        "düsseldorf",
        "duesseldorf",
        "bremen",
        "hannover",
        "nürnberg",
        "nuernberg",
        "westfalen",
        "nrw",
        "bayern",
        "baden-württemberg",
    )
    if any(m in blob_low for m in far_markers):
        return False

    if any(m in blob_low for m in DE_OST_PLACE_MARKERS):
        return True
    if any(m in blob_low for m in DE_OST_RURAL_HINTS):
        return True
    if any(m in blob_low for m in DE_OST_REGION_KEYWORDS):
        return True

    if lat is not None and lon is not None:
        try:
            la, lo = float(lat), float(lon)
            if ENABLE_PLZ_PREFIX_REGION_MATCH and _coords_in_de_de_bbox(la, lo):
                return True
            if ENABLE_DISTANCE_FROM_REGION_KM:
                return (
                    haversine_km(
                        REGION_CENTER_LAT,
                        REGION_CENTER_LON,
                        la,
                        lo,
                    )
                    <= max_km
                )
        except (TypeError, ValueError):
            pass

    return not ENABLE_REGION_PLZ_FILTER


def row_within_region_km(row: dict) -> bool:
    blob = " ".join(
        str(row.get(k) or "")
        for k in ("full_address", "adres", "nazwa", "kategoria", "www", "url")
    )
    lat = row.get("lat_center")
    lon = row.get("lon_center")
    try:
        lat_f = float(lat) if lat not in ("", None) else None
        lon_f = float(lon) if lon not in ("", None) else None
    except (TypeError, ValueError):
        lat_f, lon_f = None, None
    return location_within_region_km(blob, lat=lat_f, lon=lon_f)


def discover_places_with_serper(
    term: str,
    logger: logging.Logger,
    cache: dict,
    *,
    apply_location_filter: bool = True,
) -> list[dict]:
    query = f"{term} {SERPER_DISCOVERY_REGION_SUFFIX}".strip()
    if not query:
        return []
    api_key = get_serper_api_key()
    if not api_key:
        console_step("Serper Discovery: kein API-Key")
        return []
    if is_serper_limit_reached_today(cache):
        console_step("Serper Discovery: Tageslimit")
        return []
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {
        "q": query,
        "gl": SERPER_COUNTRY,
        "hl": SERPER_LANGUAGE,
        "num": SERPER_DISCOVERY_RESULTS_PER_TERM,
    }
    try:
        console_step(f"Serper Discovery: {query}")
        increase_daily_serper_counter(cache, 1)
        resp = request_with_retry(
            requests.post,
            SERPER_API_URL,
            logger,
            headers=headers,
            json=payload,
            timeout=SERPER_TIMEOUT,
        )
        data = resp.json()
    except Exception as e:
        console_step(f"Serper Discovery Fehler: {e}")
        return []

    rows = []
    seen = set()
    for bucket in ("organic", "places"):
        for item in data.get(bucket, []) or []:
            link = normalize_website(item.get("link") or item.get("website") or "")
            if not link or link in seen:
                continue
            if not is_germany_de_candidate(
                link, item.get("title", ""), item.get("snippet", "")
            ):
                continue
            title = (item.get("title") or "").strip()
            snippet = (item.get("snippet") or "").strip()
            if not is_valid_retail_store_builder_contact(
                url=link, name=title, text=f"{title} {snippet}"
            ):
                continue
            blob = " ".join([link, title, snippet])
            if apply_location_filter and (
                ENABLE_REGION_PLZ_FILTER or ENABLE_DISTANCE_FROM_REGION_KM
            ):
                if not location_within_region_km(blob):
                    continue
            company_clean = clean_company_name(item.get("title", ""), link)
            if is_excluded_kontrahent(name=company_clean, url=link, email="")[0]:
                continue
            if is_likely_large_company(company_clean, link, blob)[0]:
                continue
            seen.add(link)
            rows.append(
                {
                    "fraza": term,
                    "nazwa": company_clean,
                    "company_name_raw": (item.get("title") or "").strip(),
                    "company_name_clean": clean_company_name(item.get("title", ""), link),
                    "ocena": "",
                    "liczba_opinii": "",
                    "kategoria": term,
                    "adres": "",
                    "full_address": "",
                    "status": "",
                    "telefon": "",
                    "www": link,
                    "url": link,
                    "lat_center": "",
                    "lon_center": "",
                }
            )
    console_step(f"Serper Discovery Ergebnisse '{term}': {len(rows)}")
    return rows


def _is_impressum_url(url: str) -> bool:
    low = (url or "").lower()
    return "impressum" in low or "/imprint" in low


def guess_impressum_urls(base_url: str) -> list[str]:
    """Heurystyka: typowe ścieżki Impressum na tej samej domenie (mail często tylko tam)."""
    base = normalize_website(base_url)
    if not base:
        return []
    try:
        parsed = urlparse(base)
        host = (parsed.netloc or "").lower()
        if not host:
            return []
        scheme = parsed.scheme or "https"
        root = f"{scheme}://{host}"
    except Exception:
        return []
    out: list[str] = []
    for path in IMPRESSUM_GUESS_PATHS:
        full = urljoin(root + "/", path.lstrip("/"))
        if full not in out:
            out.append(full)
    return out


def sort_contact_urls_priority_pl(urls: list[str]) -> list[str]:
    """DE: najpierw Impressum, potem Kontakt; na końcu RODO/Datenschutz."""

    def key(u: str) -> tuple[int, int, str]:
        low = u.lower()
        if any(
            x in low
            for x in (
                "rodo",
                "privacy",
                "datenschutz",
                "dsgvo",
                "ochrona-danych",
                "ochrona_danych",
                "polityka-prywatnosci",
                "polityka_prywatnosci",
                "gdpr",
                "cookies",
                "cookie-richtlinie",
                "regulamin",
            )
        ):
            return (3, len(low), low)
        if _is_impressum_url(low):
            return (0, len(low), low)
        if any(
            x in low
            for x in (
                "kontakt",
                "contact",
                "anfahrt",
                "ofert",
                "wycen",
                "sprzedaz",
                "zapytan",
            )
        ):
            return (1, len(low), low)
        return (2, len(low), low)

    return sorted(urls, key=key)


def merge_contact_subpage_urls(website: str, discovered: list[str]) -> list[str]:
    """Impressum (link + zgadnięte ścieżki) przed innymi podstronami."""
    seen: set[str] = set()
    merged: list[str] = []
    for u in guess_impressum_urls(website) + list(discovered or []):
        u = (u or "").strip()
        if not u.startswith(("http://", "https://")) or u in seen:
            continue
        seen.add(u)
        merged.append(u)
    impressum = [u for u in merged if _is_impressum_url(u)]
    kontakt = [
        u
        for u in merged
        if u not in impressum
        and any(x in u.lower() for x in ("kontakt", "contact"))
    ]
    rest = [u for u in merged if u not in impressum and u not in kontakt]
    ordered = sort_contact_urls_priority_pl(impressum + kontakt + rest)
    return ordered[:MAX_CONTACT_LINKS]


def extract_html_text_with_media_hints(soup: BeautifulSoup) -> str:
    """Tekst strony + alt/title/figcaption/src obrazów (zdjęcia marketów)."""
    parts: list[str] = []
    if soup:
        parts.append(soup.get_text(" ", strip=True))
        for img in soup.find_all("img"):
            for attr in ("alt", "title"):
                val = (img.get(attr) or "").strip()
                if val:
                    parts.append(val)
            src = (img.get("src") or img.get("data-src") or "").strip()
            if src:
                parts.append(src)
        for tag in soup.find_all("figcaption"):
            cap = tag.get_text(" ", strip=True)
            if cap:
                parts.append(cap)
    return " ".join(p for p in parts if p)


def parse_contacts_from_html(
    base_url: str,
    html: str,
    *,
    logger: logging.Logger | None = None,
    cache: dict | None = None,
) -> dict:
    soup = BeautifulSoup(html or "", "html.parser")
    page_text = extract_html_text_with_media_hints(soup)
    gemini_buf: dict = {}
    emails = find_emails_in_text(
        page_text,
        logger=logger,
        cache=cache,
        page_url=base_url,
        gemini_buf=gemini_buf,
    )
    phones = find_phones_in_text(
        page_text,
        logger=logger,
        cache=cache,
        page_url=base_url,
        gemini_buf=gemini_buf,
    )
    company_candidates = _extract_company_names_from_html(soup, base_url)
    company_candidates.extend(
        find_company_names_in_text(
            page_text,
            logger=logger,
            cache=cache,
            page_url=base_url,
            website=base_url,
            gemini_buf=gemini_buf,
        )
    )
    company_name = _pick_best_company_name(company_candidates, base_url, "")
    contact_urls = []
    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        label = (a.get_text(" ", strip=True) or "").lower()
        if href.startswith("mailto:"):
            email = _normalize_relaxed_email(
                href.replace("mailto:", "", 1)
            )
            if email and email not in emails:
                emails.append(email)
        if href.startswith("tel:"):
            phone = _normalize_relaxed_phone(href.replace("tel:", "", 1))
            if phone and phone not in phones:
                phones.append(phone)
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            pass
        elif any(k in href.lower() or k in label for k in RETAIL_CONTACT_LINK_KEYWORDS):
            full = urljoin(base_url, href)
            if full.startswith(("http://", "https://")) and full not in contact_urls:
                contact_urls.append(full)
    contact_urls = merge_contact_subpage_urls(base_url, contact_urls)
    return {
        "emails": emails,
        "phones": phones,
        "company_name": company_name,
        "contact_urls": contact_urls,
        "page_text": page_text,
    }


def parse_contacts_from_page(
    url: str, logger: logging.Logger, cache: dict | None = None
) -> dict:
    if not (url or "").strip().lower().startswith(("http://", "https://")):
        return {"emails": [], "phones": [], "contact_urls": [], "page_text": ""}
    console_step(f"Lade Seite: {url}")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }
    html = ""
    empty = {"emails": [], "phones": [], "contact_urls": [], "page_text": ""}
    try:
        r = request_with_retry(
            requests.get,
            url,
            logger,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            waf_skip=True,
        )
        html = r.text
    except Exception as e:
        from http_page_guard import PageAccessBlocked

        if isinstance(e, PageAccessBlocked):
            logger.info("Strona pominięta (WAF/Cloudflare): %s", url)
            return empty
        logger.info(f"Seitenabruf fehlgeschlagen {url}: {e}")
    parsed = parse_contacts_from_html(url, html, logger=logger, cache=cache)

    def _parse_html_playwright(page_url: str, page_html: str) -> dict:
        return parse_contacts_from_html(
            page_url, page_html, logger=logger, cache=cache
        )

    parsed = apply_playwright_cookie_fallback(
        url, logger, html, parsed, _parse_html_playwright, on_step=console_step
    )
    return {
        "emails": parsed["emails"],
        "phones": parsed["phones"],
        "company_name": parsed.get("company_name") or "",
        "contact_urls": parsed["contact_urls"],
        "page_text": parsed.get("page_text", ""),
    }


def _truncate_page_snippet(text: str, max_chars: int = PAGE_SNIPPET_MAX_CHARS) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 3] + "..."


def _parse_emails_found_field(raw: str) -> list[str]:
    return [
        x.strip()
        for x in (raw or "").split(",")
        if x.strip() and "@" in x
    ]


def log_email_pick_decision(
    logger: logging.Logger,
    *,
    place_url: str = "",
    company_name: str = "",
    website: str = "",
    candidates: list[str] | None = None,
    target: str = "",
    score: int = 0,
    method: str = "none",
    note: str = "",
) -> None:
    """Jedna linia: wybrany mail, score, metoda, ranking kandydatów."""
    cand = list(candidates or [])
    ranked = rank_email_candidates(cand, website or "")
    ranked_txt = ", ".join(f"{e}({s})" for e, s in ranked[:8]) or "(brak)"
    label = (company_name or place_url or website or "?")[:72]
    site_short = (website or place_url or "")[:96]
    if target:
        msg = (
            f"E-mail pick | {label} | {site_short} | "
            f"wybrano={target} score={score} method={method} | "
            f"kandydaci: {ranked_txt}"
        )
        if note:
            msg += f" | {note}"
        logger.info(msg)
        console_step(f"E-mail: {target} (score={score}, {method})")
    else:
        best_score = ranked[0][1] if ranked else 0
        msg = (
            f"E-mail pick | {label} | {site_short} | "
            f"BRAK (min={MIN_EMAIL_SCORE_FOR_SEND}, best={best_score}) | "
            f"kandydaci: {ranked_txt}"
        )
        if note:
            msg += f" | {note}"
        logger.info(msg)


def backfill_emails_in_cache(cache: dict, logger: logging.Logger) -> dict:
    """
    Przelicza email_target z emails_found (nowe reguły Punycode / filtr śmieci).
    Czyści emails_found z fałszywych trafień regex.
    """
    contacts = cache.get("contacts") or {}
    stats = {
        "checked": 0,
        "filled": 0,
        "updated": 0,
        "cleaned_found": 0,
        "unchanged": 0,
        "still_empty": 0,
    }
    for place_url, info in contacts.items():
        if not isinstance(info, dict):
            continue
        stats["checked"] += 1
        raw_found = (info.get("emails_found") or "").strip()
        candidates = filter_commercial_emails(_parse_emails_found_field(raw_found))
        cleaned_found = ", ".join(candidates)
        if cleaned_found != raw_found:
            info["emails_found"] = cleaned_found
            stats["cleaned_found"] += 1
        website = (info.get("official_website") or place_url or "").strip()
        company = (
            info.get("company_name_clean")
            or info.get("company_name")
            or info.get("company_name_raw")
            or ""
        ).strip()
        old_target = (info.get("email_target") or "").strip().lower()
        target, score = pick_best_email_for_inquiry(candidates, website)
        if target and is_non_commercial_email(target):
            target = ""
        if target:
            new_low = target.lower()
            if new_low != old_target:
                if old_target:
                    stats["updated"] += 1
                else:
                    stats["filled"] += 1
                info["email_target"] = target
                info["email_target_score"] = score
                info["email_pick_method"] = "rules_backfill"
                if (info.get("email_status") or "") in (
                    "",
                    "no_suitable_email",
                ):
                    info["email_status"] = "backfilled"
                log_email_pick_decision(
                    logger,
                    place_url=place_url,
                    company_name=company,
                    website=website,
                    candidates=candidates,
                    target=target,
                    score=score,
                    method="rules_backfill",
                    note="backfill",
                )
            else:
                stats["unchanged"] += 1
                if score > int(info.get("email_target_score", 0) or 0):
                    info["email_target_score"] = score
        else:
            stats["still_empty"] += 1
            if candidates and not old_target:
                log_email_pick_decision(
                    logger,
                    place_url=place_url,
                    company_name=company,
                    website=website,
                    candidates=candidates,
                    target="",
                    score=score,
                    method="none",
                    note="backfill_bez_progu",
                )
    logger.info(
        "Backfill e-mail cache: sprawdzono=%s, uzupelniono=%s, zmieniono=%s, "
        "oczyszczono emails_found=%s, bez zmian=%s, nadal pusto=%s",
        stats["checked"],
        stats["filled"],
        stats["updated"],
        stats["cleaned_found"],
        stats["unchanged"],
        stats["still_empty"],
    )
    return stats


def gemini_pick_inquiry_email_from_page(
    company_name: str,
    website_url: str,
    candidates: list[str],
    page_snippet: str,
    logger: logging.Logger,
    cache: dict | None,
    *,
    cache_key: str = "",
) -> str:
    """
    Gemini wybiera WYŁĄCZNIE jeden adres z listy kandydatów znalezionych w HTML.
    """
    if not ENABLE_GEMINI_CONTACT_EMAIL:
        return ""
    api_key = get_google_ai_studio_api_key()
    if not api_key or is_gemini_rate_limited(cache):
        return ""
    normalized = [(c or "").strip().lower() for c in candidates if (c or "").strip()]
    if not normalized:
        return ""

    pick_cache = (cache or {}).setdefault("gemini_email_pick", {})
    if cache_key and cache_key in pick_cache:
        cached = (pick_cache[cache_key] or "").strip().lower()
        return validate_gemini_email_choice(cached, normalized, website_url)

    ranked = rank_email_candidates(normalized, website_url)
    ranked_lines = "\n".join(
        f"- {e} (wynik_reguł={sc})" for e, sc in ranked[:12]
    )
    snippet = _truncate_page_snippet(page_snippet)
    candidates_json = json.dumps(normalized, ensure_ascii=False)

    prompt = (
        "Du bist B2B-Assistent. Wähle EINE E-Mail für eine Anfrage an einen Generalunternehmer "
        f"im Einzelhandelsbau ({RETAIL_CHAINS_DE}) in {INQUIRY_REGION_DE}.\n"
        "Nur JSON: {\"email\":\"...\",\"reason\":\"...\"}\n\n"
        f"Firma: {company_name}\n"
        f"Webseite: {website_url}\n\n"
        "Kandidaten — nur eine Adresse aus dieser Liste (exakt, Kleinbuchstaben):\n"
        f"{candidates_json}\n\n"
        "Regel-Ranking (Hinweis):\n"
        f"{ranked_lines or '(keine)'}\n\n"
        "VERBOTEN: datenschutz, privacy, GDPR, newsletter, HR, karriere, presse, rechnung, noreply.\n"
        "BEVORZUGT: info, kontakt, anfrage, projekt, bau, gu, vertrieb, geschaeftsleitung.\n"
        "Wenn keiner passt: {\"email\":\"\",\"reason\":\"...\"}.\n"
        "Keine neue Adresse erfinden.\n\n"
        "Seitenauszug:\n"
        f"{snippet or '(kein Text)'}"
    )
    try:
        text, used_model = gemini_generate_text(prompt, logger, api_key, cache=cache)
        console_step(f"Gemini wybór e-mail kontaktowy, model: {used_model}")
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        parsed = json.loads(match.group(0) if match else text)
        raw_choice = (parsed.get("email") or "").strip().lower()
        validated = validate_gemini_email_choice(raw_choice, normalized, website_url)
        if validated:
            if cache_key:
                pick_cache[cache_key] = validated
            return validated
        if raw_choice:
            logger.info(
                "Gemini e-mail odrzucony (spoza listy lub RODO): %s", raw_choice
            )
    except Exception as e:
        logger.warning(f"Gemini wybór e-mail: {e}")
    return ""


def resolve_inquiry_email_target(
    collected: dict,
    website: str,
    company_name: str,
    logger: logging.Logger,
    cache: dict | None,
    *,
    cache_key: str = "",
) -> tuple[str, int, str]:
    """
    Zwraca (email_target, score, metoda).
    metoda: rules | gemini_arbitration | none
    """
    candidates = filter_commercial_emails(list(collected.get("emails") or []))
    site = collected.get("website") or website or ""
    snippet = collected.get("page_snippet") or ""

    target, score = pick_best_email_for_inquiry(candidates, site)
    method = "rules" if target else "none"
    if target and not is_valid_retail_store_builder_contact(
        email=target, url=site, name=company_name, text=snippet
    ):
        log_email_pick_decision(
            logger,
            place_url=cache_key,
            company_name=company_name,
            website=site,
            candidates=candidates,
            target="",
            score=score,
            method="blocked_not_store_builder",
            note=f"odrzucono={target}",
        )
        return "", score, "blocked_not_store_builder"

    use_gemini = ENABLE_GEMINI_CONTACT_EMAIL and needs_gemini_email_arbitration(
        candidates, site
    )
    if use_gemini:
        gemini_email = gemini_pick_inquiry_email_from_page(
            company_name,
            site,
            candidates,
            snippet,
            logger,
            cache,
            cache_key=cache_key,
        )
        if gemini_email:
            g_score = score_email_candidate(gemini_email, site)
            if g_score >= MIN_EMAIL_SCORE_FOR_SEND:
                log_email_pick_decision(
                    logger,
                    place_url=cache_key,
                    company_name=company_name,
                    website=site,
                    candidates=candidates,
                    target=gemini_email,
                    score=g_score,
                    method="gemini_arbitration",
                )
                return gemini_email, g_score, "gemini_arbitration"

    log_email_pick_decision(
        logger,
        place_url=cache_key,
        company_name=company_name,
        website=site,
        candidates=candidates,
        target=target,
        score=score,
        method=method,
    )
    return target, score, method


def collect_contacts_from_website(
    website: str, logger: logging.Logger, cache: dict | None = None
) -> dict:
    website = normalize_website(website)
    if not website:
        console_step("Keine Website – Kontaktsuche übersprungen")
        return {
            "emails": [],
            "phones": [],
            "company_name": "",
            "website": "",
            "source_urls": [],
            "page_snippet": "",
        }
    console_step(f"Kontakte sammeln (nach WWW-Prüfung): {website}")
    base = parse_contacts_from_page(website, logger, cache=cache)
    emails = list(base["emails"])
    phones = list(base["phones"])
    company_candidates: list[str] = []
    if base.get("company_name"):
        company_candidates.append(base["company_name"])
    source_urls = [website]
    text_parts = [base.get("page_text") or ""]
    contact_links = merge_contact_subpage_urls(
        website,
        sort_verification_urls(base.get("contact_urls") or []),
    )
    # Dodatkowe próby typowych /impressum (nawet bez linku w menu)
    impressum_guesses = guess_impressum_urls(website)[:MAX_IMPRESSUM_GUESS_FETCH]
    fetch_queue: list[str] = []
    seen_fetch: set[str] = set()
    for u in contact_links + impressum_guesses:
        if u not in seen_fetch:
            seen_fetch.add(u)
            fetch_queue.append(u)
    for u in fetch_queue:
        details = parse_contacts_from_page(u, logger, cache=cache)
        for e in details["emails"]:
            if e not in emails:
                emails.append(e)
        for p in details["phones"]:
            if p not in phones:
                phones.append(p)
        if details.get("company_name"):
            company_candidates.append(details["company_name"])
        if details.get("page_text"):
            text_parts.append(details["page_text"])
        if u not in source_urls:
            source_urls.append(u)
    page_snippet = _truncate_page_snippet(" ".join(text_parts))
    return {
        "emails": emails,
        "phones": phones,
        "company_name": _pick_best_company_name(company_candidates, website),
        "website": website,
        "source_urls": source_urls,
        "page_snippet": page_snippet,
    }


def _assemble_inquiry_email_body(company_name: str, opening: str = "") -> str:
    """Fester Block FIXED_GU_INQUIRY_DE (ohne Gemini-Fließtext)."""
    _ = company_name, opening  # zachowane dla kompatybilności wywołań
    return FIXED_GU_INQUIRY_DE.strip()


def generate_email_content_gemini(company_name: str, logger: logging.Logger, cache=None):
    """Wyłącznie stały tekst z mfg_gu_inquiry_email_de — bez Gemini i bez szablonu GUI."""
    _ = company_name, logger, cache
    console_step("E-Mail: fester MFG-Text (mfg_gu_inquiry_email_de)")
    return FIXED_EMAIL_SUBJECT_DE, FIXED_GU_INQUIRY_DE.strip()


def send_email_de_gu(
    to_email: str,
    subject: str,
    body: str,
    logger: logging.Logger,
) -> tuple[bool, str]:
    """
    Wysyłka SMTP wyłącznie dla kampanii DE Ost (GU Ladenbau).
    Stały tekst + PPTX — logika nie jest współdzielona z innymi scraperami.
    """
    from mail_transport import archive_sent_email_message
    from mfg_mail_recipients import merge_mfg_campaign_cc
    from scraper_env import (
        ENV_MAIL_BCC,
        ENV_MAIL_CC,
        get_env_value,
        get_mail_password,
        get_mail_user,
    )

    if not (get_mail_user() and get_mail_password()):
        return False, "brak MAIL_USER / MAIL_PASSWORD"

    username = get_mail_user()
    password = get_mail_password()
    subject_clean = sanitize_special_text(subject)
    body_clean = sanitize_email_body(body)
    bcc = _ost_gu_split_recipients(get_env_value(ENV_MAIL_BCC))
    cc = merge_mfg_campaign_cc(to_email, get_env_value(ENV_MAIL_CC))
    logger.info("DE GU: Cc=%s", ", ".join(cc) if cc else "(brak)")
    attach_paths = get_email_attachments_de_gu(logger)
    if not attach_paths:
        return (
            False,
            f"Brak załącznika PPTX (Google Slides {GOOGLE_SLIDES_PRESENTATION_ID}). "
            f"Udostępnij prezentację lub ustaw MFG_EMAIL_ATTACHMENT_PATH. {GOOGLE_SLIDES_URL}",
        )
    attach_path = Path(attach_paths[0])
    size_mb = attach_path.stat().st_size / (1024 * 1024)
    logger.info(
        "DE GU: załącznik %s (%.1f MB)",
        attach_path.name,
        size_mb,
    )
    if size_mb > 15:
        logger.warning(
            "DE GU: duży PPTX (%.1f MB) — serwer SMTP może odrzucić załącznik.",
            size_mb,
        )

    try:
        msg = _build_de_gu_outgoing_email(
            username,
            to_email,
            subject_clean,
            body_clean,
            cc=cc,
            attachment_path=attach_path,
        )
        _send_de_gu_via_smtp(
            msg,
            username=username,
            password=password,
            to_email=to_email,
            cc=cc,
            bcc=bcc,
            logger=logger,
        )
        archive_sent_email_message(
            msg,
            logger,
            to_email=to_email,
            subject=subject_clean,
            attachment_paths=attach_paths or None,
        )
        try:
            from email_journal import log_mail_sent

            log_mail_sent(
                to_email,
                subject,
                mail_type="DE Ost GU",
                campaign="de_gu_bauunternehmen",
                ok=True,
            )
        except Exception:
            pass
        host = _ost_gu_smtp_host()
        attach_note = (
            f" + {attach_path.name}" if attach_path and attach_path.is_file() else ""
        )
        cc_note = f", CC: {', '.join(cc)}" if cc else ""
        logger.info(
            "DE Ost GU: wysłano → %s via %s | %s%s%s",
            to_email,
            host,
            (subject or "")[:60],
            attach_note,
            cc_note,
        )
        return True, "gesendet"
    except Exception as e:
        logger.warning("DE Ost GU: błąd wysyłki do %s: %s", to_email, e)
        try:
            from email_journal import log_mail_sent

            log_mail_sent(
                to_email,
                subject,
                mail_type="DE Ost GU",
                campaign="de_gu_bauunternehmen",
                ok=False,
                error=str(e),
            )
        except Exception:
            pass
        return False, str(e)


def reenrich_contacts_for_mailing(
    all_rows: list[dict],
    cache: dict,
    logger: logging.Logger,
    *,
    refresh_all: bool = False,
) -> None:
    """Ponowne zbieranie e-maili ze stron www przed wysyłką."""
    contacts_cache = cache.setdefault("contacts", {})
    by_url = {str(r.get("url") or ""): r for r in all_rows if r.get("url")}
    urls = set(contacts_cache.keys()) | set(by_url.keys())
    console_step(f"Ponowne wzbogacanie kontaktów: {len(urls)} URL")
    for url in urls:
        if not url:
            continue
        cached = contacts_cache.get(url, {})
        if (
            not refresh_all
            and not DISCOVERY_IGNORE_CONTACT_CACHE
            and (cached.get("email_target") or "").strip()
        ):
            continue
        if refresh_all:
            contacts_cache.pop(url, None)
        seed = dict(by_url.get(url) or {})
        if not seed.get("url"):
            seed["url"] = url
        if not seed.get("www"):
            seed["www"] = cached.get("official_website") or url
        if not seed.get("nazwa"):
            seed["nazwa"] = cached.get("company_name") or cached.get("company_name_clean") or ""
        enriched = enrich_row_with_contacts(seed, cache, logger)
        if url in by_url:
            by_url[url].update(enriched)
        else:
            all_rows.append(enriched)
            by_url[url] = enriched


def _process_email_jobs(
    all_rows: list[dict],
    cache: dict,
    logger: logging.Logger,
    *,
    dry_run_email: bool = False,
    force_resend: bool = False,
    ignore_send_window: bool = False,
) -> None:
    persist_progress(all_rows, cache, logger, reason="vor Mailversand")
    email_jobs = build_email_jobs_from_cache_json(logger, force_resend=force_resend)
    email_jobs.sort(key=lambda x: x.get("contact_quality_score", 0), reverse=True)
    today, sent_today, remaining = get_remaining_daily_email_limit(cache)
    if remaining <= 0:
        jobs_to_send = []
        jobs_deferred = email_jobs
    else:
        jobs_to_send = email_jobs[:remaining]
        jobs_deferred = email_jobs[remaining:]
    contacts_cache = cache.get("contacts", {})
    for mail in jobs_to_send:
        target = mail["email_target"]
        domain = get_email_domain(target)
        place_url = mail.get("place_url", "")
        contact_info = contacts_cache.get(place_url, {})
        _em, val_url, val_name, val_text = contact_validation_fields(
            contact_info, place_url
        )
        if (
            not force_resend
            and was_email_target_sent_today(cache, target)
        ):
            status = f"duplicate_skipped_{today}"
        elif is_email_role_based_or_system(target):
            status = f"suppressed_role_based_{today}"
        elif not is_valid_retail_store_builder_contact(
            email=target,
            url=val_url,
            name=val_name,
            text=val_text,
        ):
            status = f"suppressed_not_store_builder_{today}"
            mark_suppressed_target(cache, target, "not_store_builder")
        elif not force_resend and is_suppressed_target(cache, target):
            status = f"suppressed_cached_{today}"
        elif not ignore_send_window and not is_within_send_window():
            status = f"deferred_send_window_{today}"
        elif domain:
            _, _, rem_dom = get_domain_remaining_daily_limit(cache, domain)
            if rem_dom <= 0:
                status = f"deferred_domain_limit_{today}"
            else:
                status = None
        else:
            status = None
        if status:
            logger.info("E-mail übersprungen %s: %s", target, status)
            cache.setdefault("contacts", {}).setdefault(mail["place_url"], {})[
                "email_status"
            ] = status
            continue
        if force_resend:
            cache.setdefault("email_suppression", {}).pop(target.lower(), None)
        subject, body = generate_email_content_gemini(
            mail.get("company_name", "Firma"), logger, cache=cache
        )
        if dry_run_email:
            ok, info = True, "dry_run"
            status = f"dry_run_{today}"
        else:
            ok, info = send_email_de_gu(target, subject, body, logger)
            status = "sent" if ok else f"error: {info}"
            if not ok and is_soft_bounce_or_spam_error(info):
                status = f"soft_fail_spam_{today}"
        if ok:
            increase_daily_email_counter(cache, 1)
            mark_email_target_sent_today(cache, target)
            increase_domain_daily_counter(cache, domain, 1)
        c = cache.setdefault("contacts", {}).setdefault(mail["place_url"], {})
        c["email_subject"] = subject
        c["email_body"] = body
        c["email_status"] = status
        if str(status).strip().lower() == "sent":
            mark_email_sent(
                c,
                subject,
                body=body,
                lang="de",
                campaign_id="de_gu_bauunternehmen",
            )
        if status.startswith("error:"):
            lowered = status.lower()
            if "mailbox unavailable" in lowered or "user unknown" in lowered:
                mark_suppressed_target(cache, target, status)
        for row in all_rows:
            if row.get("url") == mail["place_url"]:
                row["email_subject"] = subject
                row["email_body"] = body
                row["email_status"] = status
                row["email_target"] = target
                break
        persist_progress(all_rows, cache, logger, reason=f"Mail {target}: {status}")
        if not dry_run_email:
            sleep_between_emails(logger, target)
    for mail in jobs_deferred:
        cache.setdefault("contacts", {}).setdefault(mail["place_url"], {})[
            "email_status"
        ] = f"deferred_{today}"
    persist_progress(all_rows, cache, logger, reason="nach Mailversand")


def enrich_row_with_contacts(
    row: dict,
    cache: dict,
    logger: logging.Logger,
    *,
    force_refresh: bool | None = None,
) -> dict:
    row = normalize_row_company_name(row)
    place_url = row.get("url", "")
    contacts_cache = cache.setdefault("contacts", {})
    refresh = (
        DISCOVERY_IGNORE_CONTACT_CACHE
        if force_refresh is None
        else force_refresh
    )
    if place_url in contacts_cache and not refresh:
        console_step(f"Kontakt-Cache: {row.get('nazwa', '')}")
        cached = contacts_cache[place_url]
        row.update(cached)
        return normalize_row_company_name(row)
    if place_url in contacts_cache and refresh:
        console_step(f"Kontakt neu laden (ignoruj cache): {row.get('nazwa', '')}")

    maps_website = normalize_website(row.get("www", ""))
    website = maps_website
    serper_source_score = 0
    if FORCE_SERPER_LOOKUP:
        serper_query = build_company_query_from_row(row)
        serper_website = search_official_website_with_serper(
            serper_query, row.get("full_address") or row.get("adres", ""), logger, cache
        )
        website = serper_website or maps_website
    elif not website:
        serper_query = build_company_query_from_row(row)
        website = search_official_website_with_serper(
            serper_query, row.get("full_address") or row.get("adres", ""), logger, cache
        )

    serper_query = build_company_query_from_row(row)
    serper_cached = cache.setdefault("serper", {}).get(serper_query, {})
    if isinstance(serper_cached, dict):
        serper_source_score = int(serper_cached.get("score", 0) or 0)

    company_for_email = row.get("company_name_clean") or row.get("nazwa") or ""
    serper_blob = " ".join(
        str(row.get(k) or "")
        for k in ("nazwa", "kategoria", "www", "url", "full_address", "adres")
    )

    verification = {
        "verified": False,
        "verification_reason": "keine_website",
        "retail_chains": [],
        "is_small_firm": False,
        "verification_method": "",
        "pages_checked": [],
        "page_snippet": "",
    }
    if website and REQUIRE_WEBSITE_RETAIL_VERIFICATION:
        verification = verify_company_on_website(
            company_for_email,
            website,
            logger,
            cache,
            serper_blob=serper_blob,
            cache_key=place_url or website,
        )
        row["retail_verified"] = verification.get("verified", False)
        row["verification_reason"] = verification.get("verification_reason", "")
        row["retail_chains_found"] = ", ".join(verification.get("retail_chains") or [])
        row["is_small_firm"] = verification.get("is_small_firm", False)
        if not verification.get("verified"):
            console_step(
                f"Odrzucono (brak Einzelhandel/Hochbau-Filialbau): "
                f"{company_for_email} — {row['verification_reason']}"
            )
            skip = {
                "emails": [],
                "phones": [],
                "website": website,
                "source_urls": verification.get("pages_checked") or [],
                "page_snippet": verification.get("page_snippet") or "",
            }
            row = reconcile_contact_sources(row, skip)
            extra = {
                "company_name": company_for_email,
                "official_website": website,
                "retail_verified": False,
                "verification_reason": row["verification_reason"],
                "retail_chains_found": row.get("retail_chains_found", ""),
                "is_small_firm": row.get("is_small_firm", False),
                "email_target": "",
                "email_status": "skipped_no_retail_proof",
            }
            row.update(extra)
            contacts_cache[place_url] = {k: row.get(k) for k in extra if k in row}
            return normalize_row_company_name(row)
    elif website:
        row["retail_verified"] = True
    else:
        row["retail_verified"] = False
        row["verification_reason"] = "keine_website"
        skip = {
            "emails": [],
            "phones": [],
            "website": "",
            "source_urls": [],
            "page_snippet": "",
        }
        row = reconcile_contact_sources(row, skip)
        row["email_status"] = "skipped_no_website"
        return normalize_row_company_name(row)

    collected = (
        collect_contacts_from_website(website, logger, cache=cache)
        if website
        else {
            "emails": [],
            "phones": [],
            "website": "",
            "source_urls": [],
            "page_snippet": "",
        }
    )
    if verification.get("page_snippet"):
        collected["page_snippet"] = verification["page_snippet"]
    row = reconcile_contact_sources(row, collected)
    subject = ""
    body = ""
    mail_status = "not_sent"
    target_email, email_score, email_pick_method = resolve_inquiry_email_target(
        collected,
        website or "",
        company_for_email,
        logger,
        cache,
        cache_key=place_url,
    )
    if target_email and is_non_commercial_email(target_email):
        target_email = ""
        email_pick_method = "blocked_institution"
    if is_blocked_non_commercial_row(
        {
            **row,
            "email_target": target_email,
            "www": website,
            "nazwa": company_for_email,
        }
    ):
        target_email = ""
        email_pick_method = "blocked_institution"
        mail_status = "skipped_institution"
    elif not target_email and collected.get("emails"):
        mail_status = "no_suitable_email"
    extra = {
        "company_name": row.get("company_name_clean") or row.get("nazwa", ""),
        "company_name_raw": row.get("company_name_raw", ""),
        "company_name_clean": row.get("company_name_clean", ""),
        "official_website": collected["website"],
        "serper_source_score": serper_source_score,
        "emails_found": ", ".join(collected["emails"]),
        "phones_found": ", ".join(collected["phones"]),
        "contact_sources": ", ".join(collected["source_urls"]),
        "contact_source": row.get("contact_source", "serper"),
        "maps_contact_rejected": row.get("maps_contact_rejected", "no"),
        "email_target": target_email,
        "email_target_score": email_score,
        "email_pick_method": email_pick_method,
        "email_subject": subject,
        "email_body": body,
        "email_status": mail_status,
        "retail_verified": True,
        "verification_reason": verification.get("verification_reason", "ok"),
        "retail_chains_found": ", ".join(verification.get("retail_chains") or []),
        "is_small_firm": verification.get("is_small_firm", True),
    }
    extra["contact_quality_score"] = compute_contact_quality_score({**row, **extra})
    row.update(extra)
    contacts_cache[place_url] = extra
    return row


def _process_serper_terms(
    terms: list[str],
    label: str,
    *,
    all_rows: list,
    seen_global: set,
    cache: dict,
    logger: logging.Logger,
    enable_auto_email: bool,
    apply_distance_filter: bool,
    max_new_rows: int | None,
    total_new_rows: int,
    stop_requested: bool,
) -> tuple[int, bool]:
    """Zwraca (total_new_rows, stop_requested) po przetworzeniu listy fraz Serper."""
    by_url = index_all_rows_by_url(all_rows)
    for term in terms:
        if stop_requested:
            break
        console_step(f"Serper ({label}): {term}")
        rows = discover_places_with_serper(
            term, logger, cache, apply_location_filter=apply_distance_filter
        )
        added = 0
        refreshed = 0
        for r in rows:
            url = (r.get("url") or "").strip()
            if not url:
                continue
            existing = by_url.get(url)
            if existing and not DISCOVERY_IGNORE_CONTACT_CACHE and url in seen_global:
                continue
            if AUTO_ENRICH_CONTACTS:
                r = enrich_row_with_contacts(r, cache, logger)
            if REQUIRE_WEBSITE_RETAIL_VERIFICATION and not r.get("retail_verified"):
                reason = (r.get("verification_reason") or "").strip()
                console_step(
                    f"Übersprungen (www: {reason or 'kein GU/Filialbau/Referenzen'}): "
                    f"{r.get('nazwa', '')}"
                )
                continue
            if not (r.get("email_target") or "").strip():
                if not EXPORT_PIPELINE_ROWS_WITHOUT_EMAIL or not r.get("retail_verified"):
                    console_step(
                        f"Übersprungen (brak e-mail na www): {r.get('nazwa', '')}"
                    )
                    continue
                console_step(f"Pipeline/Excel (bez e-mail): {r.get('nazwa', '')}")
            if (r.get("email_target") or "").strip() and is_blocked_non_commercial_row(r):
                console_step(
                    f"Übersprungen (Urząd/instytucja, nie firma): {r.get('nazwa', '')}"
                )
                mark_suppressed_target(
                    cache,
                    (r.get("email_target") or "").strip(),
                    "institution",
                )
                continue
            if not is_row_eligible_for_excel_export(r):
                console_step(
                    f"Übersprungen (nie do Excela): {r.get('nazwa', '')}"
                )
                continue
            if (
                apply_distance_filter
                and ENABLE_DISTANCE_FROM_REGION_KM
                and not row_within_region_km(r)
            ):
                continue
            if enable_auto_email and r.get("email_target"):
                r["email_status"] = "queued"
                cache.setdefault("contacts", {}).setdefault(url, {})["email_status"] = "queued"
            seen_global.add(url)
            if existing:
                existing.update(r)
                refreshed += 1
            else:
                all_rows.append(r)
                by_url[url] = r
                added += 1
                total_new_rows += 1
            if max_new_rows is not None and total_new_rows >= max_new_rows:
                stop_requested = True
            persist_progress(all_rows, cache, logger, reason=f"serper +{total_new_rows}")
        suffix = f", odświeżono {refreshed}" if refreshed else ""
        print(f"{term}: +{added}{suffix}")
        persist_progress(all_rows, cache, logger, reason=f"Ende {term}")
        if len(all_rows) >= MIN_CONTACTS_TARGET:
            console_step(
                f"Cel osiągnięty: {len(all_rows)} kontaktów (target {MIN_CONTACTS_TARGET})"
            )
            break
    return total_new_rows, stop_requested


def run_scraper(
    jupyter_mode: bool | None = None,
    max_new_rows: int | None = None,
    enable_auto_email: bool | None = None,
    dry_run_email: bool = False,
    discovery_mode: str = "full",
    force_resend: bool = False,
    ignore_send_window: bool = False,
    rebuild_from_cache: bool = False,
    rotate_bundesland: bool = False,
    **_deprecated_kwargs,
):
    if jupyter_mode is None:
        jupyter_mode = is_running_in_jupyter()
    if enable_auto_email is None:
        enable_auto_email = ENABLE_AUTO_EMAIL

    logger = setup_logging()
    deprecated = [k for k in _deprecated_kwargs if _deprecated_kwargs.get(k) is not None]
    if deprecated:
        logger.warning(
            "Ignorowane przestarzałe argumenty (moduł tylko Serper): %s",
            ", ".join(deprecated),
        )
    ensure_ssl_cert_env(logger)
    if discovery_mode != "emails_only" and not get_serper_api_key():
        raise RuntimeError("Brak SERPER_API_KEY – moduł wymaga Serper API.")

    rotation_land: str | None = None
    rotation_state: dict | None = None
    rotation_state_path = None
    if rotate_bundesland and discovery_mode != "emails_only" and not rebuild_from_cache:
        from gu_bundesland_rotation import (
            apply_rotation_to_module,
            commit_rotation_after_run,
            format_rotation_status,
        )

        mod = sys.modules[__name__]
        rotation_land, rotation_state, rotation_state_path = apply_rotation_to_module(
            mod, OUTPUT_DIR
        )
        print(
            f"[ROTACJA] Discovery dla Bundesland: {rotation_land} "
            f"(1 land / cykl, min. kontaktów={MIN_CONTACTS_TARGET})"
        )
        print(f"[ROTACJA] {format_rotation_status(OUTPUT_DIR)}")

    logger.info("=== START DE GU bundesweit – GU Einzelhandelsbau bundesweit (Serper API) ===")
    print(
        "[START] Scraper Deutschland GU Filialbau – GU Neubau/Umbau Lebensmittelmärkte (Serper API)."
    )
    print(
        f"[MODUS] Jupyter={jupyter_mode} | Auto-Mail={enable_auto_email} | "
        f"DryRun={dry_run_email} | Discovery={discovery_mode} | "
        f"ForceResend={force_resend} | IgnoreWindow={ignore_send_window} | "
        f"RebuildCache={rebuild_from_cache} | "
        f"IgnoreContactCache={DISCOVERY_IGNORE_CONTACT_CACHE}"
    )
    if max_new_rows is not None:
        print(f"[LIMIT] max. nowych wierszy: {max_new_rows}")
    print(f"[TARGET] min. kontaktów: {MIN_CONTACTS_TARGET}")

    cache = load_cache(logger)
    if rebuild_from_cache:
        all_rows = build_all_rows_from_cache(cache)
        seen_global = build_discovery_seen_urls(all_rows, cache)
        console_step(
            f"Excel aus Cache neu: {len(all_rows)} Zeilen "
            f"(contacts={len(cache.get('contacts', {}))}, także bez E-Mail)"
        )
        persist_progress(all_rows, cache, logger, reason="rebuild_from_cache")
    else:
        all_rows, _seen_from_file = load_existing_output(OUTPUT_FILE, logger)
        seen_global = build_discovery_seen_urls(all_rows, cache)
    cache_contacts_n = len(cache.get("contacts", {}) or {})
    ignore_note = (
        "ignoruj contacts JSON przy discovery"
        if DISCOVERY_IGNORE_CONTACT_CACHE
        else f"+{cache_contacts_n} URL z contacts JSON w seen"
    )
    console_step(
        f"Start: wierszy={len(all_rows)}, seen={len(seen_global)} ({ignore_note})"
    )
    merged = merge_cache_contacts_into_pipeline(all_rows, cache)
    if merged:
        console_step(
            f"Z cache JSON dopisano {merged} firm do pipeline (łącznie {len(all_rows)})"
        )
        seen_global = build_discovery_seen_urls(all_rows, cache)
    total_new_rows = 0
    stop_requested = False

    try:
        if discovery_mode == "emails_only":
            console_step("Tylko wysyłka maili z cache (bez wyszukiwania Serper)")
        else:
            total_new_rows, stop_requested = _process_serper_terms(
                SERPER_DISCOVERY_TERMS,
                "primary",
                all_rows=all_rows,
                seen_global=seen_global,
                cache=cache,
                logger=logger,
                enable_auto_email=enable_auto_email,
                apply_distance_filter=True,
                max_new_rows=max_new_rows,
                total_new_rows=total_new_rows,
                stop_requested=stop_requested,
            )
            if not stop_requested and len(all_rows) < MIN_CONTACTS_TARGET:
                console_step(
                    f"Za mało kontaktów ({len(all_rows)}). Fallback Serper bez filtra odległości."
                )
                total_new_rows, stop_requested = _process_serper_terms(
                    SERPER_DISCOVERY_FALLBACK_TERMS,
                    "fallback",
                    all_rows=all_rows,
                    seen_global=seen_global,
                    cache=cache,
                    logger=logger,
                    enable_auto_email=enable_auto_email,
                    apply_distance_filter=False,
                    max_new_rows=max_new_rows,
                    total_new_rows=total_new_rows,
                    stop_requested=stop_requested,
                )

        if enable_auto_email:
            reenrich_contacts_for_mailing(
                all_rows,
                cache,
                logger,
                refresh_all=force_resend,
            )
            _process_email_jobs(
                all_rows,
                cache,
                logger,
                dry_run_email=dry_run_email,
                force_resend=force_resend,
                ignore_send_window=ignore_send_window,
            )
    finally:
        persist_progress(all_rows, cache, logger, reason="Ende Lauf")

    if (
        rotation_land
        and rotation_state is not None
        and rotation_state_path is not None
        and discovery_mode != "emails_only"
    ):
        from gu_bundesland_rotation import commit_rotation_after_run

        nxt = commit_rotation_after_run(
            rotation_state_path, rotation_state, rotation_land
        )
        print(
            f"[ROTACJA] Zakończono falę {rotation_land}. "
            f"Następny cykl: {nxt}"
        )

    logger.info(f"Fertig. {len(all_rows)} Zeilen -> {OUTPUT_FILE}")
    print(f"\nFertig. {len(all_rows)} Zeilen -> {OUTPUT_FILE}")


def run_in_jupyter(
    enable_auto_email: bool | None = None,
    max_new_rows: int | None = None,
    dry_run_email: bool = True,
    **_deprecated_kwargs,
):
    """Wejście dla Jupyter Lab (tylko Serper API)."""
    if enable_auto_email is None:
        enable_auto_email = ENABLE_AUTO_EMAIL
    console_step(
        f"Jupyter: auto_mail={enable_auto_email}, dry_run={dry_run_email}, discovery=serper_only"
    )
    run_scraper(
        jupyter_mode=True,
        max_new_rows=max_new_rows,
        enable_auto_email=enable_auto_email,
        dry_run_email=dry_run_email,
        **_deprecated_kwargs,
    )


def _run_smoke_tests() -> None:
    assert normalize_website("example.de") == "https://example.de"
    assert normalize_website("") == ""
    assert clean_company_name("  GU Ladenbau XY  | Start", "https://bau.de") == "Bau"
    assert (
        clean_company_name(
            "Edeka Fellenzer, Puderbach",
            "https://heger-store.de/referenz/edeka-fellenzer-puderbach/",
        )
        == "Heger Store"
    )
    assert (
        clean_company_name(
            "by bioPress Verlag KG",
            "https://www.biopress.de/de/inhalte/details/10651/",
        )
        == "by bioPress Verlag KG"
    )
    assert website_base_url("https://heger-store.de/referenz/x") == "https://heger-store.de"
    assert extract_bundesland({"bundesland": "Sachsen"}) == "Sachsen"
    assert extract_bundesland({"full_address": "04109 Leipzig"}) == "Sachsen"
    assert haversine_km(REGION_CENTER_LAT, REGION_CENTER_LON, REGION_CENTER_LAT, REGION_CENTER_LON) < 0.01
    assert location_within_region_km("Generalunternehmer Ladenbau Leipzig")
    assert location_within_region_km("Generalunternehmer München")
    assert location_within_region_km("GU Filialbau Köln Nordrhein-Westfalen")
    assert ENABLE_PLZ_PREFIX_REGION_MATCH is False
    assert ENABLE_REGION_PLZ_FILTER is False
    assert "Deutschland" in INQUIRY_REGION_DE
    assert "Aldi" in RETAIL_CHAINS_DE
    assert "MFG Moderner Fliesenboden GmbH" in FIXED_GU_INQUIRY_DE
    assert "spezialisiertes Bodenlegerunternehmen" in FIXED_GU_INQUIRY_DE
    assert "Rüttelboden" in FIXED_GU_INQUIRY_DE
    assert "Lebensmitteleinzelhandel" in FIXED_GU_INQUIRY_DE
    assert "ALDI, REWE, NETTO" in FIXED_GU_INQUIRY_DE
    assert "Fliesen- & Estricharbeiten" in FIXED_EMAIL_SUBJECT_DE
    assert "Maksym Swinczak" in FIXED_GU_INQUIRY_DE
    assert FIXED_EMAIL_SUBJECT_DE.startswith("Kooperationsanfrage")
    assert choose_subject_variant("Test GmbH") == FIXED_EMAIL_SUBJECT_DE
    assert GOOGLE_SLIDES_PRESENTATION_ID == "12h0_knRQVTU9sRg9kqh8dxjSiuuKx0TA"
    _att = ensure_mfg_email_attachment(CAMPAIGN_DIR)
    if _att and _att.is_file():
        assert get_email_attachments_de_gu()[0].endswith(".pptx")
    assert callable(send_email_de_gu)
    body = _assemble_inquiry_email_body("Test GmbH", "Kurzer Test.")
    assert body == FIXED_GU_INQUIRY_DE.strip()
    cleaned = sanitize_email_body(FIXED_GU_INQUIRY_DE)
    assert "\n\n" in cleaned
    assert cleaned.count("\n\n") >= 5
    assert "Sehr geehrte" in cleaned
    assert "Mit freundlichen Grüßen" in cleaned
    assert "Kurzer Test" not in body
    assert is_germany_de_candidate("https://firma.de/kontakt", "GU Leipzig", "")
    assert "@" in prepare_text_for_email_extraction("info (at) example.de")
    assert find_emails_in_text("Kontakt: name at example.de") == ["name@example.de"]
    assert find_emails_in_text("info (at) example.de") == ["info@example.de"]
    assert find_emails_in_text("vertrieb (at) firma (dot) de") == ["vertrieb@firma.de"]
    assert find_phones_in_text("Tel: +49 341 1234567 und 0341 987654") != []
    assert "GmbH" in find_company_name_in_text(
        "Willkommen bei Muster Bau GmbH — Kontakt"
    )
    assert ENABLE_GEMINI_CONTACT_TEXT_CLEANUP is False
    assert ENABLE_REGION_PLZ_FILTER is False
    assert len(SERPER_DISCOVERY_TERMS) >= 20
    from gu_bundesland_rotation import (
        BUNDESLAND_ROTATION_ORDER,
        peek_next_bundesland,
    )

    assert len(BUNDESLAND_ROTATION_ORDER) == 16
    assert peek_next_bundesland() in BUNDESLAND_ROTATION_ORDER
    from mfg_mail_recipients import merge_mfg_campaign_cc

    assert "office@mfg-fliesen.de" not in [
        a.lower() for a in merge_mfg_campaign_cc("kontakt@firma.de", "")
    ]
    assert is_rejected_company_name_for_export(
        "[PDF] X öffentlich nichtöffentlich", "", "shop@pdf-xchange.de"
    )
    assert is_rejected_company_name_for_export("Erfurt", "", "")
    assert is_rejected_company_name_for_export(
        "Max Wiessner Baugeschäft GmbH", "https://maxwiessner.de", "office@maxwiessner.de"
    )
    assert is_excluded_kontrahent(
        name="NEULA GmbH", url="https://neula.de", email="info@neula.de"
    )[0]
    assert _company_name_has_legal_form("Kultbau GmbH")
    assert is_non_commercial_email("info@leipzig.de")
    assert is_non_commercial_email("service@thueringen-entdecken.de")
    assert not is_non_commercial_email("office@maxwiessner.de")
    assert is_non_commercial_contact(name="Stadt Leipzig, Dezernat Wirtschaft")
    assert not is_valid_commercial_company_contact(
        email="info@tgzp.de",
        name="Potsdamer Technologie- und Gründerzentren",
    )
    assert not is_valid_commercial_company_contact(
        email="info@ibau.de", name="Generalunternehmer"
    )
    assert is_valid_commercial_company_contact(
        email="info@sus-bau.de",
        url="https://sus-bau.de",
        name="Baufirma SuS Bau",
    )
    assert is_valid_retail_store_builder_contact(
        email="info@logmar.net",
        url="https://www.logmar.net/",
        name="Logmar Ladenbau GmbH",
        text="Filialbau Aldi Rewe Referenzprojekte",
    )
    assert not is_valid_retail_store_builder_contact(
        name="Bau GmbH",
        text="Generalunternehmer Filialbau Supermarkt Neubau — keine Projektgalerie",
    )
    assert is_valid_retail_store_builder_contact(
        name="Weber Generalunternehmer GmbH",
        text=(
            "Generalunternehmer Filialumbau Marktmodernisierung Rewe Aldi. "
            "Referenzprojekte und Portfolio."
        ),
    )
    assert not is_valid_retail_store_builder_contact(
        name="Kultbau GmbH",
        text="Altbausanierung Wohnhaus Erfurt ohne Einzelhandel",
    )
    assert not is_valid_retail_store_builder_contact(
        url="https://www.kultbaugmbh.de/erfurt/bausanierung",
        name="Kultbau GmbH",
        text="Altbausanierung Bausanierung Erfurt",
    )
    assert not is_valid_retail_store_builder_contact(
        url="https://www.rewe.de/shop",
        name="REWE Markt",
        text="Öffnungszeiten Prospekt Filialfinder",
    )
    assert is_unsuitable_inquiry_email("privacy@firma.de")
    best, sc = pick_best_email_for_inquiry(
        ["datenschutz@obi.de", "info@logmar.net"],
        "https://www.logmar.net/",
    )
    assert best == "info@logmar.net" and sc >= MIN_EMAIL_SCORE_FOR_SEND
    best_puny, sc_puny = pick_best_email_for_inquiry(
        ["info@eichstaedtbau.de", "d@enschutzhinweisen.akzeptieren"],
        "https://xn--bauunternehmen-eichstdt-g8b.de/neubau-edeka-in-halle/",
    )
    assert best_puny == "info@eichstaedtbau.de" and sc_puny >= MIN_EMAIL_SCORE_FOR_SEND
    assert is_junk_scraped_email("d@enschutzhinweisen.akzeptieren")
    assert is_junk_scraped_email("element.d@aset.rocketlazyload")
    assert not is_junk_scraped_email("info@eichstaedtbau.de")
    imp_first = sort_contact_urls_priority_pl(
        ["https://firma.de/kontakt", "https://firma.de/impressum", "https://firma.de/datenschutz"]
    )
    assert _is_impressum_url(imp_first[0])
    guessed = guess_impressum_urls("https://www.beispiel-bau.de/leistungen/")
    assert any("/impressum" in u for u in guessed)
    seen_ignore = build_discovery_seen_urls(
        [{"url": "https://a.de"}], {"contacts": {"https://b.de": {}}}
    )
    assert "https://a.de" in seen_ignore and "https://b.de" not in seen_ignore
    assert DISCOVERY_IGNORE_CONTACT_CACHE is True
    assert EXPORT_PIPELINE_ROWS_WITHOUT_EMAIL is True
    assert is_row_eligible_for_excel_export(
        {
            "nazwa": "Müller Ladenbau GmbH",
            "url": "https://mueller-ladenbau.de",
            "email_target": "",
            "retail_verified": True,
            "verification_reason": "referenz_ladenbau",
            "page_snippet": "Referenzprojekte Aldi Filialbau",
        }
    )
    rows_export = build_export_rows(
        [
            {
                "nazwa": "Test Bau GmbH",
                "company_name_clean": "Test Bau GmbH",
                "url": "https://test-bau.de",
                "www": "https://test-bau.de",
                "email_target": "",
                "retail_verified": True,
                "verification_reason": "referenz_filialbau",
                "page_snippet": "Filialbau Referenzprojekte Supermarkt",
            }
        ]
    )
    assert len(rows_export) == 1 and rows_export[0].get("E-mail") == ""
    ok, chains, _ = page_mentions_retail_store_projects(
        "Wir realisieren Aldi und Rewe Filialneubau im Ladenbau in Sachsen. Referenzen."
    )
    assert ok and "aldi" in chains
    ok_hb, chains_hb, _ = page_mentions_retail_store_projects(
        "Generalunternehmer Hochbau: Aldi-Filialgebäude und Kaufland-Neubau in Sachsen. Referenzprojekte."
    )
    assert ok_hb and "aldi" in chains_hb
    ok_ohne, _, reason_ohne = page_mentions_retail_store_projects(
        "Generalunternehmer Filialbau Supermarkt Neubau. "
        "Wir bauen Discounter im Einzelhandel — ohne Projektgalerie."
    )
    assert not ok_ohne and reason_ohne == "kein_markt_nachweis"
    ok_nur_ref, _, reason_nur = page_mentions_retail_store_projects(
        "Generalunternehmer Filialbau. Referenzen Hallenbau und Bürobau — keine Supermarktprojekte."
    )
    assert not ok_nur_ref and reason_nur == "kein_markt_nachweis"
    ok_foto, chains_foto, reason_foto = page_mentions_retail_store_projects(
        "Generalunternehmer Filialbau Sachsen. Fotogalerie — Rewe Markt Neubau Cottbus, "
        "Bilder Supermarkt Umbau. alt-kaufland-filiale.jpg"
    )
    assert ok_foto and "rewe" in chains_foto
    assert "referenz" in reason_foto or "kette" in reason_foto
    ok_ref, chains_ref, reason_ref = page_mentions_retail_store_projects(
        "Generalunternehmer Filialbau. Referenzprojekte Aldi und Rewe. Unsere Projekte."
    )
    assert ok_ref and "referenz" in reason_ref
    assert "aldi" in chains_ref
    ok_shop, _, reason_shop = page_mentions_retail_store_projects(
        "REWE Markt Erfurt — Öffnungszeiten und Wochenangebot. Filialfinder."
    )
    assert not ok_shop and reason_shop == "einzelhandel_betrieb_kein_bau"
    assert "schlüsselfertig" in RETAIL_BUILD_KEYWORDS
    assert len(SERPER_DISCOVERY_TERMS) >= 60
    assert "ladeneinrichtung" in SERPER_NEGATIVE_TERMS
    assert "11880.com" in SERPER_BAD_DOMAINS
    from http_page_guard import is_waf_blocked

    assert is_waf_blocked(exc=Exception("522 ServerError for url"))
    assert is_waf_blocked(
        html="<html><title>Just a moment...</title>cdn-cgi/challenge</html>"
    )
    assert not is_waf_blocked(html="<html><body>Normalna firma budowlana GmbH</body></html>")
    assert is_likely_large_company("STRABAG SE", "https://www.strabag.com", "")[0]
    assert not is_likely_large_company(
        "Müller Ladenbau GmbH",
        "https://mueller-ladenbau.de",
        "Familienunternehmen Referenz Aldi Filialbau regional",
    )[0]
    print("_run_smoke_tests: OK")


def main(run_config_path: str | Path | None = None):
    import sys as _sys
    from pathlib import Path as _Path

    launch_kw: dict = {}
    if run_config_path:
        from scraper_run_config import apply_run_config_file, run_scraper_launch_kwargs

        mod = _sys.modules[__name__]
        apply_run_config_file(mod, _Path(run_config_path), _Path(__file__).resolve().parent)
        launch_kw = run_scraper_launch_kwargs(mod)
    run_scraper(
        jupyter_mode=is_running_in_jupyter(),
        **launch_kw,
    )


if __name__ == "__main__":
    import sys

    if "--test" in sys.argv:
        _run_smoke_tests()
    else:
        rc_path = None
        if "--run-config" in sys.argv:
            i = sys.argv.index("--run-config")
            if i + 1 < len(sys.argv):
                rc_path = sys.argv[i + 1]
        extra_kw: dict = {}
        if "--send-emails-only" in sys.argv:
            extra_kw.update(
                {
                    "discovery_mode": "emails_only",
                    "enable_auto_email": True,
                    "dry_run_email": False,
                }
            )
            print("[TRYB] Tylko wysyłka maili z cache (bez nowego wyszukiwania).")
        if "--backfill-emails-from-cache" in sys.argv:
            logger = setup_logging()
            cache = load_cache(logger)
            stats = backfill_emails_in_cache(cache, logger)
            save_cache(cache, logger)
            all_rows = build_all_rows_from_cache(cache)
            save_excel(all_rows, OUTPUT_FILE, logger, cache=cache)
            print(
                f"[BACKFILL] cache zapisany → {CACHE_FILE}\n"
                f"  sprawdzono={stats['checked']}, uzupelniono={stats['filled']}, "
                f"zmieniono={stats['updated']}, oczyszczono emails_found={stats['cleaned_found']}, "
                f"nadal bez maila={stats['still_empty']}\n"
                f"  Excel → {OUTPUT_FILE} ({len(all_rows)} wierszy pipeline)"
            )
            raise SystemExit(0)
        if "--rebuild-from-cache" in sys.argv:
            extra_kw["rebuild_from_cache"] = True
            if "discovery_mode" not in extra_kw:
                extra_kw["discovery_mode"] = "emails_only"
            print("[TRYB] Excel i wiersze pipeline z cache JSON (tylko rekordy z E-Mail).")
        if "--purge-institutions" in sys.argv:
            logger = setup_logging()
            cache = load_cache(logger)
            print(
                f"[CACHE] JSON oczyszczony: contacts={len(cache.get('contacts', {}))} "
                f"→ {CACHE_FILE}"
            )
            raise SystemExit(0)
        if "--force-resend" in sys.argv:
            extra_kw["force_resend"] = True
            print("[TRYB] Ponowna wysyłka także do adresów ze statusem sent.")
        if "--ignore-send-window" in sys.argv:
            extra_kw["ignore_send_window"] = True
            print("[TRYB] Wysyłka poza oknem 8–18.")
        if "--dry-run-email" in sys.argv:
            extra_kw["dry_run_email"] = True
            print("[TRYB] Dry-run: treść maili bez faktycznej wysyłki.")
        if "--respect-cache" in sys.argv:
            globals()["DISCOVERY_IGNORE_CONTACT_CACHE"] = False
            print(
                "[TRYB] Discovery respektuje contacts JSON (pomija znane URL, "
                "bez ponownego www)."
            )
        if "--bundesland" in sys.argv:
            i = sys.argv.index("--bundesland")
            if i + 1 < len(sys.argv):
                bl = sys.argv[i + 1].split(",")
                configure_campaign_bundeslaender(sys.modules[__name__], bl)
                print(f"[TRYB] Aktywne Bundesländer: {', '.join(CAMPAIGN_ACTIVE_BUNDESLAENDER)}")
        if "--rotation-status" in sys.argv:
            from gu_bundesland_rotation import format_rotation_status

            print(format_rotation_status(OUTPUT_DIR))
            raise SystemExit(0)
        rotate_bl = "--rotate-bundesland" in sys.argv
        if rotate_bl:
            extra_kw["rotate_bundesland"] = True
            print("[TRYB] Rotacja Bundesland: 1 land na cykl discovery.")
        if rc_path:
            from scraper_run_config import apply_run_config_file, run_scraper_launch_kwargs

            mod = sys.modules[__name__]
            apply_run_config_file(mod, Path(rc_path), Path(__file__).resolve().parent)
            try:
                with open(Path(rc_path), encoding="utf-8") as _rcf:
                    apply_gu_run_config_extras(mod, json.load(_rcf))
            except Exception:
                pass
            launch_kw = run_scraper_launch_kwargs(mod)
            launch_kw.update(extra_kw)
            run_scraper(jupyter_mode=is_running_in_jupyter(), **launch_kw)
        else:
            run_scraper(jupyter_mode=is_running_in_jupyter(), **extra_kw)

