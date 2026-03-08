"""Extract lightweight metadata from crawled HTML pages."""

from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup


def extract_metadata(html: str, url: str) -> dict:
    """Extract page metadata used by the indexer and analytics."""
    soup = BeautifulSoup(html, "lxml")

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    description = ""
    description_tag = soup.find("meta", attrs={"name": "description"})
    if description_tag and description_tag.get("content"):
        description = description_tag["content"].strip()

    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()

    path = urlparse(url).path.rstrip("/")
    slug = path.split("/")[-1] if path else "home"

    return {
        "title": title or slug or url,
        "description": description,
        "url": url,
        "slug": slug,
    }