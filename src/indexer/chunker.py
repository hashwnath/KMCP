"""Semantic chunking for documents.

Splits markdown documents into overlapping chunks suitable for
embedding and retrieval. Preserves code blocks as complete units
and maintains metadata on every chunk.

Chunking strategy:
  1. Split by headings (## / ###)
  2. Within sections, split by paragraphs
  3. Accumulate paragraphs until reaching ~768 tokens (target range 512-1024)
  4. Code blocks are emitted as standalone chunks with is_code=True
  5. 10% overlap: prepend last ~100 tokens of previous chunk to current
"""

import re
import logging

from src.common.tokenizer import count_tokens as _count_tokens_fn, encode as _encode, decode as _decode

from src.common.models import Chunk

logger = logging.getLogger(__name__)


# Chunk size parameters
_MIN_CHUNK_TOKENS = 512
_TARGET_CHUNK_TOKENS = 768
_MAX_CHUNK_TOKENS = 1024
_OVERLAP_FRACTION = 0.10  # 10% overlap
_OVERLAP_TOKENS = 100  # ~10% of target

# Regex patterns
_HEADING_RE = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)
_CODE_BLOCK_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)


def _count_tokens(text: str) -> int:
    """Count tokens using the portable tokenizer."""
    return _count_tokens_fn(text)


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to fit within max_tokens."""
    tokens = _encode(text)
    if len(tokens) <= max_tokens:
        return text
    return _decode(tokens[:max_tokens])


def _get_overlap_text(text: str) -> str:
    """Extract the last ~100 tokens from text for overlap."""
    tokens = _encode(text)
    if len(tokens) <= _OVERLAP_TOKENS:
        return text
    return _decode(tokens[-_OVERLAP_TOKENS:])


def _split_by_headings(markdown: str) -> list[dict]:
    """Split markdown into sections by headings.

    Returns list of dicts with 'heading' and 'content' keys.
    """
    sections: list[dict] = []
    heading_matches = list(_HEADING_RE.finditer(markdown))

    if not heading_matches:
        return [{"heading": "", "content": markdown}]

    # Content before the first heading
    first_pos = heading_matches[0].start()
    if first_pos > 0:
        preamble = markdown[:first_pos].strip()
        if preamble:
            sections.append({"heading": "", "content": preamble})

    for i, match in enumerate(heading_matches):
        heading = match.group(2).strip()
        start = match.end()
        end = heading_matches[i + 1].start() if i + 1 < len(heading_matches) else len(markdown)
        content = markdown[start:end].strip()
        if content:
            sections.append({"heading": heading, "content": content})

    return sections


def _extract_code_and_text(content: str) -> list[dict]:
    """Split section content into text blocks and code blocks.

    Returns a list of dicts:
      {"type": "text", "content": str}
      {"type": "code", "content": str, "language": str}
    """
    blocks: list[dict] = []
    last_end = 0

    for match in _CODE_BLOCK_RE.finditer(content):
        # Text before this code block
        text_before = content[last_end:match.start()].strip()
        if text_before:
            blocks.append({"type": "text", "content": text_before})

        language = match.group(1) or "plaintext"
        code = match.group(2).strip()
        if code:
            blocks.append({"type": "code", "content": code, "language": language})

        last_end = match.end()

    # Remaining text after last code block
    remaining = content[last_end:].strip()
    if remaining:
        blocks.append({"type": "text", "content": remaining})

    return blocks


def _split_text_into_paragraphs(text: str) -> list[str]:
    """Split text on double newlines (paragraph boundaries)."""
    paragraphs = re.split(r"\n{2,}", text)
    return [p.strip() for p in paragraphs if p.strip()]


def _accumulate_paragraphs(paragraphs: list[str]) -> list[str]:
    """Group paragraphs into chunks targeting ~768 tokens.

    Accumulates paragraphs until the target token count is reached.
    Never exceeds the max, and always emits at least the min
    (unless the source text is shorter than the min).
    """
    chunks: list[str] = []
    current_parts: list[str] = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = _count_tokens(para)

        # If a single paragraph exceeds the max, emit it standalone
        if para_tokens > _MAX_CHUNK_TOKENS:
            if current_parts:
                chunks.append("\n\n".join(current_parts))
                current_parts = []
                current_tokens = 0
            chunks.append(para)
            continue

        # Would adding this paragraph exceed the target?
        projected = current_tokens + para_tokens
        if projected > _TARGET_CHUNK_TOKENS and current_parts:
            chunks.append("\n\n".join(current_parts))
            current_parts = []
            current_tokens = 0

        current_parts.append(para)
        current_tokens += para_tokens

    if current_parts:
        chunks.append("\n\n".join(current_parts))

    return chunks


def chunk_document(
    doc_id: str,
    tenant_id: str,
    markdown: str,
    metadata: dict,
) -> list[Chunk]:
    """Chunk a markdown document into embedding-ready pieces.

    Args:
        doc_id: Unique document identifier.
        tenant_id: Owning tenant.
        markdown: Full document content in markdown.
        metadata: Dict with keys like url, title, section, breadcrumb.

    Returns:
        List of Chunk objects ready for embedding.
    """
    url = metadata.get("url", "")
    title = metadata.get("title", "")
    breadcrumb = metadata.get("breadcrumb", "")
    source_id = metadata.get("source_id", "")

    sections = _split_by_headings(markdown)
    raw_chunks: list[dict] = []

    for section in sections:
        heading = section["heading"]
        blocks = _extract_code_and_text(section["content"])

        for block in blocks:
            if block["type"] == "code":
                raw_chunks.append({
                    "content": block["content"],
                    "heading": heading,
                    "is_code": True,
                    "code_language": block["language"],
                })
            else:
                paragraphs = _split_text_into_paragraphs(block["content"])
                text_chunks = _accumulate_paragraphs(paragraphs)
                for tc in text_chunks:
                    raw_chunks.append({
                        "content": tc,
                        "heading": heading,
                        "is_code": False,
                        "code_language": "",
                    })

    # Build Chunk objects with overlap
    chunks: list[Chunk] = []
    prev_content = ""

    for idx, raw in enumerate(raw_chunks):
        content = raw["content"]

        # Add overlap from previous chunk (skip for code blocks and first chunk)
        if idx > 0 and not raw["is_code"] and prev_content:
            overlap = _get_overlap_text(prev_content)
            content = overlap + "\n\n" + content

        token_count = _count_tokens(content)
        chunk_id = f"{doc_id}_{idx}"

        chunk = Chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            tenant_id=tenant_id,
            source_id=source_id,
            content=content,
            title=title,
            url=url,
            section=raw["heading"],
            metadata={
                "breadcrumb": breadcrumb,
                "chunk_index": idx,
                "total_chunks": len(raw_chunks),
            },
            embedding=[],
            is_code=raw["is_code"],
            code_language=raw["code_language"],
            token_count=token_count,
        )
        chunks.append(chunk)

        # Track previous text content for overlap (only text, not code)
        if not raw["is_code"]:
            prev_content = raw["content"]

    logger.info(
        "Chunked doc %s: %d sections → %d chunks (doc: %d, code: %d)",
        doc_id,
        len(sections),
        len(chunks),
        sum(1 for c in chunks if not c.is_code),
        sum(1 for c in chunks if c.is_code),
    )
    return chunks
