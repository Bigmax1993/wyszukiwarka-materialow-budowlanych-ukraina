# -*- coding: utf-8 -*-
"""
Tekst maila — zapytanie ofertowe do hurtowni materiałów budowlanych (polski).
Domyślny telefon kontaktowy: 516513965 (+48).
"""
from __future__ import annotations

import re

_UA_PHONE_INLINE_RE = re.compile(
    r"(?:\+380|00380)\s*[\d\s()./-]{5,}\d",
    re.IGNORECASE,
)
_FOREIGN_TEL_LINE_RE = re.compile(
    r"^\s*(?:tel\.?|telefon|phone)\s*[.:]?\s*(?:\+380|00380|\+49|0049)[\d\s()./-]*\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_LEGACY_BRANDING_RE = re.compile(
    r"\b(?:mfg|moderner\s*fliesen\w*|fliesenboden|gmbh)\b",
    re.IGNORECASE,
)


def is_foreign_campaign_phone(phone: str) -> bool:
    raw = (phone or "").strip()
    if not raw:
        return False
    low = raw.lower().replace(" ", "")
    if low.startswith("+380") or low.startswith("00380"):
        return True
    if low.startswith("+49") or low.startswith("0049"):
        return True
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("380") and len(digits) >= 11:
        return True
    return digits.startswith("49") and len(digits) >= 11


def strip_foreign_phones_from_text(text: str) -> str:
    if not text:
        return ""
    out = _FOREIGN_TEL_LINE_RE.sub("", text)
    out = _UA_PHONE_INLINE_RE.sub("", out)
    out = re.sub(r"\b(?:tel\.?|telefon|phone)\s*[.:]?\s*(?=\s|$)", "", out, flags=re.IGNORECASE)
    out = re.sub(r"[ \t]+,", ",", out)
    out = re.sub(r",\s*,", ",", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip(" ,\n")


def strip_legacy_branding(text: str) -> str:
    if not text:
        return ""
    out = strip_foreign_phones_from_text(text)
    out = _LEGACY_BRANDING_RE.sub("", out)
    out = re.sub(r"\s+", " ", out).strip(" ,;-")
    return out


def _clean_sender_display_name(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    text = re.sub(r"\b(tel|telefon|phone)\b.*$", "", text, flags=re.IGNORECASE).strip()
    text = strip_foreign_phones_from_text(text)
    text = re.sub(r"https?://\S+|\bwww\.\S+|\S+@\S+", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"\+?\d[\d\s()./-]{5,}\d", "", text).strip()
    text = strip_legacy_branding(text)
    return re.sub(r"\s+", " ", text).strip(" ,;-")


DEFAULT_INQUIRY_SENDER_NAME_PL = "Maksym Świńczak"
DEFAULT_INQUIRY_PHONE_PL = "516513965"


def inquiry_sender_name() -> str:
    from scraper_env import get_mail_sender_name

    cleaned = _clean_sender_display_name(get_mail_sender_name() or "")
    if not cleaned or any(x in cleaned.lower() for x in ("свінчак", "свинчак", "mfg", "fliesen")):
        return DEFAULT_INQUIRY_SENDER_NAME_PL
    return cleaned


def inquiry_company_name() -> str:
    from scraper_env import get_env_value

    return strip_legacy_branding(get_env_value("INQUIRY_COMPANY_NAME").strip())


def inquiry_phone() -> str:
    from scraper_env import get_env_value

    phone = get_env_value("INQUIRY_PHONE").strip()
    if phone and not is_foreign_campaign_phone(phone):
        return phone
    return DEFAULT_INQUIRY_PHONE_PL


def inquiry_website() -> str:
    from scraper_env import get_env_value

    return get_env_value("INQUIRY_WEBSITE").strip()


def build_inquiry_signature_pl() -> str:
    lines = ["Z poważaniem,", ""]
    name = inquiry_sender_name()
    if name:
        lines.append(name)
    company = inquiry_company_name()
    if company:
        lines.extend(["", company])
    web = inquiry_website()
    if web:
        lines.extend(["", web])
    phone = inquiry_phone()
    lines.extend(["", f"Tel.: {phone}"])
    return strip_legacy_branding("\n".join(lines).strip())


def build_inquiry_sender_brief_pl() -> str:
    company = inquiry_company_name()
    who = company if company else "Kupujący materiałów budowlanych"
    return (
        f"{who} poszukuje dostawców materiałów budowlanych w Polsce do regularnych "
        "zakupów hurtowych (cement, piasek, żwir, cegła, bloczki, stal zbrojeniowa, "
        "styropian, wełna mineralna, płyty gipsowe, dachówki, zaprawy, farby itd.)."
    )


def build_sender_contact_line_pl() -> str:
    parts: list[str] = []
    name = inquiry_sender_name()
    if name:
        parts.append(name)
    company = inquiry_company_name()
    if company:
        parts.append(company)
    web = inquiry_website()
    if web:
        parts.append(web)
    parts.append(f"Tel. {inquiry_phone()}")
    return strip_legacy_branding(", ".join(parts))


def build_fixed_material_inquiry_pl() -> str:
    intro = (
        "zwracam się z zapytaniem o możliwość dostawy materiałów budowlanych "
        "na warunkach hurtowych."
    )
    if inquiry_company_name():
        intro = (
            f"zwracam się w imieniu {inquiry_company_name()}. "
            "Poszukujemy sprawdzonych dostawców materiałów budowlanych w Polsce "
            "do regularnych zakupów."
        )
    return f"""Szanowni Państwo,

{intro}

Interesuje nas szeroki asortyment: cement, piasek, żwir, kruszywa, cegła, bloczki, stal zbrojeniowa, styropian, wełna mineralna, płyty gipsowe, pokrycia dachowe, zaprawy, farby i produkty pokrewne. Zależą nam na cenach hurtowych, dostępności magazynowej oraz możliwości dostawy.

Prosimy o przesłanie aktualnego cennika lub wskazanie osoby kontaktowej z działu sprzedaży / hurtu.

Dziękujemy za współpracę.

{build_inquiry_signature_pl()}"""


FIXED_MATERIAL_INQUIRY_PL = build_fixed_material_inquiry_pl()


def inquiry_email_signature_pl() -> str:
    return build_inquiry_signature_pl()


def inquiry_sender_brief_pl() -> str:
    return build_inquiry_sender_brief_pl()


INQUIRY_EMAIL_SIGNATURE_PL = build_inquiry_signature_pl()
INQUIRY_SENDER_BRIEF_PL = build_inquiry_sender_brief_pl()

# Aliasy kompatybilności ze scraperem (fork UA)
strip_de_campaign_branding = strip_legacy_branding
strip_german_phones_from_text = strip_foreign_phones_from_text
