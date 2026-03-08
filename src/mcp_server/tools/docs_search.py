"""docs_search tool — primary documentation search endpoint for AI agents."""

from __future__ import annotations

import time
from typing import Annotated

from fastmcp import Context

from src.analytics.logger import log_tool_call
from src.mcp_server.retrieval import search_docs
from src.mcp_server.tenant_context import get_current_tenant


async def docs_search(
    query: Annotated[
        str,
        "Search query to find relevant documentation pages. Be specific and include key terms. "
        "(Also accepted as 'question' for backward compatibility.)",
    ],
    question: Annotated[
        str,
        "Alias for 'query' — kept for backward compatibility with older MCP clients.",
    ] = "",
    ctx: Context | None = None,
) -> str:
    """Search official documentation and return up to 10 concise, high-quality content chunks.

    Each result includes the page title, URL, and a relevant excerpt (max ~500 tokens).
    Use this tool first to find relevant information, then use docs_fetch to read
    the full content of specific pages.

    Returns results as formatted text with title, URL, and excerpt for each match.
    """
    start_time = time.perf_counter()
    tenant_id = get_current_tenant()
    effective_query = query or question  # L5: parameter aliasing

    if not effective_query:
        return "Please provide a search query."

    try:
        results = await search_docs(tenant_id=tenant_id, query=effective_query, top_k=10)
    except Exception as exc:
        await log_tool_call(tenant_id, "docs_search", effective_query, result_count=0)
        return f"Search temporarily unavailable. Please try again. (Error: {type(exc).__name__})"

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    if not results:
        await log_tool_call(tenant_id, "docs_search", effective_query, result_count=0, latency_ms=latency_ms)
        return "No results found. Try rephrasing your query or using different terms."

    sections: list[str] = []
    for idx, hit in enumerate(results, start=1):
        section = (
            f"## Result {idx}: {hit.title}\n"
            f"**URL**: {hit.url}\n\n"
            f"{hit.excerpt}\n\n"
            f"---"
        )
        sections.append(section)

    formatted = "\n\n".join(sections)

    await log_tool_call(tenant_id, "docs_search", effective_query, result_count=len(results), latency_ms=latency_ms)

    return formatted
