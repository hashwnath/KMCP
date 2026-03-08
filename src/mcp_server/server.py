"""KnowledgeMCP — Main FastMCP server definition.

Sets up a multi-tenant MCP server that exposes docs_search, code_sample_search,
and docs_fetch tools over Streamable HTTP transport.

Tenant identity is injected via contextvars by the auth middleware — tools
never receive tenant_id as a user-supplied parameter (MS Learn Lesson 1).
"""

from fastmcp import FastMCP

from src.mcp_server.tools.docs_search import docs_search
from src.mcp_server.tools.code_search import code_sample_search
from src.mcp_server.tools.docs_fetch import docs_fetch

mcp = FastMCP(
    name="KnowledgeMCP",
    instructions=(
        "Search and read documentation. Use docs_search to find relevant pages, "
        "then docs_fetch to read the full content of the best match. "
        "Use code_sample_search to find code examples with optional language filter. "
        "Always search first, then fetch — this two-step pattern gives the best results."
    ),
)

# Register tools — tenant_id comes from auth middleware contextvars,
# NOT from agent parameters (prevents tenant isolation breach).
mcp.tool()(docs_search)
mcp.tool()(code_sample_search)
mcp.tool()(docs_fetch)
