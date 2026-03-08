"""Cloud storage connectors for S3, Azure Blob, and GCS ingestion."""

from __future__ import annotations

import hashlib
import io
import json

import boto3

from src.crawler.file_processor import process_file
from src.common.models import Document


async def crawl_s3_bucket(
    bucket: str,
    prefix: str,
    aws_access_key: str,
    aws_secret_key: str,
    source_id: str,
    tenant_id: str,
) -> list[Document]:
    """Fetch S3 objects under a prefix and normalize them into documents."""
    client_kwargs = {}
    if aws_access_key and aws_secret_key:
        client_kwargs = {
            "aws_access_key_id": aws_access_key,
            "aws_secret_access_key": aws_secret_key,
        }

    s3 = boto3.client("s3", **client_kwargs)
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    documents: list[Document] = []
    for obj in response.get("Contents", []):
        key = obj["Key"]
        file_bytes = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        markdown, metadata = process_file(file_bytes, key.rsplit("/", 1)[-1])
        documents.append(
            Document(
                doc_id=hashlib.sha256(f"{tenant_id}:{source_id}:{key}".encode("utf-8")).hexdigest(),
                source_id=source_id,
                tenant_id=tenant_id,
                url=f"s3://{bucket}/{key}",
                title=metadata.get("title", key),
                content_markdown=markdown,
                content_hash=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
                metadata=metadata,
            )
        )
    return documents


async def crawl_azure_blob_container(
    account_url: str,
    container: str,
    prefix: str,
    connection_string: str,
    source_id: str,
    tenant_id: str,
) -> list[Document]:
    """Fetch blobs from Azure Blob Storage and normalize into documents."""
    try:
        from azure.storage.blob import BlobServiceClient
    except Exception as exc:  # pragma: no cover - depends on optional package
        raise RuntimeError("azure-storage-blob package is required for Azure Blob ingestion") from exc

    service = (
        BlobServiceClient.from_connection_string(connection_string)
        if connection_string
        else BlobServiceClient(account_url=account_url)
    )
    container_client = service.get_container_client(container)

    documents: list[Document] = []
    blob_iter = container_client.list_blobs(name_starts_with=prefix or None)
    for blob in blob_iter:
        key = blob.name
        stream = container_client.download_blob(key)
        file_bytes = stream.readall()
        markdown, metadata = process_file(file_bytes, key.rsplit("/", 1)[-1])
        documents.append(
            Document(
                doc_id=hashlib.sha256(f"{tenant_id}:{source_id}:{key}".encode("utf-8")).hexdigest(),
                source_id=source_id,
                tenant_id=tenant_id,
                url=f"azure://{container}/{key}",
                title=metadata.get("title", key),
                content_markdown=markdown,
                content_hash=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
                metadata={**metadata, "provider": "azure_blob"},
            )
        )
    return documents


async def crawl_gcs_bucket(
    bucket: str,
    prefix: str,
    service_account_json: str,
    source_id: str,
    tenant_id: str,
) -> list[Document]:
    """Fetch objects from GCS and normalize into documents."""
    try:
        from google.cloud import storage
        from google.oauth2 import service_account
    except Exception as exc:  # pragma: no cover - depends on optional package
        raise RuntimeError("google-cloud-storage package is required for GCS ingestion") from exc

    credentials = None
    if service_account_json:
        info = json.loads(service_account_json)
        credentials = service_account.Credentials.from_service_account_info(info)
    client = storage.Client(credentials=credentials)

    gcs_bucket = client.bucket(bucket)
    blobs = client.list_blobs(gcs_bucket, prefix=prefix or None)
    documents: list[Document] = []
    for blob in blobs:
        key = blob.name
        buf = io.BytesIO()
        blob.download_to_file(buf)
        file_bytes = buf.getvalue()
        markdown, metadata = process_file(file_bytes, key.rsplit("/", 1)[-1])
        documents.append(
            Document(
                doc_id=hashlib.sha256(f"{tenant_id}:{source_id}:{key}".encode("utf-8")).hexdigest(),
                source_id=source_id,
                tenant_id=tenant_id,
                url=f"gcs://{bucket}/{key}",
                title=metadata.get("title", key),
                content_markdown=markdown,
                content_hash=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
                metadata={**metadata, "provider": "gcs"},
            )
        )
    return documents


async def crawl_cloud_storage(
    provider: str,
    config: dict,
    source_id: str,
    tenant_id: str,
) -> list[Document]:
    """Dispatch cloud ingestion based on provider type."""
    provider = (provider or "s3").lower().strip()
    if provider == "s3":
        return await crawl_s3_bucket(
            bucket=config["bucket"],
            prefix=config.get("prefix", ""),
            aws_access_key=config.get("aws_access_key", ""),
            aws_secret_key=config.get("aws_secret_key", ""),
            source_id=source_id,
            tenant_id=tenant_id,
        )
    if provider == "azure_blob":
        return await crawl_azure_blob_container(
            account_url=config.get("account_url", ""),
            container=config["container"],
            prefix=config.get("prefix", ""),
            connection_string=config.get("connection_string", ""),
            source_id=source_id,
            tenant_id=tenant_id,
        )
    if provider == "gcs":
        return await crawl_gcs_bucket(
            bucket=config["bucket"],
            prefix=config.get("prefix", ""),
            service_account_json=config.get("service_account_json", ""),
            source_id=source_id,
            tenant_id=tenant_id,
        )
    raise ValueError(f"Unsupported cloud storage provider: {provider}")