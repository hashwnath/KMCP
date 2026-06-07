"""OpenSearch index management and hybrid search."""

import asyncio
import logging
from typing import Any, Optional

from opensearchpy import OpenSearch, helpers

from src.common.aws_clients import get_opensearch_client
from src.common.config import get_config
from src.common.models import Chunk
from src.indexer.embedder import current_provider_identity

logger = logging.getLogger(__name__)


# Hybrid search weights
_BM25_WEIGHT = 0.4
_VECTOR_WEIGHT = 0.6


def _index_body(dim: int) -> dict[str, Any]:
    return {
        "settings": {
            "index": {
                "knn": True,
                "knn.algo_param.ef_search": 100,
            },
        },
        "mappings": {
            "_meta": {
                "embedding_provider": "",  # filled in by ensure_index
                "embedding_model": "",
                "embedding_dim": dim,
            },
            "properties": {
                "tenant_id": {"type": "keyword"},
                "source_id": {"type": "keyword"},
                "doc_id": {"type": "keyword"},
                "chunk_id": {"type": "keyword"},
                "content": {"type": "text", "analyzer": "standard"},
                "title": {"type": "text"},
                "url": {"type": "keyword"},
                "section": {"type": "text"},
                "metadata": {
                    "type": "object",
                    "properties": {
                        "chunk_index": {"type": "integer"},
                        "total_chunks": {"type": "integer"},
                    },
                },
                "embedding": {
                    "type": "knn_vector",
                    "dimension": dim,
                    "method": {
                        "name": "hnsw",
                        "engine": "lucene",
                        "space_type": "cosinesimil",
                    },
                },
                "is_code": {"type": "boolean"},
                "code_language": {"type": "keyword"},
                "token_count": {"type": "integer"},
            },
        },
    }


def _index_name(tenant_id: str) -> str:
    return f"knowledgemcp-{tenant_id}"


def _get_client() -> OpenSearch:
    return get_opensearch_client()


# ---------------------------------------------------------------------------
# Index lifecycle
# ---------------------------------------------------------------------------

class IndexProviderMismatch(RuntimeError):
    """Raised when the configured embedding provider/dim doesn't match the
    provider/dim that the existing tenant index was created with."""


def ensure_index(tenant_id: str) -> None:
    """Create the tenant index if missing; verify provider/dim if it exists."""
    client = _get_client()
    name = _index_name(tenant_id)
    provider, model, dim = current_provider_identity()

    if client.indices.exists(index=name):
        # Verify dim + provider via either the lucene knn_vector mapping or
        # the persisted _meta block.
        existing = client.indices.get(index=name).get(name, {})
        mappings = existing.get("mappings", {})
        existing_meta = mappings.get("_meta", {}) or {}
        existing_dim = (
            existing_meta.get("embedding_dim")
            or mappings.get("properties", {}).get("embedding", {}).get("dimension")
        )
        if existing_dim and int(existing_dim) != int(dim):
            raise IndexProviderMismatch(
                f"Index {name} was created with dim={existing_dim} but the "
                f"current EMBEDDING_PROVIDER={provider} produces dim={dim}. "
                "Changing embedding providers requires re-creating the index. "
                "Set BACKEND back to the original provider, or delete the "
                "index and re-crawl all sources."
            )
        existing_provider = existing_meta.get("embedding_provider")
        if existing_provider and existing_provider != provider:
            logger.warning(
                "Index %s was created with provider=%s but current is %s "
                "(dim matches). Continuing but be aware results may degrade.",
                name, existing_provider, provider,
            )
        return

    body = _index_body(dim)
    body["mappings"]["_meta"]["embedding_provider"] = provider
    body["mappings"]["_meta"]["embedding_model"] = model
    client.indices.create(index=name, body=body)
    logger.info(
        "Created index %s (provider=%s model=%s dim=%d)",
        name, provider, model, dim,
    )


def delete_tenant_index(tenant_id: str) -> None:
    client = _get_client()
    name = _index_name(tenant_id)
    if client.indices.exists(index=name):
        client.indices.delete(index=name)
        logger.info("Deleted index %s", name)
    else:
        logger.warning("Index %s does not exist; nothing to delete", name)


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------

def _chunk_to_doc(chunk: Chunk) -> dict[str, Any]:
    return {
        "tenant_id": chunk.tenant_id,
        "source_id": chunk.source_id,
        "doc_id": chunk.doc_id,
        "chunk_id": chunk.chunk_id,
        "content": chunk.content,
        "title": chunk.title,
        "url": chunk.url,
        "section": chunk.section,
        "metadata": chunk.metadata,
        "embedding": chunk.embedding,
        "is_code": chunk.is_code,
        "code_language": chunk.code_language,
        "token_count": chunk.token_count,
    }


def index_chunks(tenant_id: str, chunks: list[Chunk]) -> int:
    ensure_index(tenant_id)
    client = _get_client()
    name = _index_name(tenant_id)

    actions = []
    for chunk in chunks:
        if not chunk.embedding:
            logger.warning("Skipping chunk %s — no embedding", chunk.chunk_id)
            continue
        actions.append({
            "_index": name,
            "_id": chunk.chunk_id,
            "_source": _chunk_to_doc(chunk),
        })

    if not actions:
        logger.warning("No valid chunks to index for tenant %s", tenant_id)
        return 0

    success, errors = helpers.bulk(client, actions, raise_on_error=False)
    if errors:
        logger.error("Bulk index errors for %s: %s", tenant_id, errors)
    logger.info("Indexed %d/%d chunks for tenant %s", success, len(actions), tenant_id)
    return success


def delete_source_documents(tenant_id: str, source_id: str) -> int:
    client = _get_client()
    name = _index_name(tenant_id)
    if not client.indices.exists(index=name):
        return 0
    response = client.delete_by_query(
        index=name,
        body={"query": {"term": {"source_id": source_id}}},
        refresh=True,
    )
    return response.get("deleted", 0)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

async def hybrid_search(
    tenant_id: str,
    query: str,
    query_embedding: list[float],
    top_k: int = 10,
    code_only: bool = False,
) -> list[dict]:
    client = _get_client()
    name = _index_name(tenant_id)
    if not client.indices.exists(index=name):
        logger.warning("Index %s does not exist", name)
        return []

    must_clauses: list[dict] = [
        {"multi_match": {"query": query, "fields": ["content", "title", "section"]}},
    ]
    if code_only:
        must_clauses.append({"term": {"is_code": True}})

    body: dict[str, Any] = {
        "size": top_k,
        "query": {
            "script_score": {
                "query": {"bool": {"must": must_clauses}},
                "script": {
                    "source": (
                        f"_score * {_BM25_WEIGHT} + "
                        f"{_VECTOR_WEIGHT} * cosineSimilarity(params.query_vector, 'embedding') + 1.0"
                    ),
                    "params": {"query_vector": query_embedding},
                },
            },
        },
    }
    response = await asyncio.to_thread(client.search, index=name, body=body)
    hits = response.get("hits", {}).get("hits", [])
    return [
        {
            "chunk_id": h["_source"].get("chunk_id"),
            "content": h["_source"].get("content"),
            "embedding": h["_source"].get("embedding", []),
            "title": h["_source"].get("title"),
            "url": h["_source"].get("url"),
            "section": h["_source"].get("section"),
            "is_code": h["_source"].get("is_code", False),
            "code_language": h["_source"].get("code_language", ""),
            "score": h.get("_score", 0.0),
            "metadata": h["_source"].get("metadata", {}),
        }
        for h in hits
    ]


# ---------------------------------------------------------------------------
# Document fetch
# ---------------------------------------------------------------------------

async def get_document_by_url(tenant_id: str, url: str) -> Optional[str]:
    client = _get_client()
    name = _index_name(tenant_id)
    if not client.indices.exists(index=name):
        return None

    body: dict[str, Any] = {
        "size": 200,
        "query": {"bool": {"must": [{"term": {"url": url}}]}},
        "sort": [{"metadata.chunk_index": {"order": "asc", "unmapped_type": "integer"}}],
    }
    response = await asyncio.to_thread(client.search, index=name, body=body)
    hits = response.get("hits", {}).get("hits", [])
    if not hits:
        return None
    return "\n\n".join(h["_source"]["content"] for h in hits)
