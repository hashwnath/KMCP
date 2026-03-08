"""Lambda handler for the indexer pipeline.

Processes index jobs from SQS. Each message contains document content
that needs to be chunked, embedded, and pushed to OpenSearch.
Updates source status in DynamoDB after processing.
"""

import json
import logging
import traceback
from typing import Any

import boto3

from src.common.config import get_config
from src.common.models import Document
from src.crawler.code_extractor import extract_code_blocks
from src.indexer.chunker import chunk_document
from src.indexer.embedder import generate_embeddings
from src.indexer.opensearch_client import index_chunks
from src.indexer.code_indexer import index_code_samples

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

config = get_config()


def _get_tenant_doc_limit(tenant_id: str) -> int:
    """Return tenant-specific max_docs limit (fallback: config default)."""
    dynamodb = boto3.resource("dynamodb", region_name=config.aws_region)
    tenants_table = dynamodb.Table(config.tenants_table)
    tenant = tenants_table.get_item(Key={"tenant_id": tenant_id}).get("Item", {})
    return int(tenant.get("max_docs", config.max_docs_per_tenant))


def _get_current_docs_for_tenant(tenant_id: str) -> int:
    """Return aggregated doc_count across all tenant sources."""
    from boto3.dynamodb.conditions import Key

    dynamodb = boto3.resource("dynamodb", region_name=config.aws_region)
    sources_table = dynamodb.Table(config.sources_table)
    resp = sources_table.query(
        IndexName="tenant-index",
        KeyConditionExpression=Key("tenant_id").eq(tenant_id),
    )
    items = resp.get("Items", [])
    return sum(int(i.get("doc_count", 0)) for i in items)


def _update_source_status(
    tenant_id: str,
    source_id: str,
    status: str,
    *,
    pages_indexed: int | None = None,
    doc_count: int | None = None,
    error_message: str | None = None,
) -> None:
    """Update the source record in DynamoDB with current indexing status."""
    from datetime import datetime, timezone

    dynamodb = boto3.resource("dynamodb", region_name=config.aws_region)
    table = dynamodb.Table(config.sources_table)

    update_expr_parts = ["#s = :status", "updated_at = :now"]
    expr_names: dict[str, str] = {"#s": "status"}
    expr_values: dict[str, Any] = {
        ":status": status,
        ":now": datetime.now(timezone.utc).isoformat(),
    }

    if pages_indexed is not None:
        update_expr_parts.append("pages_indexed = :pages_indexed")
        expr_values[":pages_indexed"] = pages_indexed

    if doc_count is not None:
        update_expr_parts.append("doc_count = :doc_count")
        expr_values[":doc_count"] = doc_count

    if error_message is not None:
        update_expr_parts.append("error_message = :error_message")
        expr_values[":error_message"] = error_message

    table.update_item(
        Key={"source_id": source_id},
        UpdateExpression="SET " + ", ".join(update_expr_parts),
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
    )


def _process_message(message_body: dict) -> dict[str, Any]:
    """Process a single index job message.

    Expected message schema:
        {
            "tenant_id": str,
            "source_id": str,
            "doc_id": str,
            "markdown": str,
            "metadata": {
                "url": str,
                "title": str,
                "section": str,
                "breadcrumb": str
            },
            "code_blocks": [
                {"code": str, "language": str, "context": str, "line_number": int}
            ]
        }

    Returns summary dict with counts.
    """
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
    code_blocks: list[dict] = document.metadata.get("code_blocks", []) or extract_code_blocks(markdown)

    _update_source_status(tenant_id, source_id, "indexing")

    # Step 1: Chunk the document
    chunks = chunk_document(doc_id, tenant_id, markdown, metadata)
    logger.info("Chunked doc %s into %d chunks", doc_id, len(chunks))

    # Step 2: Generate embeddings for all chunks
    chunks = generate_embeddings(chunks)
    logger.info("Generated embeddings for %d chunks", len(chunks))

    # Step 3: Push chunks to OpenSearch
    max_docs = _get_tenant_doc_limit(tenant_id)
    current_docs = _get_current_docs_for_tenant(tenant_id)
    if current_docs + len(chunks) > max_docs:
        raise ValueError(
            f"max_docs limit exceeded ({current_docs + len(chunks)} > {max_docs}). "
            "Increase plan limit or remove old sources."
        )

    doc_count = index_chunks(tenant_id, chunks)
    logger.info("Indexed %d document chunks for tenant %s", doc_count, tenant_id)

    # Note: code blocks are already indexed as is_code=True chunks by the chunker.
    # The separate code_indexer was removed to prevent double-indexing.

    return {
        "doc_id": doc_id,
        "chunks_indexed": doc_count,
        "code_samples_indexed": 0,
    }


def handler(event: dict, context: Any) -> dict:
    """AWS Lambda entry point for the indexer.

    Receives SQS events with one or more index job messages.
    """
    results: list[dict] = []
    failures: list[str] = []

    records = event.get("Records", [])
    logger.info("Indexer received %d SQS records", len(records))

    for record in records:
        message_id = record.get("messageId", "unknown")
        try:
            body = json.loads(record["body"])
            result = _process_message(body)
            results.append(result)

            _update_source_status(
                body["tenant_id"],
                body["source_id"],
                "ready",
                pages_indexed=result["chunks_indexed"],
                doc_count=result["chunks_indexed"],
            )
        except Exception:
            logger.error(
                "Failed to process message %s: %s",
                message_id,
                traceback.format_exc(),
            )
            failures.append(message_id)

            # Best-effort status update on failure
            try:
                body = json.loads(record["body"])
                _update_source_status(
                    body["tenant_id"],
                    body["source_id"],
                    "failed",
                    error_message=traceback.format_exc()[:500],
                )
            except Exception:
                logger.error("Could not update status for failed message %s", message_id)

    response = {
        "statusCode": 200,
        "body": json.dumps({
            "processed": len(results),
            "failed": len(failures),
            "results": results,
            "failed_message_ids": failures,
        }),
    }

    # If any messages failed, report partial batch failure so SQS retries them
    if failures:
        response["batchItemFailures"] = [
            {"itemIdentifier": mid} for mid in failures
        ]

    return response
