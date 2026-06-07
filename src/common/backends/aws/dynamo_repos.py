"""DynamoDB implementations of TenantRepository / SourceRepository / AnalyticsRepository.

Preserves the exact access patterns used by the existing handlers:
  - Tenant.get_by_id            -> get_item by PK tenant_id
  - Tenant.get_by_slug          -> query slug-index GSI
  - Tenant.get_by_email         -> scan with email filter (existing behavior)
  - Source.get_by_id            -> get_item by PK source_id
  - Source.list_by_tenant       -> query tenant-index GSI
  - Source.list_by_schedule     -> scan with sync_schedule filter (existing behavior)
  - Analytics.log_query         -> put_item
  - Analytics.query_logs        -> query by (tenant_id, timestamp gte)
"""

from __future__ import annotations

from typing import Iterator, Optional

from boto3.dynamodb.conditions import Key

from src.common.aws_clients import get_dynamodb_resource
from src.common.config import get_config


class DynamoTenantRepository:
    def _table(self):
        return get_dynamodb_resource().Table(get_config().tenants_table)

    def get_by_id(self, tenant_id: str) -> Optional[dict]:
        resp = self._table().get_item(Key={"tenant_id": tenant_id})
        return resp.get("Item")

    def get_by_slug(self, slug: str) -> Optional[dict]:
        resp = self._table().query(
            IndexName="slug-index",
            KeyConditionExpression=Key("slug").eq(slug),
            Limit=1,
        )
        items = resp.get("Items", [])
        return items[0] if items else None

    def get_by_email(self, email: str) -> Optional[dict]:
        # Existing behaviour: table scan + email filter. Acceptable at OSS-MVP scale.
        resp = self._table().scan(
            FilterExpression="email = :e",
            ExpressionAttributeValues={":e": email},
            Limit=1,
        )
        items = resp.get("Items", [])
        return items[0] if items else None

    def put(self, item: dict) -> None:
        self._table().put_item(Item=item)

    def update(self, tenant_id: str, updates: dict) -> None:
        if not updates:
            return
        update_parts, attr_values, attr_names = _build_update_expression(updates)
        kwargs = dict(
            Key={"tenant_id": tenant_id},
            UpdateExpression="SET " + ", ".join(update_parts),
            ExpressionAttributeValues=attr_values,
        )
        if attr_names:
            kwargs["ExpressionAttributeNames"] = attr_names
        self._table().update_item(**kwargs)

    def delete(self, tenant_id: str) -> None:
        self._table().delete_item(Key={"tenant_id": tenant_id})


class DynamoSourceRepository:
    def _table(self):
        return get_dynamodb_resource().Table(get_config().sources_table)

    def get_by_id(self, source_id: str) -> Optional[dict]:
        resp = self._table().get_item(Key={"source_id": source_id})
        return resp.get("Item")

    def list_by_tenant(self, tenant_id: str) -> list[dict]:
        resp = self._table().query(
            IndexName="tenant-index",
            KeyConditionExpression=Key("tenant_id").eq(tenant_id),
        )
        return list(resp.get("Items", []))

    def list_by_schedule(self, schedule: str) -> Iterator[dict]:
        table = self._table()
        kwargs = dict(
            FilterExpression="sync_schedule = :sc",
            ExpressionAttributeValues={":sc": schedule},
        )
        resp = table.scan(**kwargs)
        for item in resp.get("Items", []):
            yield item
        while "LastEvaluatedKey" in resp:
            resp = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"], **kwargs)
            for item in resp.get("Items", []):
                yield item

    def put(self, item: dict) -> None:
        self._table().put_item(Item=item)

    def update(self, source_id: str, updates: dict) -> None:
        if not updates:
            return
        update_parts, attr_values, attr_names = _build_update_expression(updates)
        kwargs = dict(
            Key={"source_id": source_id},
            UpdateExpression="SET " + ", ".join(update_parts),
            ExpressionAttributeValues=attr_values,
        )
        if attr_names:
            kwargs["ExpressionAttributeNames"] = attr_names
        self._table().update_item(**kwargs)

    def delete(self, source_id: str) -> None:
        self._table().delete_item(Key={"source_id": source_id})


class DynamoAnalyticsRepository:
    def _table(self):
        return get_dynamodb_resource().Table(get_config().analytics_table)

    def log_query(self, item: dict) -> None:
        self._table().put_item(Item=item)

    def query_logs(self, tenant_id: str, since_iso: str) -> list[dict]:
        table = self._table()
        items: list[dict] = []
        kwargs = dict(
            KeyConditionExpression=(
                Key("tenant_id").eq(tenant_id) & Key("timestamp").gte(since_iso)
            ),
        )
        while True:
            resp = table.query(**kwargs)
            items.extend(resp.get("Items", []))
            last = resp.get("LastEvaluatedKey")
            if not last:
                break
            kwargs["ExclusiveStartKey"] = last
        return items


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Words that collide with DynamoDB reserved keywords and therefore need an
# ExpressionAttributeNames alias. Keep small; expand as callers add fields.
_RESERVED = {"status", "slug", "name", "size", "type", "user", "data", "comment"}


def _build_update_expression(updates: dict) -> tuple[list[str], dict, dict]:
    """Convert a {field: value} dict into Dynamo UpdateExpression parts.

    Returns (update_parts, attr_values, attr_names).
    """
    parts: list[str] = []
    values: dict = {}
    names: dict = {}
    for i, (key, value) in enumerate(updates.items()):
        vkey = f":v{i}"
        if key.lower() in _RESERVED:
            nkey = f"#k{i}"
            names[nkey] = key
            parts.append(f"{nkey} = {vkey}")
        else:
            parts.append(f"{key} = {vkey}")
        values[vkey] = value
    return parts, values, names
