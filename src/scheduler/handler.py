"""Scheduled sync dispatcher.

In AWS this is triggered by EventBridge on hourly/daily/weekly cadences.
In local mode it can be invoked by an external scheduler (cron or a one-shot
manual call from the worker container).
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.common.backends.factory import get_queue, get_source_repo
from src.common.source_secrets import migrate_source_item_if_needed


def _extract_cadence(event: dict) -> str:
    cadence = str((event or {}).get("cadence", "")).strip().lower()
    if cadence not in {"hourly", "daily", "weekly"}:
        raise ValueError("cadence must be one of: hourly, daily, weekly")
    return cadence


def handler(event: dict, context: object) -> dict:
    cadence = _extract_cadence(event)
    source_repo = get_source_repo()
    queue = get_queue()

    now = datetime.now(timezone.utc).isoformat()
    enqueued = 0

    for source in source_repo.list_by_schedule(cadence):
        # Pass None: secret migration uses the SourceRepository path now.
        source = migrate_source_item_if_needed(None, source)
        status = source.get("status", "")
        if status in {"crawling", "indexing", "reindexing"}:
            continue

        source_id = source.get("source_id")
        tenant_id = source.get("tenant_id")
        source_type = source.get("source_type")
        source_config = source.get("config", {})

        if not (source_id and tenant_id and source_type):
            continue

        queue.send(
            "crawl",
            {
                "tenant_id": tenant_id,
                "source_id": source_id,
                "source_type": source_type,
                "config": source_config,
                "action": "scheduled_sync",
                "schedule": cadence,
            },
        )
        source_repo.update(
            source_id,
            {
                "status": "pending",
                "last_scheduled_at": now,
                "updated_at": now,
            },
        )
        enqueued += 1

    return {"cadence": cadence, "enqueued": enqueued}
