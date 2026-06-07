"""SQS implementation of the JobQueue Protocol."""

from __future__ import annotations

import json

from src.common.aws_clients import get_sqs_client
from src.common.config import get_config


_QUEUE_URL_BY_NAME = {
    "crawl": "crawl_queue_url",
    "index": "index_queue_url",
}


def _resolve_queue_url(queue_name: str) -> str:
    attr = _QUEUE_URL_BY_NAME.get(queue_name)
    if not attr:
        raise ValueError(f"Unknown queue name: {queue_name!r}")
    url = getattr(get_config(), attr, "")
    if not url:
        raise RuntimeError(f"Queue URL for {queue_name!r} is not configured")
    return url


class SqsJobQueue:
    def send(self, queue_name: str, message: dict) -> None:
        url = _resolve_queue_url(queue_name)
        get_sqs_client().send_message(
            QueueUrl=url,
            MessageBody=json.dumps(message),
        )

    def poll(self, queue_name: str, max_messages: int = 1):
        raise NotImplementedError(
            "Polling is not used in AWS mode — SQS pushes to Lambda via event source mapping."
        )

    def ack(self, queue_name: str, receipt: str) -> None:
        raise NotImplementedError("Acknowledgement handled by Lambda SQS integration.")

    def fail(self, queue_name: str, receipt: str, error: str) -> None:
        raise NotImplementedError("Failure handled by Lambda SQS integration.")
