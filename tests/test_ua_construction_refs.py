# -*- coding: utf-8 -*-
from __future__ import annotations

from ua_regional_construction_refs import (
    address_present_in_body,
    inject_construction_project_context,
    pick_construction_project,
)


def test_pick_project_for_lvivska_has_real_address():
    project = pick_construction_project("Lvivska", seed="supplier-a")
    assert project.address_uk.startswith("м. Львів")
    assert "вул." in project.address_uk


def test_address_present_detects_full_address():
    project = pick_construction_project("Kyiv", seed="x")
    body = f"Будуємо об'єкт за адресою {project.address_uk}."
    assert address_present_in_body(body, project.address_uk)


def test_inject_adds_verified_address_when_missing():
    project = pick_construction_project("Odeska", seed="supplier-b")
    body = "Шановні пані та панове,\n\nПрохання про прайс.\n\nЗ повагою,\nТест"
    out = inject_construction_project_context(body, project)
    assert address_present_in_body(out, project.address_uk)
    assert project.name_uk in out


def test_extract_city_from_address():
    from ua_regional_construction_refs import extract_city_from_address_uk

    assert extract_city_from_address_uk("м. Старокостянтинів, вул. Соборна, 12") == "Старокостянтинів"
    assert extract_city_from_address_uk("м. Київ, вул. Хрещатик, 1") == "Київ"


def test_pick_project_prefers_supplier_city_in_oblast():
    project = pick_construction_project(
        "Khmelnytska",
        seed="demo",
        prefer_city="Старокостянтинів",
    )
    assert "Старокостянтинів" in project.address_uk


def test_pick_project_for_kyiv_supplier_uses_kyiv_address():
    project = pick_construction_project(
        "Kyiv",
        seed="demo",
        prefer_city="Київ",
    )
    assert project.address_uk.startswith("м. Київ")
