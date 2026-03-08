"""Convert HTML pages into clean markdown for indexing."""

from __future__ import annotations

from bs4 import BeautifulSoup
from markdownify import markdownify


def html_to_markdown(html: str, url: str = "") -> str:
    """Convert a raw HTML document into readable markdown.

    The MVP strips low-value structural tags before conversion to reduce noise.
    """
    soup = BeautifulSoup(html, "lxml")
    for selector in ("nav", "header", "footer", "aside", "script", "style"):
        for node in soup.select(selector):
            node.decompose()

    markdown = markdownify(str(soup), heading_style="ATX")
    lines = [line.rstrip() for line in markdown.splitlines()]
    collapsed: list[str] = []
    blank_run = 0
    for line in lines:
        if line.strip():
            blank_run = 0
            collapsed.append(line)
            continue
        blank_run += 1
        if blank_run <= 1:
            collapsed.append("")
    return "\n".join(collapsed).strip()