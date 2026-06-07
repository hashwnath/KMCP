"""Job queue Protocol used by admin/scheduler to enqueue crawl jobs.

In AWS mode this is backed by SQS. In local mode this is backed by a SQLite
jobs table consumed by a background worker thread (see local.sqlite_queue).

The contract is intentionally minimal: send (enqueue) and (for local mode)
poll/ack/fail used by the local worker. AWS adapter implements only `send`
since SQS event-source mapping pushes records to the Lambda handler.
"""

from __future__ import annotations

from typing import Any, Iterator, Optional, Protocol


class JobQueue(Protocol):
    """Minimal job-queue contract for crawl/index jobs."""

    def send(self, queue_name: str, message: dict) -> None: ...

    # Optional methods used only by the local worker. AWS adapter raises
    # NotImplementedError if called (it's not how SQS+Lambda works).
    def poll(self, queue_name: str, max_messages: int = 1) -> list[dict]:
        return []

    def ack(self, queue_name: str, receipt: str) -> None:
        return None

    def fail(self, queue_name: str, receipt: str, error: str) -> None:
        return None
