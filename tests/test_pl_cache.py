# -*- coding: utf-8 -*-
"""Testy cache JSON kampanii PL — wersjonowanie, TTL, purge."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pl_materialy_scraper as scraper


def test_empty_cache_has_meta_version():
    cache = scraper._empty_cache()
    assert cache["cache_meta"]["pl_enrichment_version"] == scraper.PL_CACHE_ENRICHMENT_VERSION


def test_purge_on_version_mismatch_clears_buckets():
    cache = scraper._empty_cache()
    cache["cache_meta"]["pl_enrichment_version"] = "stara_wersja"
    cache["serper_discovery"] = {"search:x": {"rows": [], "at": datetime.now().isoformat()}}
    cache["claude_row_enrichment"] = {"https://x.pl": {"company_name_clean": "X"}}
    cache["website_crawl"] = {"https://x.pl": {"pages": {}}}
    cache["claude_contact_extract"] = {"k": {"emails": []}}
    removed = scraper._purge_stale_pl_cache_buckets(cache, logging.getLogger("test"))
    assert removed >= 4
    assert cache["serper_discovery"] == {}
    assert cache["claude_row_enrichment"] == {}
    assert cache["website_crawl"] == {}
    assert cache["claude_contact_extract"] == {}
    assert cache["cache_meta"]["pl_enrichment_version"] == scraper.PL_CACHE_ENRICHMENT_VERSION


def test_serper_discovery_fresh_entry_roundtrip():
    cache = scraper._empty_cache()
    rows = [{"url": "https://hurt.pl", "adres": "ul. Test 1, 00-001 Warszawa"}]
    scraper.store_serper_discovery_rows(cache, "hurtownia warszawa", rows)
    cached = scraper.get_cached_serper_discovery_rows(cache, "hurtownia warszawa")
    assert cached is not None
    assert len(cached) == 1
    assert cached[0]["adres"].startswith("ul.")


def test_serper_discovery_expired_entry_is_miss():
    cache = scraper._empty_cache()
    cache["serper_discovery"]["search:test"] = {
        "rows": [{"url": "https://x.pl"}],
        "at": (datetime.now() - timedelta(days=30)).isoformat(),
        "version": scraper.PL_CACHE_ENRICHMENT_VERSION,
    }
    assert scraper.get_cached_serper_discovery_rows(cache, "test") is None


def test_legacy_row_enrichment_rejected():
    cache = scraper._empty_cache()
    cache["claude_row_enrichment"]["https://legacy.pl"] = {
        "company_name_clean": "Legacy",
        "address": "stary snippet produktu",
        "phone": "",
    }
    assert scraper._get_row_enrichment_cache_entry(cache, "https://legacy.pl") is None


def test_row_from_cache_contact_reads_address_and_phone():
    info = {
        "company_name_clean": "Hurtownia",
        "official_website": "https://hurt.pl",
        "full_address": "ul. Główna 2, 30-001 Kraków",
        "adres": "ul. Główna 2, 30-001 Kraków",
        "telefon": "+48 12 345 67 89",
        "bundesland": "malopolskie",
        "discovery_bundesland": "malopolskie",
        "verification_reason": scraper.PENDING_WWW_VERIFY_REASON,
        "retail_verified": False,
    }
    row = scraper.row_from_cache_contact("https://hurt.pl", info)
    assert row is not None
    assert row["adres"] == "ul. Główna 2, 30-001 Kraków"
    assert "48" in row["telefon"].replace(" ", "")
    assert row["bundesland"] == "malopolskie"
    assert row["discovery_bundesland"] == "malopolskie"


def test_pipeline_row_to_contact_info_includes_address_fields():
    row = {
        "url": "https://hurt.pl",
        "nazwa": "Hurtownia",
        "company_name_clean": "Hurtownia",
        "adres": "ul. Test 5, 00-001 Warszawa",
        "telefon": "+48 22 123 45 67",
        "bundesland": "mazowieckie",
        "discovery_bundesland": "mazowieckie",
        "email_target": "kontakt@hurt.pl",
        "retail_verified": True,
    }
    info = scraper.pipeline_row_to_contact_info(row)
    assert info["full_address"] == "ul. Test 5, 00-001 Warszawa"
    assert info["adres"] == "ul. Test 5, 00-001 Warszawa"
    assert info["telefon"] == "+48 22 123 45 67"
    assert info["bundesland"] == "mazowieckie"
    assert info["discovery_bundesland"] == "mazowieckie"


def test_sync_pipeline_rows_to_contacts_cache():
    cache = scraper._empty_cache()
    rows = [
        {
            "url": "https://sync.pl",
            "nazwa": "Sync Sp. z o.o.",
            "adres": "ul. Sync 1, 90-001 Łódź",
            "telefon": "+48 42 111 22 33",
            "bundesland": "lodzkie",
            "discovery_bundesland": "lodzkie",
            "email_target": "sync@sync.pl",
            "retail_verified": True,
        }
    ]
    n = scraper.sync_pipeline_rows_to_contacts_cache(rows, cache)
    assert n == 1
    info = cache["contacts"]["https://sync.pl"]
    assert info["adres"] == "ul. Sync 1, 90-001 Łódź"
    assert info["telefon"] == "+48 42 111 22 33"
    assert info["bundesland"] == "lodzkie"
