"""Scheduled sync dispatcher.

Triggered by EventBridge on hourly/daily/weekly cadences.
Finds sources matching cadence and enqueues crawl jobs.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from src.common.aws_clients import get_dynamodb_resource, get_sqs_client
from src.common.config import get_config
from src.common.source_secrets import migrate_source_item_if_needed


def _extract_cadence(event: dict) -> str:
    cadence = str((event or {}).get("cadence", "")).strip().lower()
    if cadence not in {"hourly", "daily", "weekly"}:
        raise ValueError("cadence must be one of: hourly, daily, weekly")
    return cadence


def _iter_sources_for_cadence(cadence: str):
    config = get_config()
    table = get_dynamodb_resource().Table(config.sources_table)

    scan_kwargs = {
        "FilterExpression": "sync_schedule = :sc",
        "ExpressionAttributeValues": {":sc": cadence},
    }
    response = table.scan(**scan_kwargs)
    for item in response.get("Items", []):
        yield item

    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"], **scan_kwargs)
        for item in response.get("Items", []):
            yield item


def handler(event: dict, context: object) -> dict:
    cadence = _extract_cadence(event)
    config = get_config()
    sqs = get_sqs_client()
    table = get_dynamodb_resource().Table(config.sources_table)

    now = datetime.now(timezone.utc).isoformat()
    enqueued = 0

    for source in _iter_sources_for_cadence(cadence):
        source = migrate_source_item_if_needed(table, source)
        status = source.get("status", "")
        if status in {"crawling", "indexing", "reindexing"}:
            continue

        source_id = source.get("source_id")
        tenant_id = source.get("tenant_id")
        source_type = source.get("source_type")
        source_config = source.get("config", {})

        if not (source_id and tenant_id and source_type):
            continue

        sqs.send_message(
            QueueUrl=config.crawl_queue_url,
            MessageBody=json.dumps(
                {
                    "tenant_id": tenant_id,
                    "source_id": source_id,
                    "source_type": source_type,
                    "config": source_config,
                    "action": "scheduled_sync",
                    "schedule": cadence,
                }
            ),
        )
        table.update_item(
            Key={"source_id": source_id},
            UpdateExpression="SET #s = :s, last_scheduled_at = :ls, updated_at = :u",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":s": "pending",
                ":ls": now,
                ":u": now,
            },
        )
        enqueued += 1

    return {"cadence": cadence, "enqueued": enqueued}
