"""Global pytest fixtures for KnowledgeMCP tests."""

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.common.models import (
    Tenant, Source, Document, Chunk, SourceType, IndexingStatus,
)


@pytest.fixture(autouse=True)
def setup_env():
    os.environ.update({
        "AWS_REGION": "us-east-1",
        "AWS_ACCOUNT_ID": "123456789012",
        "JWT_SECRET_KEY": "test-secret-key",
        "EMBEDDING_PROVIDER": "bedrock",
        "OPENSEARCH_ENDPOINT": "mock://opensearch",
        "TENANTS_TABLE": "test-tenants",
        "SOURCES_TABLE": "test-sources",
        "ANALYTICS_TABLE": "test-analytics",
        "CONTENT_BUCKET": "test-content",
        "CRAWL_QUEUE_URL": "",
        "INDEX_QUEUE_URL": "",
    })
    # Clear cached Settings so tests pick up the env vars set above.
    from src.common.config import get_config
    get_config.cache_clear()
    import src.common.config as _cfg_mod
    _cfg_mod.settings = get_config()
    yield


@pytest.fixture
def test_tenant():
    return Tenant(
        tenant_id="test-tenant-001", slug="test-tenant", name="Test Tenant",
        email="test@example.com", password_hash="hashed", api_key="test_api_key_123",
    )


@pytest.fixture
def test_source(test_tenant):
    return Source(
        source_id="source-001", tenant_id=test_tenant.tenant_id,
        source_type=SourceType.WEBSITE_URL, name="Test Docs",
        config={"url": "https://example.com"}, status=IndexingStatus.READY, doc_count=5,
    )


@pytest.fixture
def test_document(test_source):
    return Document(
        doc_id="doc-001", source_id=test_source.source_id, tenant_id=test_source.tenant_id,
        url="https://example.com/api", title="API Docs",
        content_markdown="# API\n\n## GET /users\n\nFetch users.",
        metadata={"title": "API Docs", "url": "https://example.com/api", "source_id": test_source.source_id},
        content_hash="abc123",
    )


@pytest.fixture
def test_chunk(test_document):
    return Chunk(
        chunk_id="chunk-001", doc_id=test_document.doc_id, tenant_id=test_document.tenant_id,
        source_id=test_document.source_id, content="API Reference\n\nGET /users",
        token_count=15, embedding=[0.1] * 1024, title="API Docs",
        url=test_document.url, section="GET /users",
    )


@pytest.fixture
def test_html():
    return """<html><head><title>Example Page</title>
    <meta name="description" content="Test page"></head>
    <body><header>Nav</header><main><h1>Main</h1><p>Content</p></main><footer>Foot</footer></body></html>"""


@pytest.fixture
def test_markdown_with_code():
    return """# Tutorial\n\nHere's code:\n\n```python\ndef hello():\n    print("hi")\n```\n\nAnd JS:\n\n```javascript\nconsole.log("hi");\n```\n"""
