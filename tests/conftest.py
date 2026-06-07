"""Global pytest fixtures for KnowledgeMCP tests."""

import os
from unittest.mock import MagicMock

import pytest

from src.common.models import (
    Chunk, Document, IndexingStatus, Source, SourceType, Tenant,
)


@pytest.fixture(autouse=True)
def setup_env():
    os.environ.update({
        "BACKEND": "aws",
        "AWS_REGION": "us-east-1",
        "AWS_ACCOUNT_ID": "123456789012",
        "JWT_SECRET_KEY": "test-secret-key",
        "EMBEDDING_PROVIDER": "bedrock",
        "OPENSEARCH_ENDPOINT": "mock://opensearch",
        "TENANTS_TABLE": "test-tenants",
        "SOURCES_TABLE": "test-sources",
        "ANALYTICS_TABLE": "test-analytics",
        "CONTENT_BUCKET": "test-content",
        "CRAWL_QUEUE_URL": "https://sqs.example/crawl",
        "INDEX_QUEUE_URL": "https://sqs.example/index",
    })
    # Clear cached Settings + backend factories so each test re-reads env.
    from src.common.config import get_config
    get_config.cache_clear()
    import src.common.config as _cfg_mod
    _cfg_mod.settings = get_config()
    from src.common.backends.factory import reset_backend_factories
    reset_backend_factories()
    yield
    reset_backend_factories()


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


@pytest.fixture
def fake_tenant_repo(monkeypatch):
    """Drop-in mock for the TenantRepository used by admin/routes and middleware."""
    repo = MagicMock()
    monkeypatch.setattr("src.common.backends.factory.get_tenant_repo", lambda: repo)
    return repo


@pytest.fixture
def fake_source_repo(monkeypatch):
    repo = MagicMock()
    monkeypatch.setattr("src.common.backends.factory.get_source_repo", lambda: repo)
    return repo


@pytest.fixture
def fake_queue(monkeypatch):
    q = MagicMock()
    monkeypatch.setattr("src.common.backends.factory.get_queue", lambda: q)
    return q


@pytest.fixture
def fake_email_sender(monkeypatch):
    sender = MagicMock()
    monkeypatch.setattr("src.common.backends.factory.get_email_sender", lambda: sender)
    return sender


@pytest.fixture
def fake_secret_store(monkeypatch):
    store = MagicMock()
    monkeypatch.setattr("src.common.backends.factory.get_secret_store", lambda: store)
    return store


@pytest.fixture
def fake_analytics_repo(monkeypatch):
    repo = MagicMock()
    monkeypatch.setattr("src.common.backends.factory.get_analytics_repo", lambda: repo)
    return repo
