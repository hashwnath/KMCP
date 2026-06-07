"""Embedding generation for document chunks.

Supports three providers:
  - bedrock: Amazon Titan Embed v2 (1024 dim) — AWS-only
  - openai:  text-embedding-3-small (1536 dim) — external API
  - local:   fastembed (default BAAI/bge-small-en-v1.5, 384 dim) — zero-cost

Provider is selected via EMBEDDING_PROVIDER. Local mode is the OSS default.
"""

import asyncio
import json
import logging
from typing import Callable

import boto3
import httpx

from src.common.config import get_config
from src.common.models import Chunk

logger = logging.getLogger(__name__)

# Dim per provider — kept in sync with opensearch_client._EMBEDDING_DIMS
_KNOWN_DIMS: dict[str, int] = {"bedrock": 1024, "openai": 1536}


# ---------------------------------------------------------------------------
# Bedrock
# ---------------------------------------------------------------------------

def _get_bedrock_client():
    return boto3.client("bedrock-runtime", region_name=get_config().aws_region)


def embed_text_bedrock(text: str, client) -> list[float]:
    response = client.invoke_model(
        modelId=get_config().bedrock_model_id,
        body=json.dumps({"inputText": text}),
    )
    return json.loads(response["body"].read())["embedding"]


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------

def embed_text_openai(text: str, api_key: str) -> list[float]:
    resp = httpx.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": "text-embedding-3-small", "input": text},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


# ---------------------------------------------------------------------------
# Local — fastembed (ONNX, no PyTorch dependency)
# ---------------------------------------------------------------------------

_LOCAL_MODEL_CACHE: dict = {}


def _get_fastembed_model():
    """Singleton fastembed model loader. ~30MB download on first call."""
    cfg = get_config()
    model_name = cfg.local_embedding_model
    cache_key = model_name
    if cache_key not in _LOCAL_MODEL_CACHE:
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:
            raise RuntimeError(
                "EMBEDDING_PROVIDER=local requires the 'fastembed' package. "
                "Install with: pip install fastembed"
            ) from exc
        cache_dir = None
        # Allow override via env so docker can mount a named volume.
        if cfg.local_data_dir:
            from pathlib import Path
            cache_dir = str(Path(cfg.local_data_dir).expanduser() / "model_cache")
        logger.info("Loading fastembed model %s (cache=%s)", model_name, cache_dir)
        _LOCAL_MODEL_CACHE[cache_key] = TextEmbedding(
            model_name=model_name,
            cache_dir=cache_dir,
        )
    return _LOCAL_MODEL_CACHE[cache_key]


def embed_text_local(text: str) -> list[float]:
    model = _get_fastembed_model()
    vectors = list(model.embed([text]))
    if not vectors:
        return []
    vec = vectors[0]
    return vec.tolist() if hasattr(vec, "tolist") else list(vec)


def embed_batch_local(texts: list[str]) -> list[list[float]]:
    model = _get_fastembed_model()
    out: list[list[float]] = []
    for vec in model.embed(texts):
        out.append(vec.tolist() if hasattr(vec, "tolist") else list(vec))
    return out


# ---------------------------------------------------------------------------
# Provider/model identity (used by opensearch_client for the safety check)
# ---------------------------------------------------------------------------

def current_provider_identity() -> tuple[str, str, int]:
    """Return (provider, model_name, embedding_dim) for the current config."""
    cfg = get_config()
    provider = cfg.embedding_provider.lower()
    if provider == "bedrock":
        return ("bedrock", cfg.bedrock_model_id, _KNOWN_DIMS["bedrock"])
    if provider == "openai":
        return ("openai", "text-embedding-3-small", _KNOWN_DIMS["openai"])
    if provider == "local":
        model_name = cfg.local_embedding_model
        # Load model so we can read its real dimension. fastembed's
        # _model_description.dim is reliable; fall back to 384 (bge-small).
        try:
            model = _get_fastembed_model()
            dim = int(model._model_description.dim)
        except Exception:
            dim = 384
        return ("local", model_name, dim)
    raise ValueError(f"Unknown embedding provider: {provider!r}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def embed_single(text: str) -> list[float]:
    """Embed a single text string using the configured provider."""
    provider = get_config().embedding_provider.lower()

    if provider == "bedrock":
        client = _get_bedrock_client()
        return await asyncio.to_thread(embed_text_bedrock, text, client)

    if provider == "openai":
        api_key = get_config().openai_api_key
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai"
            )
        return await asyncio.to_thread(embed_text_openai, text, api_key)

    if provider == "local":
        return await asyncio.to_thread(embed_text_local, text)

    raise ValueError(f"Unknown embedding provider: {provider}")


def generate_embeddings(
    chunks: list[Chunk],
    batch_size: int = 25,
) -> list[Chunk]:
    """Add embedding vectors to a list of chunks (in-place)."""
    provider = get_config().embedding_provider.lower()
    total = len(chunks)
    logger.info(
        "Generating embeddings for %d chunks (provider=%s)", total, provider
    )

    if provider == "local":
        # fastembed supports native batching
        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            batch = chunks[start:end]
            vectors = embed_batch_local([c.content for c in batch])
            for chunk, vec in zip(batch, vectors):
                chunk.embedding = vec
            logger.info("Embedded batch %d-%d / %d", start, end - 1, total)
        return chunks

    if provider == "bedrock":
        client = _get_bedrock_client()
        embed_fn: Callable[[str], list[float]] = lambda t: embed_text_bedrock(t, client)
    elif provider == "openai":
        api_key = get_config().openai_api_key
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai"
            )
        embed_fn = lambda t: embed_text_openai(t, api_key)  # noqa: E731
    else:
        raise ValueError(f"Unknown embedding provider: {provider}")

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            batch = chunks[start:end]
            futures = {
                executor.submit(embed_fn, chunk.content): chunk
                for chunk in batch
            }
            for fut in concurrent.futures.as_completed(futures):
                chunk = futures[fut]
                try:
                    chunk.embedding = fut.result()
                except Exception:
                    logger.exception("Failed to embed chunk %s", chunk.chunk_id)
                    chunk.embedding = []
            logger.info("Embedded batch %d-%d / %d", start, end - 1, total)

    embedded = sum(1 for c in chunks if c.embedding)
    logger.info("Embedding complete: %d/%d succeeded", embedded, total)
    return chunks
