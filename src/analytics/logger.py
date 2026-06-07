"""Log queries via the AnalyticsRepository backend."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from src.common.backends.factory import get_analytics_repo

logger = logging.getLogger(__name__)


def _sync_log_query(
    tenant_id: str,
    tool_name: str,
    query: str,
    results_count: int,
    latency_ms: int,
) -> None:
    """Synchronous persist — call via asyncio.to_thread to avoid blocking."""
    try:
        get_analytics_repo().log_query(
            {
                "tenant_id": tenant_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tool_name": tool_name,
                "query": query,
                "results_count": results_count,
                "latency_ms": latency_ms,
            }
        )
    except Exception:
        logger.exception(
            "Failed to log query for tenant=%s tool=%s", tenant_id, tool_name
        )


# Public alias for backward compatibility
log_query = _sync_log_query


async def log_tool_call(
    tenant_id: str,
    tool_name: str,
    query: str,
    result_count: int = 0,
    latency_ms: int = 0,
    **_: object,
) -> None:
    """Non-blocking async wrapper used by the MCP tool layer."""
    await asyncio.to_thread(
        _sync_log_query,
        tenant_id=tenant_id,
        tool_name=tool_name,
        query=query,
        results_count=result_count,
        latency_ms=latency_ms,
    )
