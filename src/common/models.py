"""Pydantic data models for KnowledgeMCP."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    WEBSITE_URL = "website_url"
    FILE_UPLOAD = "file_upload"
    CLOUD_STORAGE = "cloud_storage"
    WIKI_KB = "wiki_kb"
    GIT_REPO = "git_repo"
    PASTE_TEXT = "paste_text"


class IndexingStatus(str, Enum):
    PENDING = "pending"
    CRAWLING = "crawling"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


class Tenant(BaseModel):
    tenant_id: str
    slug: str
    name: str
    email: str
    password_hash: str
    api_key: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    max_docs: int = 500
    max_queries_per_hour: int = 100


class Source(BaseModel):
    source_id: str
    tenant_id: str
    source_type: SourceType
    name: str
    config: dict  # source-type-specific config (url, bucket, credentials, etc.)
    status: IndexingStatus = IndexingStatus.PENDING
    doc_count: int = 0
    last_sync: Optional[datetime] = None
    sync_schedule: str = "manual"  # manual, hourly, daily, weekly
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CrawlJob(BaseModel):
    tenant_id: str
    source_id: str
    source_type: SourceType
    config: dict = Field(default_factory=dict)
    action: str = "crawl"
    submitted_at: datetime = Field(default_factory=datetime.utcnow)


class Document(BaseModel):
    doc_id: str
    source_id: str
    tenant_id: str
    url: Optional[str] = None
    title: str
    content_markdown: str
    metadata: dict = Field(default_factory=dict)
    content_hash: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    tenant_id: str
    source_id: str = ""
    content: str
    token_count: int
    embedding: Optional[list[float]] = None
    title: str = ""
    url: Optional[str] = None
    section: str = ""
    metadata: dict = Field(default_factory=dict)  # title, url, section, breadcrumb
    is_code: bool = False
    code_language: Optional[str] = None


class SearchResult(BaseModel):
    chunk_id: str
    title: str
    url: Optional[str]
    excerpt: str
    score: float
    metadata: dict = Field(default_factory=dict)


class CodeSearchResult(BaseModel):
    chunk_id: str
    code: str
    language: str
    context: str
    title: str
    url: Optional[str]
    score: float


class QueryLog(BaseModel):
    tenant_id: str
    tool_name: str
    query: str
    results_count: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    latency_ms: int = 0
