"""Indexer handler.

In AWS this is a Lambda triggered by SQS index queue. In local mode this
handler is called by the worker thread for each pending index job.
"""

import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Any

from src.common.backends.factory import get_source_repo, get_tenant_repo
from src.common.config import get_config
from src.common.models import Document
from src.crawler.code_extractor import extract_code_blocks
from src.indexer.chunker import chunk_document
from src.indexer.embedder import generate_embeddings
from src.indexer.opensearch_client import index_chunks

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _get_tenant_doc_limit(tenant_id: str) -> int:
    """Return tenant-specific max_docs limit (fallback: config default)."""
    tenant = get_tenant_repo().get_by_id(tenant_id) or {}
    return int(tenant.get("max_docs", get_config().max_docs_per_tenant))


def _get_current_docs_for_tenant(tenant_id: str) -> int:
    """Return aggregated doc_count across all tenant sources."""
    sources = get_source_repo().list_by_tenant(tenant_id)
    return sum(int(s.get("doc_count", 0)) for s in sources)


def _update_source_status(
    tenant_id: str,
    source_id: str,
    status: str,
    *,
    pages_indexed: int | None = None,
    doc_count: int | None = None,
    error_message: str | None = None,
) -> None:
    updates: dict[str, Any] = {
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if pages_indexed is not None:
        updates["pages_indexed"] = pages_indexed
    if doc_count is not None:
        updates["doc_count"] = doc_count
    if error_message is not None:
        updates["error_message"] = error_message
    get_source_repo().update(source_id, updates)


def _process_message(message_body: dict) -> dict[str, Any]:
    document = Document(**message_body)
    tenant_id = document.tenant_id
    source_id = document.source_id
    doc_id = document.doc_id
    markdown = document.content_markdown
    metadata = {
        **document.metadata,
        "url": document.url,
        "title": document.title,
        "source_id": source_id,
    }
    _ = document.metadata.get("code_blocks", []) or extract_code_blocks(markdown)

    _update_source_status(tenant_id, source_id, "indexing")

    chunks = chunk_document(doc_id, tenant_id, markdown, metadata)
    logger.info("Chunked doc %s into %d chunks", doc_id, len(chunks))

    chunks = generate_embeddings(chunks)
    logger.info("Generated embeddings for %d chunks", len(chunks))

    max_docs = _get_tenant_doc_limit(tenant_id)
    current_docs = _get_current_docs_for_tenant(tenant_id)
    if current_docs + len(chunks) > max_docs:
        raise ValueError(
            f"max_docs limit exceeded ({current_docs + len(chunks)} > {max_docs}). "
            "Increase plan limit or remove old sources."
        )

    doc_count = index_chunks(tenant_id, chunks)
    logger.info("Indexed %d document chunks for tenant %s", doc_count, tenant_id)

    return {
        "doc_id": doc_id,
        "chunks_indexed": doc_count,
        "code_samples_indexed": 0,
    }


def process_index_job(message_body: dict) -> dict[str, Any]:
    """Public, backend-agnostic entrypoint used by the local worker."""
    result = _process_message(message_body)
    _update_source_status(
        message_body["tenant_id"],
        message_body["source_id"],
        "ready",
        pages_indexed=result["chunks_indexed"],
        doc_count=result["chunks_indexed"],
    )
    return result


def handler(event: dict, context: Any) -> dict:
    """AWS Lambda entry point — SQS event with one or more index jobs."""
    results: list[dict] = []
    failures: list[str] = []

    records = event.get("Records", [])
    logger.info("Indexer received %d SQS records", len(records))

    for record in records:
        message_id = record.get("messageId", "unknown")
        try:
            body = json.loads(record["body"])
            result = process_index_job(body)
            results.append(result)
        except Exception:
            logger.error(
                "Failed to process message %s: %s",
                message_id,
                traceback.format_exc(),
            )
            failures.append(message_id)
            try:
                body = json.loads(record["body"])
                _update_source_status(
                    body["tenant_id"],
                    body["source_id"],
                    "failed",
                    error_message=traceback.format_exc()[:500],
                )
            except Exception:
                logger.error(
                    "Could not update status for failed message %s", message_id
                )

    response = {
        "statusCode": 200,
        "body": json.dumps(
            {
                "processed": len(results),
                "failed": len(failures),
                "results": results,
                "failed_message_ids": failures,
            }
        ),
    }
    if failures:
        response["batchItemFailures"] = [
            {"itemIdentifier": mid} for mid in failures
        ]
    return response
