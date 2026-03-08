"""Log queries to DynamoDB for analytics tracking."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from src.common.aws_clients import get_dynamodb_resource
from src.common.config import get_config

logger = logging.getLogger(__name__)


def _sync_log_query(
    tenant_id: str,
    tool_name: str,
    query: str,
    results_count: int,
    latency_ms: int,
) -> None:
    """Synchronous DynamoDB put — run via asyncio.to_thread to avoid blocking."""
    try:
        table = get_dynamodb_resource().Table(get_config().analytics_table)
        table.put_item(Item={
            "tenant_id": tenant_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool_name": tool_name,
            "query": query,
            "results_count": results_count,
            "latency_ms": latency_ms,
        })
    except Exception:
        logger.exception("Failed to log query for tenant=%s tool=%s", tenant_id, tool_name)


# Keep the old name as a public alias for backward compatibility
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
