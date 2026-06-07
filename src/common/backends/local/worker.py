"""Background worker that drains the local SQLite job queue.

Runs as either a standalone process (``python -m src.common.backends.local.worker``)
or a background thread (see ``run_in_thread``). Polls both ``crawl`` and
``index`` queues with a short sleep between empty polls.
"""

from __future__ import annotations

import logging
import threading
import time
import traceback
from typing import Optional

logger = logging.getLogger(__name__)


_POLL_INTERVAL_S = 1.0


def _process_one(queue_name: str, job: dict) -> bool:
    """Run a single job. Returns True on success."""
    body = job["body"]
    try:
        if queue_name == "crawl":
            from src.crawler.handler import process_crawl_job
            process_crawl_job(body)
        elif queue_name == "index":
            from src.indexer.handler import process_index_job
            process_index_job(body)
        else:
            raise ValueError(f"Unknown queue: {queue_name}")
        return True
    except Exception:
        logger.exception("Worker job failed: queue=%s receipt=%s", queue_name, job["receipt"])
        return False


def run_forever(stop_event: Optional[threading.Event] = None) -> None:
    """Main worker loop. Pass a stop_event to allow graceful shutdown."""
    from src.common.backends.factory import get_queue

    logger.info("KnowledgeMCP local worker starting")
    queue = get_queue()

    while True:
        if stop_event is not None and stop_event.is_set():
            logger.info("Worker stop requested; exiting")
            return
        did_work = False
        for q in ("crawl", "index"):
            jobs = queue.poll(q, max_messages=1)
            for job in jobs:
                did_work = True
                ok = _process_one(q, job)
                if ok:
                    queue.ack(q, job["receipt"])
                else:
                    queue.fail(q, job["receipt"], traceback.format_exc())
        if not did_work:
            time.sleep(_POLL_INTERVAL_S)


def run_in_thread() -> threading.Event:
    """Start the worker on a daemon thread. Returns the stop event."""
    stop = threading.Event()
    t = threading.Thread(target=run_forever, args=(stop,), name="kmcp-worker", daemon=True)
    t.start()
    return stop


if __name__ == "__main__":
    import os
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run_forever()
