# -*- coding: utf-8 -*-
from __future__ import annotations

from ua_regional_sender_context import (
    build_regional_sender_instructions_uk,
    oblast_primary_city_uk,
    resolve_discovery_oblast,
)
from ua_claude_prompts import build_personalized_inquiry_email_prompt_uk


def test_resolve_discovery_oblast_prefers_discovery_tag():
    info = {"bundesland": "Lvivska", "discovery_bundesland": "Kyiv"}
    assert resolve_discovery_oblast(info) == "Kyiv"


def test_resolve_discovery_oblast_falls_back_to_bundesland():
    assert resolve_discovery_oblast({"bundesland": "Odeska"}) == "Odeska"


def test_oblast_primary_city_kyiv():
    assert oblast_primary_city_uk("Kyiv") == "Київ"


def test_regional_sender_instructions_require_medium_company_and_project():
    block = build_regional_sender_instructions_uk(
        "Lvivska",
        sender_name="Свінчак Максим",
        sender_phone="+380977091141",
    )
    lowered = block.lower()
    assert "середнь" in lowered
    assert "будівельн" in lowered
    assert "об'єкт" in lowered or "обʼєкт" in lowered
    assert "львів" in lowered
    assert "менеджер відділу продажу" in lowered


def test_personalized_prompt_includes_regional_discovery_context():
    p = build_personalized_inquiry_email_prompt_uk(
        company_name="ТОВ Будмаркет Львів",
        oblast="Lvivska",
        discovery_oblast="Lvivska",
        page_snippet="Оптовий склад цементу",
    )
    lowered = p.lower()
    assert "регіон discovery" in lowered
    assert "lvivska" in lowered
    assert "середнь" in lowered
    assert "перевірена база" in lowered or "об'єкт будівництва" in lowered
    assert "адреса" in lowered
    assert "будмаркет" in lowered
    assert "україн" in lowered
