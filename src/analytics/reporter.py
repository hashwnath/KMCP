"""Generate analytics reports from DynamoDB query logs."""

from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from boto3.dynamodb.conditions import Key

from src.common.aws_clients import get_dynamodb_resource
from src.common.config import get_config


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _query_logs(tenant_id: str, days: int) -> list[dict]:
    """Fetch all analytics rows for *tenant_id* within the last *days* days."""
    table = get_dynamodb_resource().Table(get_config().analytics_table)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    items: list[dict] = []
    kwargs: dict = {
        "KeyConditionExpression": (
            Key("tenant_id").eq(tenant_id) & Key("timestamp").gte(since)
        ),
    }

    while True:
        resp = table.query(**kwargs)
        items.extend(resp.get("Items", []))
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key

    return items


def _safe_int(value: object) -> int:
    """Convert DynamoDB Decimal / str to plain int."""
    if isinstance(value, Decimal):
        return int(value)
    return int(value)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_overview(tenant_id: str) -> dict:
    """Return summary stats for the tenant dashboard.

    Keys: ``total_queries_today``, ``total_queries_week``,
    ``total_docs_indexed``, ``top_queries_week``, ``last_sync``.
    """
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0,
    ).isoformat()

    week_items = _query_logs(tenant_id, days=7)
    today_items = [i for i in week_items if i["timestamp"] >= today_start]

    query_counter: Counter[str] = Counter()
    for item in week_items:
        query_counter[item["query"]] += 1

    # Estimate indexed docs from sources table
    config = get_config()
    sources_table = get_dynamodb_resource().Table(config.sources_table)
    sources_resp = sources_table.query(
        IndexName="tenant-index",
        KeyConditionExpression=Key("tenant_id").eq(tenant_id),
    )
    sources = sources_resp.get("Items", [])
    total_docs = sum(_safe_int(s.get("doc_count", 0)) for s in sources)
    last_sync = max(
        (s.get("updated_at", "") for s in sources),
        default=None,
    )

    return {
        "total_queries_today": len(today_items),
        "total_queries_week": len(week_items),
        "total_docs_indexed": total_docs,
        "top_queries_week": [
            {"query": q, "count": c}
            for q, c in query_counter.most_common(10)
        ],
        "last_sync": last_sync,
    }


def get_top_queries(
    tenant_id: str, days: int = 7, limit: int = 20,
) -> list[dict]:
    """Return the top *limit* queries by frequency over the last *days* days."""
    items = _query_logs(tenant_id, days)
    counter: Counter[str] = Counter()
    for item in items:
        counter[item["query"]] += 1

    return [
        {"query": q, "count": c}
        for q, c in counter.most_common(limit)
    ]


def get_content_gaps(
    tenant_id: str, days: int = 7, limit: int = 20,
) -> list[dict]:
    """Return queries that returned 0 or very few results — content gaps.

    This is the **killer feature**: it surfaces documentation holes that
    real users are hitting so the tenant can fill them.

    Returns a list of ``{query, count, avg_results}`` sorted by frequency.
    """
    items = _query_logs(tenant_id, days)

    gap_data: dict[str, list[int]] = {}
    for item in items:
        results_count = _safe_int(item.get("results_count", 0))
        if results_count <= 2:  # 0, 1, or 2 results considered a gap
            gap_data.setdefault(item["query"], []).append(results_count)

    gaps = [
        {
            "query": q,
            "count": len(counts),
            "avg_results": round(sum(counts) / len(counts), 2),
        }
        for q, counts in gap_data.items()
    ]
    gaps.sort(key=lambda g: g["count"], reverse=True)
    return gaps[:limit]


def get_tool_usage_breakdown(
    tenant_id: str, days: int = 7,
) -> dict[str, int]:
    """Return per-tool query counts: ``{docs_search: N, code_sample_search: N, …}``."""
    items = _query_logs(tenant_id, days)
    counter: Counter[str] = Counter()
    for item in items:
        counter[item.get("tool_name", "unknown")] += 1
    return dict(counter)
