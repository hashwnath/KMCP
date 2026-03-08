"""Indexer-side HTML to markdown conversion helper."""

from __future__ import annotations

from src.crawler.html_to_markdown import html_to_markdown as crawler_html_to_markdown


def html_to_markdown(html: str) -> str:
    """Reuse crawler conversion without URL-specific behavior."""
    return crawler_html_to_markdown(html, "")