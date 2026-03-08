"""Tests for retrieval service."""

import pytest
from unittest.mock import patch, AsyncMock
from src.mcp_server.retrieval import search_docs, search_code, fetch_page
from src.common.models import SearchResult, CodeSearchResult


class TestSearchDocs:
    @pytest.mark.asyncio
    async def test_returns_results(self, test_tenant):
        hits = [{"chunk_id": "c1", "title": "T", "url": "u", "excerpt": "e", "score": 0.9, "metadata": {}}]
        with patch("src.mcp_server.retrieval.embed_single", new_callable=AsyncMock, return_value=[0.1]*1024):
            with patch("src.mcp_server.retrieval.hybrid_search", new_callable=AsyncMock, return_value=hits):
                results = await search_docs(test_tenant.tenant_id, "q")
                assert len(results) == 1
                assert isinstance(results[0], SearchResult)

    @pytest.mark.asyncio
    async def test_empty(self, test_tenant):
        with patch("src.mcp_server.retrieval.embed_single", new_callable=AsyncMock, return_value=[0.1]*1024):
            with patch("src.mcp_server.retrieval.hybrid_search", new_callable=AsyncMock, return_value=[]):
                results = await search_docs(test_tenant.tenant_id, "nothing")
                assert results == []


class TestSearchCode:
    @pytest.mark.asyncio
    async def test_returns_code(self, test_tenant):
        hits = [{"chunk_id": "c1", "title": "T", "url": "u", "content": "def f(): pass", "code_language": "python", "section": "S", "score": 0.8}]
        with patch("src.mcp_server.retrieval.embed_single", new_callable=AsyncMock, return_value=[0.1]*1024):
            with patch("src.mcp_server.retrieval.hybrid_search", new_callable=AsyncMock, return_value=hits):
                results = await search_code(test_tenant.tenant_id, "q")
                assert len(results) == 1
                assert isinstance(results[0], CodeSearchResult)

    @pytest.mark.asyncio
    async def test_language_filter(self, test_tenant):
        hits = [
            {"chunk_id": "c1", "title": "T", "url": "u", "content": "x", "code_language": "python", "section": "", "score": 0.8},
            {"chunk_id": "c2", "title": "T", "url": "u", "content": "y", "code_language": "javascript", "section": "", "score": 0.7},
        ]
        with patch("src.mcp_server.retrieval.embed_single", new_callable=AsyncMock, return_value=[0.1]*1024):
            with patch("src.mcp_server.retrieval.hybrid_search", new_callable=AsyncMock, return_value=hits):
                results = await search_code(test_tenant.tenant_id, "q", language="python")
                assert len(results) == 1
                assert results[0].language == "python"


class TestFetchPage:
    @pytest.mark.asyncio
    async def test_returns_cached(self, test_tenant):
        with patch("src.mcp_server.retrieval.get_document_by_url", new_callable=AsyncMock, return_value="# Cached"):
            result = await fetch_page(test_tenant.tenant_id, "https://x.com/a")
            assert result == "# Cached"

    @pytest.mark.asyncio
    async def test_live_fetch_fallback(self, test_tenant):
        with patch("src.mcp_server.retrieval.get_document_by_url", new_callable=AsyncMock, return_value=None):
            with patch("src.mcp_server.retrieval.httpx.AsyncClient") as mock_client_cls:
                mock_resp = AsyncMock()
                mock_resp.text = "<p>Live</p>"
                mock_resp.raise_for_status = lambda: None
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_resp)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=False)
                mock_client_cls.return_value = mock_client
                result = await fetch_page(test_tenant.tenant_id, "https://x.com/b")
                assert isinstance(result, str)
