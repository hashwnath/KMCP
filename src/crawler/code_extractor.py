"""Extract fenced code blocks from markdown content."""

from __future__ import annotations

import re


_CODE_BLOCK_RE = re.compile(r"```([\w#+.-]*)\n(.*?)```", re.DOTALL)


def extract_code_blocks(markdown: str) -> list[dict]:
    """Return code blocks with minimal surrounding metadata."""
    blocks: list[dict] = []
    for match in _CODE_BLOCK_RE.finditer(markdown):
        language = (match.group(1) or "text").strip() or "text"
        code = match.group(2).strip()
        if not code:
            continue
        blocks.append(
            {
                "language": language,
                "code": code,
                "context": "",
                "line_number": 0,
            }
        )
    return blocks