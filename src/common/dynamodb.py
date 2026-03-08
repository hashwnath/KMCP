"""Small DynamoDB helpers used by the runtime edge."""

from __future__ import annotations

from boto3.dynamodb.conditions import Key

from src.common.aws_clients import get_dynamodb_resource
from src.common.config import get_config


async def get_tenant_by_slug(slug: str) -> dict | None:
    """Look up a full tenant record by slug.

    Uses the slug-index GSI for O(1) lookup instead of a full table scan.
    Returns the full tenant dict (tenant_id, slug, api_key, rate_limit, …)
    or None if not found.
    """
    table = get_dynamodb_resource().Table(get_config().tenants_table)
    response = table.query(
        IndexName="slug-index",
        KeyConditionExpression=Key("slug").eq(slug),
        Limit=1,
    )
    items = response.get("Items", [])
    return items[0] if items else None


async def get_tenant_api_key(slug: str) -> str | None:
    """Look up a tenant API key by slug (convenience wrapper)."""
    tenant = await get_tenant_by_slug(slug)
    return tenant.get("api_key") if tenant else None