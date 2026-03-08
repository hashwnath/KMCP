"""Tests for scheduled sync dispatcher."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.scheduler.handler import handler


def test_scheduler_enqueues_matching_sources(monkeypatch):
    sources = [
        {
            "source_id": "s1",
            "tenant_id": "t1",
            "source_type": "website_url",
            "config": {"url": "https://a.example"},
            "status": "ready",
        },
        {
            "source_id": "s2",
            "tenant_id": "t1",
            "source_type": "website_url",
            "config": {"url": "https://b.example"},
            "status": "indexing",
        },
    ]

    sqs = MagicMock()
    table = MagicMock()
    dynamo = MagicMock()
    dynamo.Table.return_value = table

    monkeypatch.setattr("src.scheduler.handler._iter_sources_for_cadence", lambda c: sources)
    monkeypatch.setattr("src.scheduler.handler.get_sqs_client", lambda: sqs)
    monkeypatch.setattr("src.scheduler.handler.get_dynamodb_resource", lambda: dynamo)
    monkeypatch.setattr(
        "src.scheduler.handler.migrate_source_item_if_needed",
        lambda table, source: {
            **source,
            "config": {
                "url": source["config"].get("url", ""),
                "secret_ref": "arn:sm:secret:s1",
            },
        },
    )
    monkeypatch.setattr(
        "src.scheduler.handler.get_config",
        lambda: SimpleNamespace(sources_table="test-sources", crawl_queue_url="https://queue"),
    )

    result = handler({"cadence": "hourly"}, context=None)

    assert result["cadence"] == "hourly"
    assert result["enqueued"] == 1
    assert sqs.send_message.call_count == 1
    assert table.update_item.call_count == 1
    payload = json.loads(sqs.send_message.call_args.kwargs["MessageBody"])
    assert payload["config"].get("secret_ref") == "arn:sm:secret:s1"


def test_scheduler_rejects_invalid_cadence():
    try:
        handler({"cadence": "monthly"}, context=None)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "cadence must be one of" in str(exc)
