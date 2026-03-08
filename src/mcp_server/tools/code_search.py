"""code_sample_search tool — searches the code-specific index for examples."""

from __future__ import annotations

import time
from typing import Annotated

from fastmcp import Context

from src.analytics.logger import log_tool_call
from src.mcp_server.retrieval import search_code
from src.mcp_server.tenant_context import get_current_tenant


async def code_sample_search(
    query: Annotated[
        str,
        "Search query to find code examples and snippets in the documentation.",
    ],
    language: Annotated[
        str,
        "Optional programming language filter (e.g., 'python', 'javascript', 'typescript'). "
        "Leave empty for all languages.",
    ] = "",
    ctx: Context | None = None,
) -> str:
    """Search for code snippets and examples in the documentation.

    Returns up to 20 relevant code samples with their surrounding context,
    programming language, and source URL. Use the optional language parameter
    to filter results by programming language.
    """
    start_time = time.perf_counter()
    tenant_id = get_current_tenant()

    try:
        results = await search_code(
            tenant_id=tenant_id,
            query=query,
            language=language,
            top_k=20,
        )
    except Exception as exc:
        await log_tool_call(tenant_id, "code_sample_search", query, result_count=0)
        return f"Code search temporarily unavailable. (Error: {type(exc).__name__})"

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    if not results:
        await log_tool_call(tenant_id, "code_sample_search", query, result_count=0, latency_ms=latency_ms)
        return "No code samples found. Try broadening your query or removing the language filter."

    sections: list[str] = []
    for hit in results:
        lang_tag = hit.language or "text"
        section = (
            f"### {hit.title} ({lang_tag})\n"
            f"**URL**: {hit.url}\n"
            f"**Context**: {hit.context}\n\n"
            f"```{lang_tag}\n"
            f"{hit.code}\n"
            f"```\n\n"
            f"---"
        )
        sections.append(section)

    formatted = "\n\n".join(sections)

    await log_tool_call(tenant_id, "code_sample_search", query, result_count=len(results), latency_ms=latency_ms)

    return formatted
