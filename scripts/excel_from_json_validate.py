# -*- coding: utf-8 -*-
"""Walidacja Excel vs cache JSON: przepuszcza potrzebne dane z JSON i uzupelnia braki."""
from __future__ import annotations

from typing import Any

EXCEL_REQUIRED_IF_JSON_HAS = (
    "Nazwa firmy",
    "E-mail",
    "Telefon",
    "Adres",
    "Obwód",
    "Strona www",
    "URL",
)


def _s(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def first_email_from_contact(info: dict) -> str:
    email = _s(info.get("email_target"))
    if email and "@" in email:
        return email
    found = [
        x.strip()
        for x in _s(info.get("emails_found")).split(",")
        if x.strip() and "@" in x
    ]
    return found[0] if found else ""


def first_phone_from_contact(info: dict) -> str:
    phone = _s(info.get("phones_found"))
    if "," in phone:
        phone = phone.split(",", 1)[0].strip()
    return phone


def json_contact_has_needed_data(place_url: str, info: Any) -> bool:
    """Przepuszcza rekord JSON, jesli ma dane potrzebne w Excelu (nazwa/mail/telefon + URL)."""
    if not isinstance(info, dict):
        return False
    url = _s(place_url) or _s(info.get("official_website"))
    if not url:
        return False
    name = (
        _s(info.get("company_name_clean"))
        or _s(info.get("company_name"))
        or _s(info.get("company_name_raw"))
    )
    email = first_email_from_contact(info)
    phone = first_phone_from_contact(info)
    if email or phone:
        return True
    if name and name.lower() not in {"nieznana firma", "unknown", "-"}:
        return True
    return False


def contact_richness(info: dict) -> int:
    if not isinstance(info, dict):
        return 0
    score = 0
    for key in (
        "company_name_clean",
        "company_name",
        "email_target",
        "emails_found",
        "phones_found",
        "full_address",
        "official_website",
        "bundesland",
        "email_status",
        "retail_chains_found",
    ):
        if _s(info.get(key)):
            score += 2 if key in {"email_target", "emails_found", "phones_found"} else 1
    if info.get("retail_verified"):
        score += 1
    return score


def merge_contact_info(base: dict, incoming: dict) -> dict:
    out = dict(base or {})
    for key, val in (incoming or {}).items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = merge_contact_info(out[key], val)
            continue
        if val in (None, "", [], {}):
            continue
        cur = out.get(key)
        if cur in (None, "", [], {}):
            out[key] = val
            continue
        if isinstance(val, str) and isinstance(cur, str) and len(val) > len(cur):
            out[key] = val
        elif isinstance(val, bool) and val and not cur:
            out[key] = val
        elif isinstance(val, (int, float)) and isinstance(cur, (int, float)) and val > cur:
            out[key] = val
    return out


def merge_contacts_maps(*maps: dict) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    for blob in maps:
        if not isinstance(blob, dict):
            continue
        for url, info in blob.items():
            key = _s(url)
            if not key or not isinstance(info, dict):
                continue
            if key not in merged:
                merged[key] = dict(info)
            elif contact_richness(info) >= contact_richness(merged[key]):
                merged[key] = merge_contact_info(merged[key], info)
            else:
                merged[key] = merge_contact_info(info, merged[key])
    return merged


def pipeline_row_from_json(place_url: str, info: dict) -> dict:
    name = (
        _s(info.get("company_name_clean"))
        or _s(info.get("company_name"))
        or _s(info.get("company_name_raw"))
    )
    email = first_email_from_contact(info)
    phone = first_phone_from_contact(info)
    website = _s(info.get("official_website")) or _s(place_url)
    return {
        "url": _s(place_url) or website,
        "www": website,
        "official_website": website,
        "nazwa": name,
        "company_name_clean": name,
        "company_name_raw": _s(info.get("company_name_raw")) or name,
        "email_target": email,
        "emails_found": _s(info.get("emails_found")),
        "telefon": phone,
        "phones_found": _s(info.get("phones_found")) or phone,
        "full_address": _s(info.get("full_address")),
        "adres": _s(info.get("full_address")),
        "bundesland": _s(info.get("bundesland")) or _s(info.get("discovery_bundesland")),
        "retail_verified": bool(info.get("retail_verified")),
        "verification_reason": _s(info.get("verification_reason")),
        "page_snippet": _s(info.get("page_snippet")),
        "retail_chains_found": _s(info.get("retail_chains_found")),
        "is_gu": bool(info.get("is_gu")),
        "is_small_firm": info.get("is_small_firm", True),
        "gu_marker": _s(info.get("gu_marker")),
        "email_status": _s(info.get("email_status")),
        "contact_sources": _s(info.get("contact_sources")),
        "contact_quality_score": int(info.get("contact_quality_score", 0) or 0),
    }


def excel_row_from_json(place_url: str, info: dict) -> dict:
    row = pipeline_row_from_json(place_url, info)
    return {
        "Nazwa firmy": row["nazwa"],
        "Adres": row["adres"],
        "Obwód": row["bundesland"],
        "Telefon": row["telefon"],
        "E-mail": row["email_target"],
        "Strona www": row["www"],
        "URL": row["url"],
        "Kategoria materiałów": row["retail_chains_found"],
        "WWW sprawdzone": "tak" if row["retail_verified"] else "nie",
        "Mała firma": "tak" if row["is_small_firm"] else "nie",
        "Generalny wykonawca": "tak" if row["is_gu"] else "nie",
        "Znacznik GW": row["gu_marker"],
        "Status": row["email_status"],
    }


def index_excel_by_url(export_rows: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for rec in export_rows:
        for key in (rec.get("URL"), rec.get("Strona www")):
            url = _s(key)
            if url and url not in out:
                out[url] = rec
    return out


def json_field_for_excel_col(info: dict, col: str, place_url: str) -> str:
    if col == "Nazwa firmy":
        return (
            _s(info.get("company_name_clean"))
            or _s(info.get("company_name"))
            or _s(info.get("company_name_raw"))
        )
    if col == "Adres":
        return _s(info.get("full_address"))
    if col in ("Obwód", "Województwo"):
        return _s(info.get("bundesland")) or _s(info.get("discovery_bundesland"))
    if col == "Telefon":
        return first_phone_from_contact(info)
    if col == "E-mail":
        return first_email_from_contact(info)
    if col == "Strona www":
        return _s(info.get("official_website")) or _s(place_url)
    if col == "URL":
        return _s(place_url) or _s(info.get("official_website"))
    if col in ("Kategoria materiałów", "Kategorie_materialow"):
        return _s(info.get("retail_chains_found"))
    if col == "Status":
        return _s(info.get("email_status"))
    return ""


def find_excel_gaps(contacts: dict[str, dict], export_rows: list[dict]) -> list[dict]:
    """Luki: brak wiersza albo pusta kolumna Excela przy niepustym polu JSON."""
    by_url = index_excel_by_url(export_rows)
    gaps: list[dict] = []
    for place_url, info in contacts.items():
        if not json_contact_has_needed_data(place_url, info):
            continue
        rec = by_url.get(_s(place_url))
        if rec is None:
            gaps.append({"url": _s(place_url), "reason": "missing_row", "columns": ["*"]})
            continue
        missing_cols = []
        for col in EXCEL_REQUIRED_IF_JSON_HAS:
            json_val = json_field_for_excel_col(info, col, place_url)
            excel_val = _s(rec.get(col))
            if json_val and not excel_val:
                missing_cols.append(col)
        if missing_cols:
            gaps.append(
                {"url": _s(place_url), "reason": "empty_columns", "columns": missing_cols}
            )
    return gaps


def fill_export_from_json(contacts: dict[str, dict], export_rows: list[dict]) -> tuple[list[dict], int]:
    """Uzupelnia Excel danymi z JSON. Zwraca (wiersze, liczba zmian)."""
    by_url = index_excel_by_url(export_rows)
    changed = 0
    for place_url, info in contacts.items():
        if not json_contact_has_needed_data(place_url, info):
            continue
        url = _s(place_url)
        rec = by_url.get(url)
        if rec is None:
            rec = excel_row_from_json(place_url, info)
            export_rows.append(rec)
            by_url[url] = rec
            changed += 1
            continue
        filled = excel_row_from_json(place_url, info)
        for col, val in filled.items():
            if _s(val) and not _s(rec.get(col)):
                rec[col] = val
                changed += 1
    return export_rows, changed


def verify_and_fill_until_complete(
    contacts: dict[str, dict],
    export_rows: list[dict],
    *,
    max_rounds: int = 5,
) -> tuple[list[dict], list[dict], int]:
    """Petla: weryfikacja calego Excela → JSON → uzupelnienie."""
    rounds = 0
    gaps = find_excel_gaps(contacts, export_rows)
    while gaps and rounds < max_rounds:
        export_rows, _n = fill_export_from_json(contacts, export_rows)
        rounds += 1
        gaps = find_excel_gaps(contacts, export_rows)
    return export_rows, gaps, rounds
