# -*- coding: utf-8 -*-
"""
Rotacja Bundesländer — jeden land na cykl discovery (np. piątek).

Stan: Wyniki/de_gu_bundeslaender_rotation.json
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from de_gu_keywords import BUNDESLAND_CONFIG, configure_campaign_bundeslaender

# Kolejność fal (duże rynki → mniejsze landy)
BUNDESLAND_ROTATION_ORDER: tuple[str, ...] = tuple(BUNDESLAND_CONFIG.keys())

STATE_FILENAME = "de_gu_bundeslaender_rotation.json"
DEFAULT_MIN_CONTACTS_SINGLE_LAND = 20


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


def peek_next_bundesland(state: dict[str, Any] | None = None) -> str:
    st = state if state is not None else _empty_state()
    idx = int(st.get("next_index", 0)) % len(BUNDESLAND_ROTATION_ORDER)
    return BUNDESLAND_ROTATION_ORDER[idx]


def apply_rotation_to_module(
    module,
    wyniki_dir: Path,
    *,
    min_contacts: int = DEFAULT_MIN_CONTACTS_SINGLE_LAND,
    max_discovery_terms: int = 120,
) -> tuple[str, dict[str, Any], Path]:
    """Wybiera bieżący land (bez przesunięcia indeksu) i konfiguruje scraper."""
    state_path = rotation_state_path(wyniki_dir)
    state = load_rotation_state(state_path)
    land = peek_next_bundesland(state)
    configure_campaign_bundeslaender(
        module, [land], max_discovery_terms=max_discovery_terms
    )
    if hasattr(module, "MIN_CONTACTS_TARGET"):
        module.MIN_CONTACTS_TARGET = min_contacts
    return land, state, state_path


def commit_rotation_after_run(
    state_path: Path,
    state: dict[str, Any],
    land: str,
    *,
    run_date: date | None = None,
) -> str:
    """Po udanym discovery przesuwa rotację na następny land (≥20 retail_verified)."""
    idx = int(state.get("next_index", 0)) % len(BUNDESLAND_ROTATION_ORDER)
    if BUNDESLAND_ROTATION_ORDER[idx] != land:
        land = BUNDESLAND_ROTATION_ORDER[idx]
    history = list(state.get("history") or [])
    history.append(
        {
            "land": land,
            "index": idx,
            "at": (run_date or date.today()).isoformat(),
        }
    )
    state["history"] = history[-32:]
    state["next_index"] = (idx + 1) % len(BUNDESLAND_ROTATION_ORDER)
    save_rotation_state(state_path, state)
    return peek_next_bundesland(state)


def format_rotation_status(wyniki_dir: Path) -> str:
    state_path = rotation_state_path(wyniki_dir)
    state = load_rotation_state(state_path)
    current = peek_next_bundesland(state)
    nxt_idx = int(state.get("next_index", 0))
    nxt = BUNDESLAND_ROTATION_ORDER[(nxt_idx + 1) % len(BUNDESLAND_ROTATION_ORDER)]
    return (
        f"Bieżący land (ten tydzień): {current} | "
        f"następny po zakończeniu: {nxt} | "
        f"indeks={nxt_idx}/{len(BUNDESLAND_ROTATION_ORDER)}"
    )
