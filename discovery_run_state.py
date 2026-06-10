# -*- coding: utf-8 -*-
"""Stan discovery (Serper / cel) — decyzja o sobotnim wznowieniu po piatku."""
from __future__ import annotations

from typing import Any


def record_discovery_run_state(
    cache: dict,
    *,
    all_rows: list,
    total_new_rows: int,
    serper_only: bool,
    rotate_mode: bool,
    campaign_today: str,
    serper_daily_limit: int,
    serper_discovery_reserve: int,
    is_serper_unlimited: bool,
    is_serper_limit_reached_today_fn,
    is_serper_api_exhausted_fn,
    discovery_target_reached_fn,
) -> None:
    if not serper_only:
        return
    used = int((cache.get("serper_daily") or {}).get(campaign_today, 0))
    if is_serper_unlimited:
        exhausted = False
    else:
        exhausted = (
            bool(is_serper_limit_reached_today_fn(cache))
            or bool(is_serper_api_exhausted_fn(cache))
            or used >= max(0, serper_daily_limit - serper_discovery_reserve)
        )
    target = discovery_target_reached_fn(
        all_rows,
        total_new_rows=total_new_rows,
        rotate_mode=rotate_mode,
        serper_only=True,
    )
    cache["discovery_run_state"] = {
        "campaign_date": campaign_today,
        "serper_used": used,
        "serper_exhausted": exhausted,
        "target_reached": target,
        "total_new_rows": int(total_new_rows),
    }


def discovery_should_continue_saturday(cache: dict) -> bool:
    """
    Sobota: kontynuuj discovery tylko gdy piatek nie wyczerpal limitu Serper
    i nie osiagnal min_contacts_target.
    """
    state = cache.get("discovery_run_state") or {}
    if not state:
        return True
    if state.get("serper_exhausted"):
        return False
    if state.get("target_reached"):
        return False
    return True


def discovery_run_state_summary(cache: dict) -> dict[str, Any]:
    state = dict(cache.get("discovery_run_state") or {})
    state["should_continue_saturday"] = discovery_should_continue_saturday(cache)
    return state
