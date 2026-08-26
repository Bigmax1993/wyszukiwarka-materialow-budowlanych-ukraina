# -*- coding: utf-8 -*-
"""Zbiorczy Excel UA: unia kolumn, append wierszy, nagłówki tylko po polsku."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

SHEET_INFO = "Info"
SHEET_KONTAKTY = "Kontakty"
SHEET_OBWODY = "Obwody"

SHEET_ALIASES = {
    "info": SHEET_INFO,
    "kontakte": SHEET_KONTAKTY,
    "kontakty": SHEET_KONTAKTY,
    "baza firm": SHEET_KONTAKTY,
    "wojewodztwa": SHEET_OBWODY,
    "województwa": SHEET_OBWODY,
    "bundeslaender": SHEET_OBWODY,
    "bundesländer": SHEET_OBWODY,
    "obwody": SHEET_OBWODY,
}

HEADER_ALIASES = {
    "firmenname": "Nazwa firmy",
    "firma": "Nazwa firmy",
    "nazwa firmy": "Nazwa firmy",
    "nazwa": "Nazwa firmy",
    "company name": "Nazwa firmy",
    "adresse": "Adres",
    "address": "Adres",
    "adres": "Adres",
    "obwód": "Obwód",
    "obwod": "Obwód",
    "oblast": "Obwód",
    "bundesland": "Obwód",
    "województwo": "Obwód",
    "wojewodztwo": "Obwód",
    "telefon": "Telefon",
    "telefonnummer": "Telefon",
    "phone": "Telefon",
    "e-mail": "E-mail",
    "e-mail ": "E-mail",
    "email": "E-mail",
    "mail": "E-mail",
    "webseite": "Strona www",
    "website": "Strona www",
    "www": "Strona www",
    "strona www": "Strona www",
    "url": "URL",
    "link": "URL",
    "adres url": "URL",
    "kategorie_materialow": "Kategoria materiałów",
    "kategorie materialow": "Kategoria materiałów",
    "kategoria materiałów": "Kategoria materiałów",
    "kategoria materialow": "Kategoria materiałów",
    "handelsketten": "Kategoria materiałów",
    "www_geprueft": "WWW sprawdzone",
    "www geprueft": "WWW sprawdzone",
    "www_geprüft": "WWW sprawdzone",
    "www sprawdzone": "WWW sprawdzone",
    "kleinunternehmen": "Mała firma",
    "mała firma": "Mała firma",
    "mala firma": "Mała firma",
    "gu": "Generalny wykonawca",
    "generalny wykonawca": "Generalny wykonawca",
    "gu_marker": "Znacznik GW",
    "gu marker": "Znacznik GW",
    "znacznik gw": "Znacznik GW",
    "status": "Status",
    "status maila": "Status maila",
    "thema": "Temat",
    "temat": "Temat",
    "wert": "Wartość",
    "value": "Wartość",
    "wartość": "Wartość",
    "wartosc": "Wartość",
    "gesendet": "Wysłano",
    "antwort": "Odpowiedź",
    "preis": "Cena",
}

FLAG_COLUMNS = frozenset(
    {
        "WWW sprawdzone",
        "Mała firma",
        "Generalny wykonawca",
        "Odpowiedź",
        "Wymaga interwencji",
        "Odczytane (Twoja reakcja)",
        "Zadzwoń?",
    }
)

_TRUE_VALUES = {
    "ja",
    "yes",
    "true",
    "1",
    "tak",
    "так",
    "tak.",
}
_FALSE_VALUES = {
    "nein",
    "no",
    "false",
    "0",
    "nie",
    "ні",
    "ні.",
}

KONTAKTY_COLUMNS = (
    "Nazwa firmy",
    "Adres",
    "Obwód",
    "Telefon",
    "E-mail",
    "Strona www",
    "URL",
    "Kategoria materiałów",
    "WWW sprawdzone",
    "Mała firma",
    "Generalny wykonawca",
    "Znacznik GW",
    "Status",
    "Status maila",
    "Wysłano",
    "Odpowiedź",
    "Status odpowiedzi",
    "Wymaga interwencji",
    "Odczytane (Twoja reakcja)",
    "Cena",
    "Waluta",
    "Opis",
    "Ceny (wszystkie)",
    "Źródło ceny",
    "Zadzwoń?",
    "Cena rel. 1",
    "Cena rel. 2",
    "Cena rel. 3",
)

OBWODY_COLUMNS = (
    "Nazwa firmy",
    "Obwód",
    "Adres",
    "Strona www",
    "URL",
)

INFO_COLUMNS = ("Temat", "Wartość")

SHEET_PREFERRED_COLUMNS = {
    SHEET_INFO: INFO_COLUMNS,
    SHEET_KONTAKTY: KONTAKTY_COLUMNS,
    SHEET_OBWODY: OBWODY_COLUMNS,
}

SHEET_DEDUPE_KEYS = {
    SHEET_INFO: ("Temat",),
    SHEET_KONTAKTY: ("URL", "E-mail"),
    SHEET_OBWODY: ("URL", "Nazwa firmy"),
}


def _norm_header_key(name: Any) -> str:
    return " ".join(str(name or "").strip().replace("_", " ").split()).casefold()


def canonical_header(name: Any) -> str:
    raw = " ".join(str(name or "").strip().split())
    if not raw:
        return ""
    mapped = HEADER_ALIASES.get(_norm_header_key(raw))
    return mapped or raw


def canonical_sheet_name(name: Any) -> str:
    raw = str(name or "").strip()
    if not raw:
        return SHEET_KONTAKTY
    return SHEET_ALIASES.get(raw.casefold(), raw)


def polish_flag_value(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    low = text.casefold()
    if low in _TRUE_VALUES:
        return "tak"
    if low in _FALSE_VALUES:
        return "nie"
    return text


def normalize_record(rec: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, val in (rec or {}).items():
        header = canonical_header(key)
        if not header or str(header).startswith("_") or header.casefold().startswith("unnamed"):
            continue
        cell = "" if val is None else str(val).strip()
        if header in FLAG_COLUMNS:
            cell = polish_flag_value(cell)
        if header in out and not cell:
            continue
        if cell or header not in out:
            out[header] = cell
    return out


def _row_key(sheet: str, rec: dict[str, str]) -> str:
    keys = SHEET_DEDUPE_KEYS.get(sheet, ())
    for key in keys:
        val = (rec.get(key) or "").strip()
        if val:
            return f"{key}::{val.casefold()}"
    name = (rec.get("Nazwa firmy") or "").strip()
    addr = (rec.get("Adres") or "").strip()
    oblast = (rec.get("Obwód") or "").strip()
    topic = (rec.get("Temat") or "").strip()
    blob = topic or f"{name}|{addr}|{oblast}"
    return blob.casefold() if blob else ""


def _merge_row(old: dict[str, str], new: dict[str, str]) -> dict[str, str]:
    out = dict(old)
    for key, val in new.items():
        if str(val or "").strip():
            out[key] = val
        elif key not in out:
            out[key] = val
    return out


def append_sheet_rows(
    existing: list[dict[str, str]],
    incoming: list[dict[str, str]],
    *,
    sheet: str,
) -> list[dict[str, str]]:
    """Append + unia kolumn. Duplikat (URL/e-mail) uzupełnia puste komórki nowszym wierszem."""
    index: dict[str, int] = {}
    rows: list[dict[str, str]] = []
    for rec in existing:
        norm = normalize_record(rec)
        key = _row_key(sheet, norm)
        if key and key in index:
            rows[index[key]] = _merge_row(rows[index[key]], norm)
            continue
        if key:
            index[key] = len(rows)
        rows.append(norm)
    for rec in incoming:
        norm = normalize_record(rec)
        if not any(str(v).strip() for v in norm.values()):
            continue
        key = _row_key(sheet, norm)
        if key and key in index:
            rows[index[key]] = _merge_row(rows[index[key]], norm)
            continue
        if key:
            index[key] = len(rows)
        rows.append(norm)
    return rows


def ordered_columns(sheet: str, rows: Iterable[dict[str, str]]) -> list[str]:
    preferred = list(SHEET_PREFERRED_COLUMNS.get(sheet, ()))
    seen: set[str] = set()
    out: list[str] = []
    extras: list[str] = []
    present: set[str] = set()
    for rec in rows:
        present.update(k for k in rec.keys() if k)
    for col in preferred:
        if col in present and col not in seen:
            out.append(col)
            seen.add(col)
    for rec in rows:
        for col in rec.keys():
            if col and col not in seen:
                extras.append(col)
                seen.add(col)
    extras.sort(key=lambda c: c.casefold())
    return out + extras


def merge_workbooks(paths: list[Path]) -> dict[str, list[dict[str, str]]]:
    """Kolejność plików = od najstarszego; nowsze dopisują / uzupełniają."""
    import pandas as pd  # pyright: ignore[reportMissingImports]

    merged: dict[str, list[dict[str, str]]] = {
        SHEET_INFO: [],
        SHEET_KONTAKTY: [],
        SHEET_OBWODY: [],
    }
    for path in paths:
        book = pd.read_excel(path, sheet_name=None, dtype=str)
        for raw_name, df in (book or {}).items():
            sheet = canonical_sheet_name(raw_name)
            if sheet not in merged:
                merged[sheet] = []
            frame = df.fillna("")
            records = [normalize_record(rec) for rec in frame.to_dict(orient="records")]
            merged[sheet] = append_sheet_rows(merged[sheet], records, sheet=sheet)
    return merged


def rows_as_dataframe(sheet: str, rows: list[dict[str, str]]):
    import pandas as pd  # pyright: ignore[reportMissingImports]

    cols = ordered_columns(sheet, rows)
    if not cols:
        return pd.DataFrame()
    data = [{c: rec.get(c, "") for c in cols} for rec in rows]
    return pd.DataFrame(data, columns=cols)


def write_merged_workbook(path: Path, sheets: dict[str, list[dict[str, str]]]) -> None:
    import pandas as pd  # pyright: ignore[reportMissingImports]

    path.parent.mkdir(parents=True, exist_ok=True)
    order = [SHEET_INFO, SHEET_KONTAKTY, SHEET_OBWODY]
    extra = [name for name in sheets if name not in order]
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name in order + extra:
            rows = sheets.get(name) or []
            rows_as_dataframe(name, rows).to_excel(writer, index=False, sheet_name=name)


def workbook_sheets(
    info_rows: list[dict],
    kontakty_rows: list[dict],
    obwody_rows: list[dict],
) -> dict[str, list[dict]]:
    return {
        SHEET_INFO: list(info_rows or []),
        SHEET_KONTAKTY: [normalize_record(r) for r in (kontakty_rows or [])],
        SHEET_OBWODY: [normalize_record(r) for r in (obwody_rows or [])],
    }
