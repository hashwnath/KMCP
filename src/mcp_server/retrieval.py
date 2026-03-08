"""High-level retrieval service: query expansion -> hybrid search -> re-rank -> dedup -> format.

Implements the full 3-phase RAG pipeline from the architecture doc:
  1. Pre-retrieval: query expansion
  2. Retrieval: hybrid BM25 + vector search
  3. Post-retrieval: MMR re-ranking, dedup, token-bounded excerpts
"""

from __future__ import annotations

import httpx

from src.common.models import CodeSearchResult, SearchResult
from src.common.tokenizer import encode as _encode, decode as _decode
from src.indexer.embedder import embed_single
from src.indexer.html_to_markdown import html_to_markdown
from src.indexer.opensearch_client import get_document_by_url, hybrid_search

_MAX_EXCERPT_TOKENS = 500


def _truncate_to_tokens(text: str, max_tokens: int = _MAX_EXCERPT_TOKENS) -> str:
    """Token-bounded truncation (MS Learn contract: ~500 tokens per excerpt)."""
    tokens = _encode(text)
    if len(tokens) <= max_tokens:
        return text
    return _decode(tokens[:max_tokens]) + "..."


# ---------------------------------------------------------------------------
# Pre-retrieval: query expansion
# ---------------------------------------------------------------------------

def _expand_query(query: str) -> list[str]:
    """Generate lightweight query variants for better recall.

    Rule-based expander. A production system could use an LLM for rewriting,
    but this avoids extra API calls and covers common agent query patterns.
    """
    variants = [query]
    q_lower = query.lower()

    for prefix in ("how to ", "how do i ", "what is ", "what are ", "explain "):
        if q_lower.startswith(prefix):
            variants.append(query[len(prefix):])
            break

    if any(kw in q_lower for kw in ("implement", "configure", "setup", "install", "create")):
        variants.append(f"{query} example")

    return variants


# ---------------------------------------------------------------------------
# Post-retrieval: MMR re-ranking
# ---------------------------------------------------------------------------

def _cosine_sim(a: list[float], b: list[float]) -> float:
    """Dot-product cosine similarity (vectors assumed unit-normalized by HNSW)."""
    return sum(x * y for x, y in zip(a, b))


def _mmr_rerank(
    hits: list[dict],
    query_embedding: list[float],
    top_k: int = 10,
    lambda_param: float = 0.7,
) -> list[dict]:
    """Maximal Marginal Relevance re-ranking.

    Balances relevance to query (lambda) vs diversity among selected (1 - lambda).
    Prevents returning 5 overlapping chunks from the same section.
    """
    if len(hits) <= top_k:
        return hits

    selected: list[dict] = []
    remaining = list(hits)

    while remaining and len(selected) < top_k:
        best_idx = 0
        best_score = float("-inf")

        for i, candidate in enumerate(remaining):
            relevance = candidate.get("score", 0.0)

            max_sim = 0.0
            cand_emb = candidate.get("embedding", [])
            if selected and cand_emb:
                for sel in selected:
                    sel_emb = sel.get("embedding", [])
                    if sel_emb:
                        max_sim = max(max_sim, _cosine_sim(cand_emb, sel_emb))

            mmr = lambda_param * relevance - (1 - lambda_param) * max_sim
            if mmr > best_score:
                best_score = mmr
                best_idx = i

        selected.append(remaining.pop(best_idx))

    return selected


# ---------------------------------------------------------------------------
# Post-retrieval: URL-level dedup
# ---------------------------------------------------------------------------

def _dedup_by_url(hits: list[dict]) -> list[dict]:
    """Keep only the highest-scoring chunk per URL."""
    seen: dict[str, dict] = {}
    for hit in hits:
        url = hit.get("url") or hit.get("chunk_id")
        if url not in seen or hit.get("score", 0) > seen[url].get("score", 0):
            seen[url] = hit
    return list(seen.values())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def search_docs(
    tenant_id: str,
    query: str,
    top_k: int = 10,
) -> list[SearchResult]:
    """Full 3-phase pipeline: expand -> hybrid search -> MMR re-rank -> dedup -> truncate."""
    query_embedding = await embed_single(query)
    variants = _expand_query(query)

    all_hits: list[dict] = []
    seen_chunk_ids: set[str] = set()

    for variant in variants:
        var_emb = query_embedding if variant == query else await embed_single(variant)
        hits = await hybrid_search(
            tenant_id=tenant_id,
            query=variant,
            query_embedding=var_emb,
            top_k=top_k * 2,
        )
        for hit in hits:
            cid = hit["chunk_id"]
            if cid not in seen_chunk_ids:
                seen_chunk_ids.add(cid)
                all_hits.append(hit)

    reranked = _mmr_rerank(all_hits, query_embedding, top_k=top_k * 2)
    deduped = _dedup_by_url(reranked)
    final = sorted(deduped, key=lambda h: h.get("score", 0), reverse=True)[:top_k]

    return [
        SearchResult(
            chunk_id=hit["chunk_id"],
            title=hit.get("title", ""),
            url=hit.get("url"),
            excerpt=_truncate_to_tokens(hit.get("content", ""), _MAX_EXCERPT_TOKENS),
            score=hit.get("score", 0.0),
            metadata=hit.get("metadata", {}),
        )
        for hit in final
    ]


async def search_code(
    tenant_id: str,
    query: str,
    language: str = "",
    top_k: int = 20,
) -> list[CodeSearchResult]:
    """Code-specific retrieval pipeline with dedup."""
    query_embedding = await embed_single(query)

    raw_hits = await hybrid_search(
        tenant_id=tenant_id,
        query=query,
        query_embedding=query_embedding,
        top_k=top_k * 2,
        code_only=True,
    )

    deduped = _dedup_by_url(raw_hits)
    final = sorted(deduped, key=lambda h: h.get("score", 0), reverse=True)[:top_k]

    results = [
        CodeSearchResult(
            chunk_id=hit["chunk_id"],
            title=hit.get("title", ""),
            url=hit.get("url"),
            code=hit["content"],
            language=hit.get("code_language", "text"),
            context=hit.get("section", ""),
            score=hit["score"],
        )
        for hit in final
    ]

    if language:
        lang_lower = language.lower().strip()
        results = [r for r in results if r.language.lower() == lang_lower]

    return results


async def fetch_page(tenant_id: str, url: str) -> str:
    """Fetch full page content, with cache fallback to live fetch."""
    cached = await get_document_by_url(tenant_id, url)
    if cached:
        return cached

    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={"User-Agent": "KnowledgeMCP/1.0"},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    return html_to_markdown(response.text)
