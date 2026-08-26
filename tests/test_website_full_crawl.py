# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json

from website_full_crawl import (
    WebsiteCrawlResult,
    crawl_entire_website,
    extract_all_internal_links,
    format_crawl_text_for_claude,
    is_probably_html_content_type,
    is_skippable_asset_url,
    read_response_html_capped,
    website_crawl_result_from_dict,
    website_crawl_result_to_dict,
)


def _norm(url: str) -> str:
    u = url.strip()
    if not u.startswith("http"):
        u = "https://" + u
    return u.rstrip("/") if u.endswith("/") and u.count("/") > 2 else u


class WebsiteFullCrawlTest(unittest.TestCase):
    def test_extract_internal_links_same_domain(self):
        html = '<a href="/karriere/stelle">Jobs</a><a href="https://other.com/x">X</a>'
        links = extract_all_internal_links(
            "https://wijcobau.de/",
            html,
            site_domain="wijcobau.de",
            normalize_website=_norm,
        )
        self.assertTrue(any("karriere" in u for u in links))
        self.assertFalse(any("other.com" in u for u in links))

    def test_crawl_visits_all_internal_pages(self):
        pages = {
            "https://example.de": (
                '<a href="https://example.de/ueber-uns">About</a>'
                "<p>Generalunternehmer Einzelhandel</p>"
            ),
            "https://example.de/ueber-uns": (
                '<a href="https://example.de/karriere">Karriere</a>'
                "<p>Auftraggeber Netto</p>"
            ),
            "https://example.de/karriere": "<p>Retail Projekte</p>",
        }

        def fetch(url: str) -> str:
            key = url.rstrip("/")
            return pages.get(key, pages.get(key + "/", ""))

        def parse(url: str, html: str) -> dict:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")
            return {
                "emails": [],
                "phones": [],
                "company_name": "",
                "contact_urls": [],
                "page_text": soup.get_text(" ", strip=True),
            }

        result = crawl_entire_website(
            "https://example.de",
            logger=MagicMock(),
            fetch_page_html=fetch,
            parse_html_page=parse,
            normalize_website=_norm,
            max_pages=10,
        )
        self.assertEqual(len(result.urls_visited), 3)
        text = format_crawl_text_for_claude(result)
        self.assertIn("=== https://example.de/karriere", text)
        self.assertIn("Netto", text)

    def test_crawl_result_json_roundtrip(self):
        original = WebsiteCrawlResult(
            pages={"https://firma.de/impressum": {"emails": ["info@firma.de"]}},
            urls_visited=["https://firma.de/impressum"],
            urls_skipped=["https://firma.de/feed"],
            capped=True,
        )
        payload = {"website_crawl": {"https://firma.de": website_crawl_result_to_dict(original)}}
        raw = json.dumps(payload)
        loaded = json.loads(raw)
        restored = website_crawl_result_from_dict(loaded["website_crawl"]["https://firma.de"])
        self.assertEqual(restored.urls_visited, original.urls_visited)
        self.assertEqual(restored.pages, original.pages)
        self.assertTrue(restored.capped)


class SkipBinaryAndBudgetTest(unittest.TestCase):
    def test_skips_exe_in_query_string(self):
        url = (
            "https://www.inproekt.kiev.ua/IVK/Download/File"
            "?Name=ivk_update_1_920_3218.exe"
        )
        self.assertTrue(is_skippable_asset_url(url))

    def test_skips_download_file_path(self):
        self.assertTrue(
            is_skippable_asset_url(
                "https://www.inproekt.kiev.ua/IVK/Download/File?Name=list7.pdf"
            )
        )

    def test_skips_rtf_in_query(self):
        self.assertTrue(
            is_skippable_asset_url(
                "https://www.inproekt.kiev.ua/IVK/Download/File?Name=ivk920_3218.rtf"
            )
        )

    def test_allows_html_pages(self):
        self.assertFalse(is_skippable_asset_url("https://www.inproekt.kiev.ua/IVK"))
        self.assertFalse(is_skippable_asset_url("https://bud24.com.ua/kontakty"))

    def test_extract_does_not_queue_exe_links(self):
        html = (
            '<a href="/about">About</a>'
            '<a href="/IVK/Download/File?Name=ivk_setup_1_920.exe">Setup</a>'
        )
        links = extract_all_internal_links(
            "https://www.inproekt.kiev.ua/",
            html,
            site_domain="inproekt.kiev.ua",
            normalize_website=_norm,
        )
        self.assertTrue(any("/about" in u.lower() for u in links))
        self.assertFalse(any(".exe" in u.lower() for u in links))

    def test_content_type_rejects_binaries(self):
        self.assertFalse(is_probably_html_content_type("application/octet-stream"))
        self.assertFalse(is_probably_html_content_type("application/x-msdownload"))
        self.assertFalse(is_probably_html_content_type("application/pdf"))
        self.assertTrue(is_probably_html_content_type("text/html; charset=utf-8"))
        self.assertTrue(is_probably_html_content_type(""))

    def test_read_capped_skips_exe_magic(self):
        class _Resp:
            headers = {"Content-Type": "application/octet-stream"}
            _content = True
            content = b"MZ" + b"\x00" * 100
            encoding = "utf-8"

            def close(self):
                return None

        self.assertEqual(read_response_html_capped(_Resp()), "")

    def test_read_capped_accepts_html(self):
        class _Resp:
            headers = {"Content-Type": "text/html; charset=utf-8"}
            _content = True
            content = b"<html><body>Kontakt</body></html>"
            encoding = "utf-8"

            def close(self):
                return None

        self.assertIn("Kontakt", read_response_html_capped(_Resp()))

    def test_crawl_stops_on_should_stop(self):
        fetched: list[str] = []

        def fetch(url: str) -> str:
            fetched.append(url)
            return "<p>ok</p><a href='/kolejna'>x</a>"

        def parse(_url: str, html: str) -> dict:
            return {"page_text": html, "contact_urls": []}

        calls = {"n": 0}

        def should_stop() -> bool:
            calls["n"] += 1
            return calls["n"] > 1

        result = crawl_entire_website(
            "https://example.de",
            logger=MagicMock(),
            fetch_page_html=fetch,
            parse_html_page=parse,
            normalize_website=_norm,
            max_pages=10,
            max_seconds=0,
            should_stop=should_stop,
        )
        self.assertTrue(result.capped)
        self.assertLessEqual(len(fetched), 1)

    def test_crawl_does_not_fetch_exe_links(self):
        fetched: list[str] = []
        pages = {
            "https://www.inproekt.kiev.ua": (
                '<a href="/IVK">IVK</a>'
                '<a href="/IVK/Download/File?Name=ivk_setup_1_920.exe">exe</a>'
            ),
            "https://www.inproekt.kiev.ua/IVK": "<p>Software</p>",
        }

        def fetch(url: str) -> str:
            fetched.append(url)
            if ".exe" in url.lower() or "/Download/File" in url:
                raise AssertionError(f"should not fetch binary {url}")
            key = url.rstrip("/")
            return pages.get(key, pages.get(key + "/", ""))

        def parse(_url: str, html: str) -> dict:
            return {"page_text": html, "contact_urls": []}

        result = crawl_entire_website(
            "https://www.inproekt.kiev.ua",
            logger=MagicMock(),
            fetch_page_html=fetch,
            parse_html_page=parse,
            normalize_website=_norm,
            max_pages=10,
            max_seconds=0,
        )
        self.assertGreaterEqual(len(result.urls_visited), 1)
        self.assertFalse(any(".exe" in u.lower() for u in fetched))


if __name__ == "__main__":
    unittest.main(verbosity=2)
