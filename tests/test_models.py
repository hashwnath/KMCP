"""Tests for pydantic data models."""

from src.common.models import (
    Tenant, Source, Document, Chunk, CrawlJob,
    SearchResult, CodeSearchResult, QueryLog,
    SourceType, IndexingStatus,
)


class TestModels:
    def test_tenant_creation(self):
        t = Tenant(tenant_id="t1", slug="s", name="N", email="e@e.c", password_hash="h", api_key="k")
        assert t.tenant_id == "t1"

    def test_source_defaults(self):
        s = Source(source_id="s1", tenant_id="t1", source_type=SourceType.WEBSITE_URL, name="n", config={})
        assert s.status == IndexingStatus.PENDING
        assert s.sync_schedule == "manual"

    def test_crawl_job(self):
        j = CrawlJob(tenant_id="t1", source_id="s1", source_type=SourceType.PASTE_TEXT)
        assert j.action == "crawl"

    def test_chunk_has_source_id(self):
        c = Chunk(chunk_id="c1", doc_id="d1", tenant_id="t1", source_id="s1", content="x", token_count=1)
        assert c.source_id == "s1"

    def test_search_result(self):
        r = SearchResult(chunk_id="c1", title="t", url=None, excerpt="e", score=0.9)
        assert r.score == 0.9

    def test_code_search_result(self):
        r = CodeSearchResult(chunk_id="c1", code="x", language="py", context="c", title="t", url=None, score=0.8)
        assert r.language == "py"
