"""SQLite-backed JobQueue + background worker.

Design:
  - send(): inserts into jobs table with status='pending'
  - poll(): atomically claims oldest pending row -> 'in_flight', returns it
  - ack():  marks the row 'done' (and removes after a short retention)
  - fail(): marks row 'failed' with attempts++; queue is at-least-once
            up to MAX_ATTEMPTS, then leaves it 'failed' for inspection

The actual handler dispatch (calling crawler.process_crawl_job /
indexer.process_index_job) lives in src/common/backends/local/worker.py,
which can be run as a separate process (`python -m src.common.backends.local.worker`)
or as a thread started by the admin container at startup.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from src.common.backends.local.sqlite_db import _connect


MAX_ATTEMPTS = 3


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SqliteJobQueue:
    def send(self, queue_name: str, message: dict) -> None:
        if queue_name not in {"crawl", "index"}:
            raise ValueError(f"Unknown queue name: {queue_name!r}")
        now = _now_iso()
        _connect().execute(
            "INSERT INTO jobs (queue_name, payload_json, status, created_at, updated_at) "
            "VALUES (?, ?, 'pending', ?, ?)",
            (queue_name, json.dumps(message), now, now),
        )

    def poll(self, queue_name: str, max_messages: int = 1) -> list[dict]:
        """Atomically claim up to max_messages pending jobs."""
        conn = _connect()
        claimed: list[dict] = []
        now = _now_iso()
        for _ in range(max_messages):
            # SQLite has no SELECT ... FOR UPDATE; use a write transaction
            # via BEGIN IMMEDIATE which acquires the RESERVED lock.
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    "SELECT job_id, payload_json, attempts FROM jobs "
                    "WHERE status = 'pending' AND queue_name = ? "
                    "ORDER BY job_id LIMIT 1",
                    (queue_name,),
                ).fetchone()
                if not row:
                    conn.execute("COMMIT")
                    break
                conn.execute(
                    "UPDATE jobs SET status = 'in_flight', updated_at = ?, "
                    "attempts = attempts + 1 WHERE job_id = ?",
                    (now, row["job_id"]),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
            try:
                payload = json.loads(row["payload_json"])
            except Exception:
                payload = {}
            claimed.append(
                {
                    "receipt": str(row["job_id"]),
                    "attempts": int(row["attempts"]) + 1,
                    "body": payload,
                }
            )
        return claimed

    def ack(self, queue_name: str, receipt: str) -> None:
        _connect().execute(
            "UPDATE jobs SET status = 'done', updated_at = ? WHERE job_id = ?",
            (_now_iso(), int(receipt)),
        )

    def fail(self, queue_name: str, receipt: str, error: str) -> None:
        conn = _connect()
        row = conn.execute(
            "SELECT attempts FROM jobs WHERE job_id = ?", (int(receipt),)
        ).fetchone()
        attempts = int(row["attempts"]) if row else 0
        if attempts >= MAX_ATTEMPTS:
            conn.execute(
                "UPDATE jobs SET status = 'failed', error = ?, updated_at = ? "
                "WHERE job_id = ?",
                (error[:1000], _now_iso(), int(receipt)),
            )
        else:
            # Retry: put back into pending
            conn.execute(
                "UPDATE jobs SET status = 'pending', error = ?, updated_at = ? "
                "WHERE job_id = ?",
                (error[:1000], _now_iso(), int(receipt)),
            )
