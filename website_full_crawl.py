# -*- coding: utf-8 -*-
"""Pełny crawl witryny (ta sama domena) przed weryfikacją Claude."""
from __future__ import annotations

import os
import re
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from typing import Any, Callable
from urllib.parse import parse_qs, unquote, urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup  # pyright: ignore[reportMissingModuleSource]

from email_targeting import get_registrable_domain

# Bezpieczny limit — małe witryny GU zwykle < 40 podstron
MAX_SITE_CRAWL_PAGES = 80
_SITE_CRAWL_MAX_ENV = (os.environ.get("SITE_CRAWL_MAX_PAGES") or "").strip()
if _SITE_CRAWL_MAX_ENV.isdigit():
    MAX_SITE_CRAWL_PAGES = max(10, int(_SITE_CRAWL_MAX_ENV))

# Twardy limit czasu na jedną domenę — zapobiega 3h na .exe (read-timeout
# requests liczy przerwę między bajtami, nie cały download).
SITE_CRAWL_MAX_SECONDS = 300
_SITE_CRAWL_SEC_ENV = (os.environ.get("SITE_CRAWL_MAX_SECONDS") or "").strip()
if _SITE_CRAWL_SEC_ENV.isdigit():
    SITE_CRAWL_MAX_SECONDS = max(0, int(_SITE_CRAWL_SEC_ENV))

MAX_HTML_BYTES = 1_500_000
HTML_FETCH_WALL_SECONDS = 25.0
_DOWNLOAD_FILE_PATH_RE = re.compile(r"/download/file(?:/|$)", re.I)
_BINARY_MAGIC_PREFIXES = (b"MZ", b"%PDF", b"PK\x03\x04", b"Rar!", b"\x7fELF")

_SKIP_PATH_EXTENSIONS = (
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".zip",
    ".rar",
    ".7z",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".mp4",
    ".mp3",
    ".avi",
    ".css",
    ".js",
    ".xml",
    ".json",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".ico",
    ".exe",
    ".msi",
    ".rtf",
    ".dmg",
    ".iso",
    ".apk",
    ".bin",
    ".cab",
    ".gz",
    ".bz2",
    ".tar",
)

_SKIP_PATH_MARKERS = (
    "/wp-json/",
    "/feed/",
    "/xmlrpc",
    "mailto:",
    "tel:",
    "javascript:",
)

_HTML_CONTENT_TYPE_PREFIXES = (
    "text/html",
    "application/xhtml",
    "text/xml",
    "application/xml",
    "text/plain",
)


@dataclass
class WebsiteCrawlResult:
    pages: dict[str, dict] = field(default_factory=dict)
    urls_visited: list[str] = field(default_factory=list)
    urls_skipped: list[str] = field(default_factory=list)
    capped: bool = False


def website_crawl_result_to_dict(result: WebsiteCrawlResult) -> dict:
    return asdict(result)


def website_crawl_result_from_dict(data: dict) -> WebsiteCrawlResult:
    if not isinstance(data, dict):
        return WebsiteCrawlResult()
    return WebsiteCrawlResult(
        pages=dict(data.get("pages") or {}),
        urls_visited=list(data.get("urls_visited") or []),
        urls_skipped=list(data.get("urls_skipped") or []),
        capped=bool(data.get("capped")),
    )


def _url_parts_for_extension_check(url: str) -> list[str]:
    parsed = urlparse((url or "").strip())
    parts = [unquote(parsed.path or "")]
    try:
        qs = parse_qs(parsed.query or "", keep_blank_values=True)
        for key, vals in qs.items():
            parts.append(unquote(key))
            parts.extend(unquote(v) for v in vals)
    except Exception:
        parts.append(unquote(parsed.query or ""))
    return parts


def is_skippable_asset_url(url: str) -> bool:
    """True = nie pobieraj (binarka, asset, download/file?Name=*.exe)."""
    raw = (url or "").strip()
    if not raw:
        return True
    low = raw.lower()
    for marker in _SKIP_PATH_MARKERS:
        if marker in low:
            return True
    parsed = urlparse(raw)
    path = unquote(parsed.path or "")
    if _DOWNLOAD_FILE_PATH_RE.search(path):
        return True
    for part in _url_parts_for_extension_check(raw):
        part_low = part.lower()
        for ext in _SKIP_PATH_EXTENSIONS:
            if part_low.endswith(ext):
                return True
    return False


def is_probably_html_content_type(content_type: str) -> bool:
    if not (content_type or "").strip():
        return True
    low = content_type.lower().split(";", 1)[0].strip()
    if any(low.startswith(prefix) for prefix in _HTML_CONTENT_TYPE_PREFIXES):
        return True
    if low.startswith(("image/", "audio/", "video/", "font/")):
        return False
    if "javascript" in low or "octet-stream" in low:
        return False
    if low.startswith("application/") and "html" not in low and "xml" not in low:
        return False
    return True


def read_response_html_capped(
    response: Any,
    *,
    max_bytes: int = MAX_HTML_BYTES,
    max_seconds: float = HTML_FETCH_WALL_SECONDS,
) -> str:
    """Zczytaj treść HTML z limitem bajtów i czasu — nie ściągaj .exe."""
    headers = getattr(response, "headers", None) or {}
    try:
        content_type = headers.get("Content-Type") or headers.get("content-type") or ""
    except Exception:
        content_type = ""
    if not is_probably_html_content_type(str(content_type)):
        close = getattr(response, "close", None)
        if callable(close):
            close()
        return ""
    try:
        raw_len = headers.get("Content-Length") or headers.get("content-length")
        if raw_len is not None and int(raw_len) > max_bytes:
            close = getattr(response, "close", None)
            if callable(close):
                close()
            return ""
    except (TypeError, ValueError):
        pass

    content = b""
    already_loaded = getattr(response, "_content", False)
    if already_loaded:
        content = bytes(getattr(response, "content", b"") or b"")[:max_bytes]
    else:
        chunks: list[bytes] = []
        total = 0
        started = time.monotonic()
        try:
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                if time.monotonic() - started > max_seconds:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total >= max_bytes:
                    break
        finally:
            close = getattr(response, "close", None)
            if callable(close):
                close()
        content = b"".join(chunks)[:max_bytes]

    if content.startswith(_BINARY_MAGIC_PREFIXES):
        return ""
    encoding = getattr(response, "encoding", None) or "utf-8"
    try:
        return content.decode(encoding, errors="replace")
    except LookupError:
        return content.decode("utf-8", errors="replace")


def _normalize_crawl_url(
    raw_url: str,
    *,
    site_domain: str,
    normalize_website: Callable[[str], str],
) -> str:
    url = (raw_url or "").strip()
    if not url or url.startswith(("#", "mailto:", "tel:", "javascript:")):
        return ""
    if not url.startswith(("http://", "https://")):
        return ""
    url, _frag = urldefrag(url)
    normalized = normalize_website(url)
    if not normalized:
        return ""
    if is_skippable_asset_url(normalized):
        return ""
    if get_registrable_domain(normalized) != site_domain:
        return ""
    return normalized


def extract_all_internal_links(
    page_url: str,
    html: str,
    *,
    site_domain: str,
    normalize_website: Callable[[str], str],
    extra_urls: list[str] | None = None,
) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    def _add(candidate: str) -> None:
        normalized = _normalize_crawl_url(
            candidate, site_domain=site_domain, normalize_website=normalize_website
        )
        if normalized and normalized not in seen:
            seen.add(normalized)
            out.append(normalized)

    for candidate in extra_urls or []:
        _add(candidate)

    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup.find_all("a", href=True):
        href = (tag.get("href") or "").strip()
        if not href:
            continue
        _add(urljoin(page_url, href))

    return out


def format_crawl_text_for_claude(
    result: WebsiteCrawlResult,
    *,
    purpose: str = "verify",
    per_section_max_chars: int | None = None,
) -> str:
    from claude_page_text import (
        CRAWL_SECTION_MAX_CHARS,
        format_crawl_text_for_claude as _format_for_claude,
    )

    return _format_for_claude(
        result,
        purpose=purpose,
        per_section_max_chars=per_section_max_chars or CRAWL_SECTION_MAX_CHARS,
    )


def crawl_entire_website(
    website: str,
    logger,
    *,
    fetch_page_html: Callable[[str], str],
    parse_html_page: Callable[[str, str], dict],
    normalize_website: Callable[[str], str],
    on_step: Callable[[str], None] | None = None,
    max_pages: int = MAX_SITE_CRAWL_PAGES,
    max_seconds: float | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> WebsiteCrawlResult:
    """
  BFS po całej domenie. Każda strona: fetch HTML → parse → odkryj linki wewnętrzne.
  """
    start = normalize_website(website)
    if not start:
        return WebsiteCrawlResult()

    site_domain = get_registrable_domain(start)
    if not site_domain:
        return WebsiteCrawlResult()

    result = WebsiteCrawlResult()
    queue: deque[str] = deque([start])
    queued: set[str] = {start}
    started = time.monotonic()
    if max_seconds is None:
        max_seconds = float(SITE_CRAWL_MAX_SECONDS) if SITE_CRAWL_MAX_SECONDS > 0 else None
    elif max_seconds <= 0:
        max_seconds = None

    while queue and len(result.urls_visited) < max_pages:
        if should_stop and should_stop():
            result.capped = True
            logger.info("Website-Crawl: limit czasu scrapera — stop %s", start)
            break
        if max_seconds is not None and (time.monotonic() - started) >= max_seconds:
            result.capped = True
            logger.info(
                "Website-Crawl: limit %ss na domenę (%s)",
                int(max_seconds),
                start,
            )
            break

        url = queue.popleft()
        if url in result.pages:
            continue
        if is_skippable_asset_url(url):
            result.urls_skipped.append(url)
            continue

        if on_step:
            on_step(
                f"Website-Crawl {len(result.urls_visited) + 1}/{max_pages}: {url}"
            )

        html = fetch_page_html(url)
        if not html:
            result.urls_skipped.append(url)
            continue

        try:
            parsed = parse_html_page(url, html)
        except Exception as exc:
            logger.info("Website-Crawl parse fehlgeschlagen %s: %s", url, exc)
            result.urls_skipped.append(url)
            continue

        if not isinstance(parsed, dict):
            parsed = {}

        result.pages[url] = parsed
        result.urls_visited.append(url)

        for link in extract_all_internal_links(
            url,
            html,
            site_domain=site_domain,
            normalize_website=normalize_website,
            extra_urls=list(parsed.get("contact_urls") or []),
        ):
            if link not in queued and link not in result.pages:
                queued.add(link)
                queue.append(link)

    if queue:
        if not result.capped:
            logger.info(
                "Website-Crawl: Limit %s Seiten erreicht (%s übrig in Queue)",
                max_pages,
                len(queue),
            )
        result.capped = True

    return result
