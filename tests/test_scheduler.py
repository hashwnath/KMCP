"""Tests for scheduled sync dispatcher."""

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

    repo = MagicMock()
    repo.list_by_schedule.return_value = iter(sources)
    queue = MagicMock()

    monkeypatch.setattr("src.scheduler.handler.get_source_repo", lambda: repo)
    monkeypatch.setattr("src.scheduler.handler.get_queue", lambda: queue)
    monkeypatch.setattr(
        "src.scheduler.handler.migrate_source_item_if_needed",
        lambda _table, source: {
            **source,
            "config": {
                "url": source["config"].get("url", ""),
                "secret_ref": "arn:sm:secret:s1",
            },
        },
    )

    result = handler({"cadence": "hourly"}, context=None)

    assert result["cadence"] == "hourly"
    assert result["enqueued"] == 1
    queue.send.assert_called_once()
    args, kwargs = queue.send.call_args
    assert args[0] == "crawl"
    assert args[1]["config"].get("secret_ref") == "arn:sm:secret:s1"
    repo.update.assert_called_once()


def test_scheduler_rejects_invalid_cadence():
    try:
        handler({"cadence": "monthly"}, context=None)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "cadence must be one of" in str(exc)
