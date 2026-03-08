"""docs_fetch tool — fetches full page content as clean markdown."""

from __future__ import annotations

import time
from typing import Annotated

from fastmcp import Context

from src.analytics.logger import log_tool_call
from src.mcp_server.retrieval import fetch_page
from src.mcp_server.tenant_context import get_current_tenant


async def docs_fetch(
    url: Annotated[
        str,
        "The URL of the documentation page to fetch. Use URLs from docs_search results.",
    ],
    ctx: Context | None = None,
) -> str:
    """Fetch and return the full content of a documentation page as clean markdown.

    Use this after docs_search when you need the complete content of a specific page.
    Provide the URL from a search result. Returns the page content with navigation
    and boilerplate removed.
    """
    start_time = time.perf_counter()
    tenant_id = get_current_tenant()

    try:
        markdown_content = await fetch_page(tenant_id=tenant_id, url=url)
    except Exception as exc:
        await log_tool_call(tenant_id, "docs_fetch", url, result_count=0)
        return f"Could not fetch page. (Error: {type(exc).__name__})"

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    if not markdown_content.strip():
        await log_tool_call(tenant_id, "docs_fetch", url, result_count=0, latency_ms=latency_ms)
        return "Could not extract meaningful content from this page."

    await log_tool_call(tenant_id, "docs_fetch", url, result_count=1, latency_ms=latency_ms)
    return markdown_content
