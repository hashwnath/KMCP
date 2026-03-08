"""Embedding generation for document chunks.

Supports two providers:
  - Amazon Bedrock Titan Embed v2 (default, stays within AWS)
  - OpenAI text-embedding-3-small (higher quality, external)

Provider is selected via EMBEDDING_PROVIDER config.
Internal batching is used for throughput.
"""

import json
import logging
import asyncio
from typing import Callable

import boto3
import httpx

from src.common.config import get_config
from src.common.models import Chunk

logger = logging.getLogger(__name__)

config = get_config()

# ---------------------------------------------------------------------------
# Provider-specific implementations
# ---------------------------------------------------------------------------


def _get_bedrock_client() -> "boto3.client":
    """Lazy-create a Bedrock Runtime client."""
    return boto3.client("bedrock-runtime", region_name=config.aws_region)


def embed_text_bedrock(text: str, client: "boto3.client") -> list[float]:
    """Generate an embedding using Amazon Bedrock Titan Embed v2."""
    response = client.invoke_model(
        modelId=config.bedrock_model_id,
        body=json.dumps({"inputText": text}),
    )
    return json.loads(response["body"].read())["embedding"]


def embed_text_openai(text: str, api_key: str) -> list[float]:
    """Generate an embedding using OpenAI text-embedding-3-small."""
    resp = httpx.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": "text-embedding-3-small", "input": text},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def embed_single(text: str) -> list[float]:
    """Embed a single text string using the configured provider.

    Returns a list of floats (the embedding vector).
    """
    provider = config.embedding_provider.lower()

    if provider == "bedrock":
        client = _get_bedrock_client()
        return await asyncio.to_thread(embed_text_bedrock, text, client)

    if provider == "openai":
        api_key = config.openai_api_key
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
        return await asyncio.to_thread(embed_text_openai, text, api_key)

    raise ValueError(f"Unknown embedding provider: {provider}")


def generate_embeddings(
    chunks: list[Chunk],
    batch_size: int = 25,
) -> list[Chunk]:
    """Add embedding vectors to a list of chunks.

    Processes chunks in batches for throughput. Each chunk's ``embedding``
    field is populated in-place and the updated list is returned.

    Args:
        chunks: Chunks to embed (must have ``content`` set).
        batch_size: Number of chunks per batch (default 25).

    Returns:
        The same list of chunks with ``embedding`` populated.
    """
    provider = config.embedding_provider.lower()
    total = len(chunks)
    logger.info("Generating embeddings for %d chunks (provider=%s)", total, provider)

    if provider == "bedrock":
        client = _get_bedrock_client()
        embed_fn: Callable[[str], list[float]] = lambda text: embed_text_bedrock(text, client)
    elif provider == "openai":
        api_key = config.openai_api_key
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
        embed_fn = lambda text: embed_text_openai(text, api_key)  # noqa: E731
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
            for future in concurrent.futures.as_completed(futures):
                chunk = futures[future]
                try:
                    chunk.embedding = future.result()
                except Exception:
                    logger.exception("Failed to embed chunk %s", chunk.chunk_id)
                    chunk.embedding = []

            logger.info("Embedded batch %d-%d / %d", start, end - 1, total)

    embedded_count = sum(1 for c in chunks if c.embedding)
    logger.info("Embedding complete: %d/%d succeeded", embedded_count, total)
    return chunks
