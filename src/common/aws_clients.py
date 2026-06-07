"""Boto3 client factory with cached singletons for KnowledgeMCP."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

from src.common.config import get_config

if TYPE_CHECKING:
    from mypy_boto3_bedrock_runtime import BedrockRuntimeClient
    from mypy_boto3_dynamodb import DynamoDBServiceResource
    from mypy_boto3_s3 import S3Client
    from mypy_boto3_ses import SESClient
    from mypy_boto3_secretsmanager import SecretsManagerClient
    from mypy_boto3_sqs import SQSClient


@lru_cache(maxsize=1)
def get_dynamodb_resource() -> DynamoDBServiceResource:
    """Return a cached DynamoDB resource."""
    cfg = get_config()
    return boto3.resource("dynamodb", region_name=cfg.aws_region)


@lru_cache(maxsize=1)
def get_s3_client() -> S3Client:
    """Return a cached S3 client."""
    cfg = get_config()
    return boto3.client("s3", region_name=cfg.aws_region)


@lru_cache(maxsize=1)
def get_sqs_client() -> SQSClient:
    """Return a cached SQS client."""
    cfg = get_config()
    return boto3.client("sqs", region_name=cfg.aws_region)


@lru_cache(maxsize=1)
def get_ses_client() -> SESClient:
    """Return a cached SES client."""
    cfg = get_config()
    return boto3.client("ses", region_name=cfg.aws_region)


@lru_cache(maxsize=1)
def get_secretsmanager_client() -> SecretsManagerClient:
    """Return a cached Secrets Manager client."""
    cfg = get_config()
    return boto3.client("secretsmanager", region_name=cfg.aws_region)


@lru_cache(maxsize=1)
def get_bedrock_client() -> BedrockRuntimeClient:
    """Return a cached Bedrock Runtime client."""
    cfg = get_config()
    return boto3.client("bedrock-runtime", region_name=cfg.aws_region)


@lru_cache(maxsize=1)
def get_opensearch_client() -> OpenSearch:
    """Return a cached OpenSearch client.

    Modes (auto-detected):
      - BACKEND=local + http:// endpoint -> no auth, no TLS (docker compose)
      - OPENSEARCH_MASTER_USER set       -> managed OpenSearch with basic auth
      - otherwise                        -> AOSS serverless with SigV4 IAM auth
    """
    import os

    cfg = get_config()
    if cfg.backend == "local" and cfg.opensearch_endpoint.startswith("http://"):
        from urllib.parse import urlparse
        parsed = urlparse(cfg.opensearch_endpoint)
        host = parsed.hostname or "opensearch"
        port = parsed.port or 9200
        return OpenSearch(
            hosts=[{"host": host, "port": port}],
            use_ssl=False,
            verify_certs=False,
            connection_class=RequestsHttpConnection,
        )

    master_user = os.environ.get("OPENSEARCH_MASTER_USER", "")
    master_pass = os.environ.get("OPENSEARCH_MASTER_PASSWORD", "")

    host = cfg.opensearch_endpoint.replace("https://", "").replace("http://", "").rstrip("/")

    if master_user and master_pass:
        # Managed OpenSearch with fine-grained access control (basic auth)
        return OpenSearch(
            hosts=[{"host": host, "port": 443}],
            http_auth=(master_user, master_pass),
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
        )

    # Fallback: AOSS (serverless) with IAM auth
    session = boto3.Session(region_name=cfg.aws_region)
    credentials = session.get_credentials()
    awsauth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        cfg.aws_region,
        "aoss",
        session_token=credentials.token,
    )
    return OpenSearch(
        hosts=[{"host": host, "port": 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )
