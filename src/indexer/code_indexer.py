"""Code sample indexer.

Takes code blocks extracted from documents, wraps them as Chunk objects,
generates embeddings, and indexes them into the same tenant OpenSearch
index with ``is_code=True``.
"""

import logging
from src.common.tokenizer import count_tokens

from src.common.models import Chunk
from src.indexer.embedder import generate_embeddings
from src.indexer.opensearch_client import index_chunks

logger = logging.getLogger(__name__)


def index_code_samples(
    tenant_id: str,
    doc_id: str,
    source_id: str,
    code_blocks: list[dict],
) -> int:
    """Index extracted code samples for a document.

    Each ``code_block`` dict is expected to have:
        - ``code`` (str): The source code.
        - ``language`` (str): Programming language identifier.
        - ``context`` (str): Surrounding text / description.
        - ``line_number`` (int): Line number in the original document.

    The code and its context are combined into the chunk content so that
    semantic search can match on descriptive text as well as code tokens.

    Args:
        tenant_id: Owning tenant.
        doc_id: Parent document id.
        code_blocks: List of code block dicts from the code extractor.

    Returns:
        Number of code chunks successfully indexed.
    """
    if not code_blocks:
        return 0

    chunks: list[Chunk] = []

    for idx, block in enumerate(code_blocks):
        code: str = block.get("code", "")
        language: str = block.get("language", "plaintext")
        context: str = block.get("context", "")
        line_number: int = block.get("line_number", 0)

        if not code.strip():
            continue

        # Combine context + code for richer embedding
        content = f"{context}\n\n```{language}\n{code}\n```" if context else code

        chunk = Chunk(
            chunk_id=f"{doc_id}_code_{idx}",
            doc_id=doc_id,
            tenant_id=tenant_id,
            source_id=source_id,
            content=content,
            title="",
            url="",
            section="",
            metadata={
                "language": language,
                "line_number": line_number,
                "chunk_type": "code_sample",
            },
            embedding=[],
            is_code=True,
            code_language=language,
            token_count=count_tokens(content),
        )
        chunks.append(chunk)

    if not chunks:
        logger.info("No non-empty code blocks for doc %s", doc_id)
        return 0

    # Generate embeddings
    chunks = generate_embeddings(chunks)

    # Push to OpenSearch
    indexed = index_chunks(tenant_id, chunks)
    logger.info(
        "Indexed %d/%d code samples for doc %s (tenant %s)",
        indexed,
        len(chunks),
        doc_id,
        tenant_id,
    )
    return indexed
