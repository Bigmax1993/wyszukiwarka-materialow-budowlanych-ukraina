# -*- coding: utf-8 -*-
"""
Rotacja województw PL — jedno województwo na cykl discovery.

Stan: Wyniki/pl_materialy_wojewodztwo_rotation.json
"""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any

from pl_wojewodztwo_keywords import WOJEWODZTWO_CONFIG, configure_campaign_wojewodztwa

DEFAULT_ROTATION_START = date(2026, 7, 14)

WOJEWODZTWO_ROTATION_ORDER: tuple[str, ...] = (
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
)
BUNDESLAND_ROTATION_ORDER = WOJEWODZTWO_ROTATION_ORDER

STATE_FILENAME = "pl_materialy_wojewodztwo_rotation.json"
DEFAULT_MIN_CONTACTS_SINGLE_WOJEWODZTWO = 20


def get_rotation_start_date() -> date:
    raw = (os.environ.get("PL_WOJEWODZTWO_ROTATION_START") or "").strip()
    if not raw:
        return DEFAULT_ROTATION_START
    return date.fromisoformat(raw)


def rotation_is_active(as_of: date | None = None) -> bool:
    return (as_of or date.today()) >= get_rotation_start_date()


def rotation_state_path(wyniki_dir: Path) -> Path:
    return wyniki_dir / STATE_FILENAME


def _empty_state() -> dict[str, Any]:
    return {"version": 1, "next_index": 0, "history": []}


def load_rotation_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _empty_state()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return _empty_state()
        data.setdefault("version", 1)
        data.setdefault("next_index", 0)
        data.setdefault("history", [])
        return data
    except (OSError, json.JSONDecodeError):
        return _empty_state()


def save_rotation_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def peek_next_wojewodztwo(state: dict[str, Any] | None = None) -> str:
    st = state if state is not None else _empty_state()
    idx = int(st.get("next_index", 0)) % len(WOJEWODZTWO_ROTATION_ORDER)
    return WOJEWODZTWO_ROTATION_ORDER[idx]


peek_next_bundesland = peek_next_wojewodztwo
peek_next_oblast = peek_next_wojewodztwo


def apply_rotation_to_module(
    module,
    wyniki_dir: Path,
    *,
    min_contacts: int = DEFAULT_MIN_CONTACTS_SINGLE_WOJEWODZTWO,
    max_discovery_terms: int = 120,
) -> tuple[str, dict[str, Any], Path]:
    state_path = rotation_state_path(wyniki_dir)
    state = load_rotation_state(state_path)
    woj = peek_next_wojewodztwo(state)
    configure_campaign_wojewodztwa(module, [woj], max_discovery_terms=max_discovery_terms)
    if hasattr(module, "MIN_CONTACTS_TARGET"):
        module.MIN_CONTACTS_TARGET = min_contacts
    return woj, state, state_path


def commit_rotation_after_run(
    state_path: Path,
    state: dict[str, Any],
    wojewodztwo: str,
    *,
    run_date: date | None = None,
) -> str:
    idx = int(state.get("next_index", 0)) % len(WOJEWODZTWO_ROTATION_ORDER)
    if WOJEWODZTWO_ROTATION_ORDER[idx] != wojewodztwo:
        wojewodztwo = WOJEWODZTWO_ROTATION_ORDER[idx]
    history = list(state.get("history") or [])
    history.append(
        {
            "wojewodztwo": wojewodztwo,
            "index": idx,
            "at": (run_date or date.today()).isoformat(),
        }
    )
    state["history"] = history[-32:]
    state["next_index"] = (idx + 1) % len(WOJEWODZTWO_ROTATION_ORDER)
    save_rotation_state(state_path, state)
    return peek_next_wojewodztwo(state)


def format_rotation_status(wyniki_dir: Path) -> str:
    state_path = rotation_state_path(wyniki_dir)
    state = load_rotation_state(state_path)
    start = get_rotation_start_date()
    if not rotation_is_active():
        return (
            f"Rotacja województw od {start.isoformat()} — "
            f"teraz tryb cała Polska (bez rotacji). "
            f"Następne po starcie: {WOJEWODZTWO_ROTATION_ORDER[0]}"
        )
    current = peek_next_wojewodztwo(state)
    nxt_idx = int(state.get("next_index", 0))
    nxt = WOJEWODZTWO_ROTATION_ORDER[(nxt_idx + 1) % len(WOJEWODZTWO_ROTATION_ORDER)]
    return (
        f"Bieżące województwo (ten tydzień): {current} | "
        f"następne po zakończeniu: {nxt} | "
        f"indeks={nxt_idx}/{len(WOJEWODZTWO_ROTATION_ORDER)}"
    )
