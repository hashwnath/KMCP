"""Backfill legacy source configs by moving inline secrets to Secrets Manager.

Run:
    python scripts/migrate_legacy_source_secrets.py
"""

from __future__ import annotations

from src.common.aws_clients import get_dynamodb_resource
from src.common.config import get_config
from src.common.source_secrets import migrate_source_item_if_needed, split_sensitive_config


def main() -> None:
    cfg = get_config()
    table = get_dynamodb_resource().Table(cfg.sources_table)

    scanned = 0
    migrated = 0

    response = table.scan()
    items = response.get("Items", [])

    while True:
        for item in items:
            scanned += 1
            _, sensitive = split_sensitive_config(item.get("config", {}))
            if not sensitive:
                continue
            migrate_source_item_if_needed(table, item)
            migrated += 1

        last = response.get("LastEvaluatedKey")
        if not last:
            break

        response = table.scan(ExclusiveStartKey=last)
        items = response.get("Items", [])

    print(f"Scanned: {scanned}")
    print(f"Migrated: {migrated}")


if __name__ == "__main__":
    main()
