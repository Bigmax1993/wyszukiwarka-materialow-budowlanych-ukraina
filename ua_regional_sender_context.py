# -*- coding: utf-8 -*-
"""Kontekst nadawcy maili UA — firma budowlana średniego rozmiaru per obwód discovery."""
from __future__ import annotations

from ua_oblast_keywords import OBLAST_CONFIG, _normalize_oblast_key


def resolve_discovery_oblast(contact_info: dict | None, *, fallback: str = "") -> str:
    """Obwód z discovery (discovery_bundesland) lub z wiersza kontaktu."""
    info = contact_info or {}
    for key in ("discovery_bundesland", "bundesland", "oblast"):
        raw = str(info.get(key) or "").strip()
        if not raw:
            continue
        normalized = _normalize_oblast_key(raw)
        if normalized in OBLAST_CONFIG:
            return normalized
    fb = _normalize_oblast_key(fallback)
    return fb if fb in OBLAST_CONFIG else (fallback or "").strip()


def oblast_primary_city_uk(oblast_key: str) -> str:
    key = _normalize_oblast_key(oblast_key)
    cfg = OBLAST_CONFIG.get(key) or {}
    cities = cfg.get("cities") or ()
    return str(cities[0]) if cities else key


def oblast_cities_uk(oblast_key: str, *, limit: int = 5) -> tuple[str, ...]:
    key = _normalize_oblast_key(oblast_key)
    cfg = OBLAST_CONFIG.get(key) or {}
    cities = tuple(str(c) for c in (cfg.get("cities") or ()))
    return cities[:limit] if limit > 0 else cities


def oblast_region_label_uk(oblast_key: str) -> str:
    """Etykieta regionu po ukraińsku do promptu Claude."""
    key = _normalize_oblast_key(oblast_key)
    if key == "Kyiv":
        return "м. Київ"
    city = oblast_primary_city_uk(key)
    if key in OBLAST_CONFIG:
        return f"{city} ({key})"
    return oblast_key or "Україна"


def build_regional_sender_instructions_uk(
    oblast_key: str,
    *,
    sender_name: str,
    sender_phone: str,
    construction_project_block: str = "",
) -> str:
    """
    Instrukcje dla Claude: wybór realnej średniej firmy budowlanej z regionu
    i wzmianka o aktualnej dużej budowie w tym regionie.
    """
    key = _normalize_oblast_key(oblast_key)
    region = oblast_region_label_uk(key) if key in OBLAST_CONFIG else (oblast_key or "Україна")
    cities = ", ".join(oblast_cities_uk(key, limit=6)) or region
    name = (sender_name or "Свінчак Максим").strip()
    phone = (sender_phone or "+380977091141").strip()
    project_section = (
        f"\n\n{construction_project_block.strip()}\n"
        if (construction_project_block or "").strip()
        else ""
    )

    return f"""РЕГІОН DISCOVERY (обов'язковий контекст)
Область / регіон: {region}
Ключ oblast: {key or "(невідомо)"}
Основні міста регіону: {cities}

ВІДПРАВНИК — СЕРЕДНЯ РЕГІОНАЛЬНА БУДІВЕЛЬНА КОМПАНІЯ
• Обери РЕАЛЬНУ існуючу українську будівельну компанію СЕРЕДНЬОГО розміру, яка діє в цьому регіоні discovery.
  Середній розмір = регіональний забудовник / підрядник (ТОВ, ПП), НЕ найбільший національний холдинг
  (не Київміськбуд, UDP, Arkada, Будімпекс тощо) і не ФОП / «гаражна» фірма.
• Представ себе як {name} — менеджер відділу продажу обраної компанії.
• У листі чітко назви цю компанію та її роль (будівництво житла, комерційних чи промислових об'єктів у регіоні).
{project_section}
ПІДПИС (додай у body наприкінці):
З повагою,
{name}
Менеджер відділу продажу
[повна назва обраної компанії]
[сайт компанії, якщо відомий]
Tel.: {phone}"""
