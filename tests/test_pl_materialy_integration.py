# -*- coding: utf-8 -*-
"""
Testy integracyjne kampanii PL — smoke, run_config, prompty Claude, workflowy.

  python -m pytest tests/test_pl_materialy_integration.py -v
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import pytest

import pl_materialy_scraper as scraper
from pl_claude_prompts import build_page_verify_prompt, build_personalized_inquiry_email_prompt_pl
from pl_wojewodztwo_keywords import configure_campaign_wojewodztwa
from pl_wojewodztwo_rotation import apply_rotation_to_module

ROOT = Path(__file__).resolve().parent.parent
_LOGGER = logging.getLogger("test_pl_materialy_integration")

PL_WORKFLOWS = (
    "pl_materialy_pi.yml",
    "pl_materialy_thu.yml",
    "pl_materialy_mon.yml",
    "pl_materialy_tue.yml",
    "pl_materialy_fri.yml",
    "sync-google-drive-pl.yml",
)

EXPECTED_PL_CRONS = {
    "pl_materialy_pi.yml": {
        "0 22 * * 1",
        "0 20 * * 2",
        "0 0 * * 4",
        "0 1 * * 5",
        "0 21 * * 5",
    },
    "pl_materialy_thu.yml": {"30 10 * * 0"},
    "sync-google-drive-pl.yml": {"0 11 * * 1"},
    "pl_materialy_mon.yml": {"0 12 * * 1"},
    "pl_materialy_tue.yml": {"0 14 * * 1"},
    "pl_materialy_fri.yml": {"0 14 * * 2"},
}


def test_scraper_smoke_test_entrypoint():
    scraper._run_smoke_tests()


def test_run_config_mazowieckie_test_loads():
    from scraper_run_config import load_run_config_file

    data = load_run_config_file("run_config/pl_mazowieckie_test.json", ROOT)
    assert "mazowieckie" in data.get("active_bundeslaender", [])


def test_apply_rotation_configures_module(tmp_path):
    mod = type("M", (), {})()
    woj, state, path = apply_rotation_to_module(mod, tmp_path, max_discovery_terms=40)
    assert woj in scraper.CAMPAIGN_ACTIVE_BUNDESLAENDER
    assert len(mod.SERPER_DISCOVERY_TERMS) <= 40
    assert path.parent == tmp_path


def test_configure_wojewodztwa_sets_discovery_waves():
    mod = type("M", (), {})()
    configure_campaign_wojewodztwa(mod, ["mazowieckie"], max_discovery_terms=50)
    assert mod.SERPER_DISCOVERY_TERMS
    assert mod.SERPER_DISCOVERY_FALLBACK_TERMS
    assert mod.SERPER_DISCOVERY_BROAD_TERMS
    assert mod.SERPER_DISCOVERY_LANDKREIS_TERMS
    assert mod.SERPER_DISCOVERY_PLACES_TERMS
    assert mod.SERPER_DISCOVERY_REGION_SUFFIX == "Polska"


def test_page_verify_prompt_polish_context():
    p = build_page_verify_prompt(
        "Hurtownia Budowlana",
        "https://budmat.pl",
        "Hurtownia materiałów budowlanych cement piasek Warszawa",
    )
    assert "is_gu" in p
    assert "Polsce" in p or "polsk" in p.lower()
    assert "budowlane" in p.lower() or "materiał" in p.lower()


def test_row_cleanup_prompt_polish():
    from pl_claude_prompts import build_row_cleanup_prompt

    p = build_row_cleanup_prompt(
        company="Hurtownia Test sp. z o.o.",
        address="ul. Test 1, 00-001 Warszawa",
        phone="+48 22 123 45 67",
        email="kontakt@test.pl",
        website="https://test.pl",
        states="mazowieckie, malopolskie",
    )
    assert "+48" in p
    assert "województwo" in p.lower() or "bundesland" in p.lower()
    assert "+380" not in p


def test_run_config_pl_materialy_cache_and_claude_flags():
    from scraper_run_config import load_run_config_file

    data = load_run_config_file("run_config/pl_materialy.json", ROOT)
    assert data.get("enable_claude_row_cleanup") is True
    assert data.get("enable_claude_contact_extract") is True
    assert data.get("claude_discovery_cache_days") == 7
    assert data.get("geo_filter_enabled") is False


def test_pl_module_uses_pl_contact_extract_not_de():
    import inspect

    source = inspect.getsource(scraper.enrich_row_with_contacts)
    assert "pl_claude_contact_extract" in source
    assert "from claude_contact_extract import" not in source


def test_reconcile_prefers_website_phone_when_found():
    row = {"telefon": "+48 11 111 11 11", "www": "https://hurt.pl"}
    collected = {"website": "https://hurt.pl", "phones": ["+48 22 222 22 22"]}
    out = scraper.reconcile_contact_sources(row, collected)
    assert "222" in out["telefon"].replace(" ", "")


def test_claude_inquiry_prompt_polish_and_phone():
    p = build_personalized_inquiry_email_prompt_pl(
        company_name="Hurtownia Test",
        wojewodztwo="mazowieckie",
    )
    assert "polsk" in p.lower()
    assert "516513965" in p
    assert "JSON" in p


@pytest.mark.parametrize("workflow_file", PL_WORKFLOWS)
def test_pl_workflow_yaml_valid(workflow_file: str):
    path = ROOT / ".github" / "workflows" / workflow_file
    assert path.is_file(), f"brak {workflow_file}"
    text = path.read_text(encoding="utf-8")
    assert "jobs:" in text
    assert "runs-on:" in text
    assert "PL" in text or "Drive PL" in text


@pytest.mark.parametrize("workflow_file", PL_WORKFLOWS)
def test_pl_workflow_cron_schedule(workflow_file: str):
    path = ROOT / ".github" / "workflows" / workflow_file
    text = path.read_text(encoding="utf-8")
    crons = set(re.findall(r'cron:\s*"([^"]+)"', text))
    if workflow_file not in EXPECTED_PL_CRONS:
        return
    assert crons == EXPECTED_PL_CRONS[workflow_file]


def test_pl_discovery_workflow_uses_pl_scraper():
    text = (ROOT / ".github" / "workflows" / "pl_materialy_pi.yml").read_text(encoding="utf-8")
    assert "pl_materialy_scraper.py" in text
    assert "run_config/pl_materialy.json" in text
    assert "--rotate-wojewodztwo" in text
    assert "pl-pipeline" in text


def test_sync_drive_pl_uses_pl_campaign():
    text = (ROOT / ".github" / "workflows" / "sync-google-drive-pl.yml").read_text(encoding="utf-8")
    assert "GDRIVE_FOLDER_ID_PL" in text
    assert "--campaign pl" in text
