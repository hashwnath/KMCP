"""Lambda handler that routes crawl jobs by source type."""

from __future__ import annotations

import json
import logging
import hashlib
from typing import Any
from datetime import datetime, timezone

import boto3

from src.common.aws_clients import get_dynamodb_resource, get_secretsmanager_client
from src.common.config import get_config
from src.common.models import CrawlJob, Document, SourceType

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _send_to_index_queue(documents: list[Document]) -> None:
    """Send processed documents to the INDEX_QUEUE for indexing."""
    config = get_config()
    if not config.index_queue_url:
        logger.error("INDEX_QUEUE_URL is not configured")
        return

    sqs = boto3.client("sqs", region_name=config.aws_region)
    for doc in documents:
        sqs.send_message(
            QueueUrl=config.index_queue_url,
            MessageBody=doc.model_dump_json(),
            MessageAttributes={
                "tenant_id": {"StringValue": doc.tenant_id, "DataType": "String"},
                "source_id": {"StringValue": doc.source_id, "DataType": "String"},
            },
        )
    logger.info("Sent %d documents to index queue", len(documents))


def _resolve_source_config(config: dict) -> dict:
    """Expand `secret_ref` credentials from Secrets Manager into config."""
    resolved = dict(config or {})
    secret_ref = resolved.get("secret_ref")
    if not secret_ref:
        return resolved

    sm = get_secretsmanager_client()
    payload = sm.get_secret_value(SecretId=secret_ref).get("SecretString", "{}")
    secret_values = json.loads(payload)
    if isinstance(secret_values, dict):
        resolved.update(secret_values)
    return resolved


def _update_source_crawl_progress(source_id: str, *, status: str, pages_found: int | None = None) -> None:
    """Persist crawl-stage progress fields on source record."""
    table = get_dynamodb_resource().Table(get_config().sources_table)
    expr = ["#s = :s", "updated_at = :u"]
    values: dict[str, Any] = {
        ":s": status,
        ":u": datetime.now(timezone.utc).isoformat(),
    }
    if pages_found is not None:
        expr.append("pages_found = :pf")
        values[":pf"] = pages_found

    table.update_item(
        Key={"source_id": source_id},
        UpdateExpression="SET " + ", ".join(expr),
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues=values,
    )


async def _dispatch_crawl(job: CrawlJob) -> list[Document]:
    """Dispatch to the appropriate connector based on source type."""
    cfg = _resolve_source_config(job.config)
    source_id = job.source_id
    tenant_id = job.tenant_id

    if job.action == "delete":
        from src.indexer.opensearch_client import delete_source_documents

        deleted = delete_source_documents(tenant_id, source_id)
        logger.info("Deleted %d indexed chunks for source_id=%s", deleted, source_id)
        return []

    if job.source_type == SourceType.WEBSITE_URL:
        from src.crawler.sitemap_parser import parse_sitemap
        from src.crawler.page_fetcher import fetch_pages_batch
        from src.crawler.html_to_markdown import html_to_markdown
        from src.crawler.metadata_extractor import extract_metadata
        from src.crawler.code_extractor import extract_code_blocks

        sitemap_url = cfg.get("sitemap_url") or cfg.get("url", "").rstrip("/") + "/sitemap.xml"
        urls = await parse_sitemap(sitemap_url)
        logger.info("Parsed %d URLs from sitemap %s", len(urls), sitemap_url)

        results = await fetch_pages_batch(urls, concurrency=cfg.get("concurrency", 5))
        documents: list[Document] = []
        for url, html, status in results:
            if status != 200 or not html:
                continue
            md = html_to_markdown(html, url)
            meta = extract_metadata(html, url)
            code = extract_code_blocks(md)
            doc_id = _hash_text(f"{tenant_id}:{source_id}:{url}")
            documents.append(
                Document(
                    doc_id=doc_id,
                    source_id=source_id,
                    tenant_id=tenant_id,
                    url=url,
                    title=meta.get("title", ""),
                    content_markdown=md,
                    content_hash=_hash_text(md),
                    metadata={**meta, "code_blocks": code},
                )
            )
        return documents

    if job.source_type == SourceType.CLOUD_STORAGE:
        from src.crawler.s3_connector import crawl_cloud_storage

        return await crawl_cloud_storage(
            provider=cfg.get("provider", "s3"),
            config=cfg,
            source_id=source_id,
            tenant_id=tenant_id,
        )

    if job.source_type == SourceType.WIKI_KB:
        platform = cfg.get("platform", "confluence")
        if platform == "confluence":
            from src.crawler.wiki_connector import crawl_confluence

            return await crawl_confluence(
                base_url=cfg["base_url"],
                space_key=cfg["space_key"],
                email=cfg["email"],
                api_token=cfg["api_token"],
                source_id=source_id,
                tenant_id=tenant_id,
            )
        if platform == "notion":
            from src.crawler.wiki_connector import crawl_notion

            return await crawl_notion(
                api_key=cfg["api_key"],
                root_page_id=cfg.get("root_page_id", ""),
                source_id=source_id,
                tenant_id=tenant_id,
            )
        if platform == "sharepoint":
            from src.crawler.wiki_connector import crawl_sharepoint

            return await crawl_sharepoint(
                site_url=cfg["site_url"],
                source_id=source_id,
                tenant_id=tenant_id,
            )
        if platform == "gitbook":
            from src.crawler.wiki_connector import crawl_gitbook

            return await crawl_gitbook(
                base_url=cfg["base_url"],
                source_id=source_id,
                tenant_id=tenant_id,
            )
        raise ValueError(f"Unsupported wiki platform: {platform}")

    if job.source_type == SourceType.GIT_REPO:
        from src.crawler.git_connector import crawl_git_repo

        return crawl_git_repo(
            repo_url=cfg["repo_url"],
            branch=cfg.get("branch", "main"),
            docs_path=cfg.get("docs_path", "docs"),
            source_id=source_id,
            tenant_id=tenant_id,
            token=cfg.get("token", ""),
        )

    if job.source_type == SourceType.FILE_UPLOAD:
        from src.crawler.file_processor import process_file

        s3 = boto3.client("s3", region_name=get_config().aws_region)
        bucket = cfg["bucket"]
        key = cfg["key"]
        resp = s3.get_object(Bucket=bucket, Key=key)
        file_bytes = resp["Body"].read()
        filename = key.rsplit("/", 1)[-1]
        md, meta = process_file(file_bytes, filename)
        return [
            Document(
                doc_id=_hash_text(f"{tenant_id}:{source_id}:{key}"),
                source_id=source_id,
                tenant_id=tenant_id,
                url=f"s3://{bucket}/{key}",
                title=meta.get("title", filename),
                content_markdown=md,
                content_hash=_hash_text(md),
                metadata=meta,
            )
        ]

    if job.source_type == SourceType.PASTE_TEXT:
        from src.crawler.text_ingestor import ingest_text

        return [
            ingest_text(
                text=cfg.get("text", ""),
                title=cfg.get("title", "Pasted Content"),
                source_id=source_id,
                tenant_id=tenant_id,
            )
        ]

    raise ValueError(f"Unsupported source type: {job.source_type}")


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda handler triggered by SQS crawl queue."""
    import asyncio

    processed = 0
    errors = 0

    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])
            job = CrawlJob(**body)
            logger.info(
                "Processing crawl job source_id=%s type=%s",
                job.source_id,
                job.source_type,
            )
            if job.action != "delete":
                _update_source_crawl_progress(job.source_id, status="crawling")
            documents = asyncio.get_event_loop().run_until_complete(
                _dispatch_crawl(job)
            )
            if job.action != "delete":
                _update_source_crawl_progress(job.source_id, status="indexing", pages_found=len(documents))
            _send_to_index_queue(documents)
            processed += len(documents)
            logger.info("Crawled %d documents for source_id=%s", len(documents), job.source_id)
        except Exception:
            errors += 1
            logger.exception("Failed to process crawl record")

    return {"processed": processed, "errors": errors}
