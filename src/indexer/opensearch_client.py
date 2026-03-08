"""OpenSearch index management and search.

Manages per-tenant indexes in OpenSearch, handles bulk indexing of
document/code chunks with kNN vectors, and provides hybrid search
(BM25 + kNN vector similarity).

Index naming: ``knowledgemcp-{tenant_id}``
"""

import logging
import asyncio
from typing import Any, Optional

from opensearchpy import OpenSearch, helpers

from src.common.aws_clients import get_opensearch_client
from src.common.config import get_config
from src.common.models import Chunk

logger = logging.getLogger(__name__)

config = get_config()

# Embedding dimension for Titan Embed v2 / OpenAI text-embedding-3-small
_EMBEDDING_DIM = 1024

# Hybrid search weights
_BM25_WEIGHT = 0.4
_VECTOR_WEIGHT = 0.6

# ── Index schema ──────────────────────────────────────────────────────────

_INDEX_BODY: dict[str, Any] = {
    "settings": {
        "index": {
            "knn": True,
            "knn.algo_param.ef_search": 100,
        },
    },
    "mappings": {
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
                "dimension": _EMBEDDING_DIM,
                "method": {
                    "name": "hnsw",
                    "engine": "nmslib",
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
    """Derive the OpenSearch index name for a tenant."""
    return f"knowledgemcp-{tenant_id}"


def _get_client() -> OpenSearch:
    return get_opensearch_client()


# ── Index lifecycle ───────────────────────────────────────────────────────


def ensure_index(tenant_id: str) -> None:
    """Create the tenant index if it does not already exist."""
    client = _get_client()
    name = _index_name(tenant_id)

    if client.indices.exists(index=name):
        logger.info("Index %s already exists", name)
        return

    client.indices.create(index=name, body=_INDEX_BODY)
    logger.info("Created index %s", name)


def delete_tenant_index(tenant_id: str) -> None:
    """Delete a tenant's entire search index."""
    client = _get_client()
    name = _index_name(tenant_id)

    if client.indices.exists(index=name):
        client.indices.delete(index=name)
        logger.info("Deleted index %s", name)
    else:
        logger.warning("Index %s does not exist; nothing to delete", name)


# ── Indexing ──────────────────────────────────────────────────────────────


def _chunk_to_doc(chunk: Chunk) -> dict[str, Any]:
    """Convert a Chunk model to an OpenSearch document dict."""
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
    """Bulk-index chunks into the tenant's OpenSearch index.

    Creates the index if it doesn't exist. Skips chunks without
    embeddings. Returns the number of successfully indexed chunks.
    """
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

    success_count, errors = helpers.bulk(client, actions, raise_on_error=False)

    if errors:
        logger.error("Bulk index errors for %s: %s", tenant_id, errors)

    logger.info("Indexed %d/%d chunks for tenant %s", success_count, len(actions), tenant_id)
    return success_count


def delete_source_documents(tenant_id: str, source_id: str) -> int:
    """Remove all indexed chunks for a source from a tenant index."""
    client = _get_client()
    name = _index_name(tenant_id)

    if not client.indices.exists(index=name):
        return 0

    response = client.delete_by_query(
        index=name,
        body={
            "query": {
                "term": {
                    "source_id": source_id,
                }
            }
        },
        refresh=True,
    )
    return response.get("deleted", 0)


# ── Search ────────────────────────────────────────────────────────────────


async def hybrid_search(
    tenant_id: str,
    query: str,
    query_embedding: list[float],
    top_k: int = 10,
    code_only: bool = False,
) -> list[dict]:
    """Hybrid BM25 + kNN search across a tenant's index.

    Uses OpenSearch's ``script_score`` query to combine BM25 relevance
    with cosine similarity on the kNN vector.

    Weights: 0.4 BM25 + 0.6 vector.

    Args:
        tenant_id: Tenant whose index to search.
        query: Text query for BM25 matching.
        query_embedding: Vector for kNN similarity.
        top_k: Number of results to return.
        code_only: If True, restrict to code chunks only.

    Returns:
        List of hit dicts, each with ``_source`` and ``_score``.
    """
    client = _get_client()
    name = _index_name(tenant_id)

    if not client.indices.exists(index=name):
        logger.warning("Index %s does not exist", name)
        return []

    # Build the BM25 filter
    must_clauses: list[dict] = [
        {"multi_match": {"query": query, "fields": ["content", "title", "section"]}},
    ]
    if code_only:
        must_clauses.append({"term": {"is_code": True}})

    search_body: dict[str, Any] = {
        "size": top_k,
        "query": {
            "script_score": {
                "query": {
                    "bool": {
                        "must": must_clauses,
                    },
                },
                "script": {
                    "source": (
                        f"_score * {_BM25_WEIGHT} + "
                        f"{_VECTOR_WEIGHT} * cosineSimilarity(params.query_vector, 'embedding') + 1.0"
                    ),
                    "params": {
                        "query_vector": query_embedding,
                    },
                },
            },
        },
    }

    response = await asyncio.to_thread(client.search, index=name, body=search_body)
    hits = response.get("hits", {}).get("hits", [])

    results = []
    for hit in hits:
        results.append({
            "chunk_id": hit["_source"].get("chunk_id"),
            "content": hit["_source"].get("content"),
            "embedding": hit["_source"].get("embedding", []),
            "title": hit["_source"].get("title"),
            "url": hit["_source"].get("url"),
            "section": hit["_source"].get("section"),
            "is_code": hit["_source"].get("is_code", False),
            "code_language": hit["_source"].get("code_language", ""),
            "score": hit.get("_score", 0.0),
            "metadata": hit["_source"].get("metadata", {}),
        })

    return results


# ── Document fetch ────────────────────────────────────────────────────────


async def get_document_by_url(tenant_id: str, url: str) -> Optional[str]:
    """Fetch all chunks for a given URL and concatenate into full content.

    Used by the ``docs_fetch`` MCP tool to return complete page content.

    Returns:
        Concatenated markdown string, or None if no chunks found.
    """
    client = _get_client()
    name = _index_name(tenant_id)

    if not client.indices.exists(index=name):
        return None

    search_body: dict[str, Any] = {
        "size": 200,
        "query": {
            "bool": {
                "must": [{"term": {"url": url}}],
            },
        },
        "sort": [{"metadata.chunk_index": {"order": "asc", "unmapped_type": "integer"}}],
    }

    response = await asyncio.to_thread(client.search, index=name, body=search_body)
    hits = response.get("hits", {}).get("hits", [])

    if not hits:
        return None

    parts = [hit["_source"]["content"] for hit in hits]
    return "\n\n".join(parts)
