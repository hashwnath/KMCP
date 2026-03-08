"""Parse sitemap.xml (and nested sitemap index files) to extract page URLs."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import httpx

from src.common.config import get_config

logger = logging.getLogger(__name__)

_SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
_HTML_EXTENSIONS = {"", ".html", ".htm", ".php", ".asp", ".aspx", ".jsp"}


def _is_html_url(url: str) -> bool:
    """Return True if the URL likely points to an HTML page."""
    path = urlparse(url).path.lower()
    ext = path.rsplit(".", 1)[-1] if "." in path.rsplit("/", 1)[-1] else ""
    if ext:
        return f".{ext}" in _HTML_EXTENSIONS
    return True  # no extension → assume HTML


async def _fetch_xml(client: httpx.AsyncClient, url: str) -> ET.Element | None:
    """Fetch and parse an XML document, returning the root element."""
    try:
        resp = await client.get(url, follow_redirects=True, timeout=30.0)
        resp.raise_for_status()
        return ET.fromstring(resp.text)
    except (httpx.HTTPError, ET.ParseError) as exc:
        logger.warning("Failed to fetch/parse sitemap %s: %s", url, exc)
        return None


async def _parse_sitemap_recursive(
    client: httpx.AsyncClient, url: str, visited: set[str]
) -> list[str]:
    """Recursively parse sitemap or sitemap index, returning page URLs."""
    if url in visited:
        return []
    visited.add(url)

    root = await _fetch_xml(client, url)
    if root is None:
        return []

    urls: list[str] = []

    # Sitemap index: contains <sitemap><loc> entries
    for sitemap_elem in root.findall("sm:sitemap/sm:loc", _SITEMAP_NS):
        child_url = (sitemap_elem.text or "").strip()
        if child_url:
            urls.extend(await _parse_sitemap_recursive(client, child_url, visited))

    # Regular sitemap: contains <url><loc> entries
    for url_elem in root.findall("sm:url/sm:loc", _SITEMAP_NS):
        page_url = (url_elem.text or "").strip()
        if page_url and _is_html_url(page_url):
            urls.append(page_url)

    return urls


async def parse_sitemap(sitemap_url: str) -> list[str]:
    """Parse a sitemap URL and return all discovered HTML page URLs.

    Handles both sitemap index files (which reference other sitemaps)
    and regular sitemaps (which list page URLs directly).
    """
    config = get_config()
    headers = {"User-Agent": config.user_agent}

    async with httpx.AsyncClient(headers=headers) as client:
        visited: set[str] = set()
        urls = await _parse_sitemap_recursive(client, sitemap_url, visited)

    unique = list(dict.fromkeys(urls))  # deduplicate, preserve order
    logger.info("Parsed %d unique URLs from %s", len(unique), sitemap_url)
    return unique
