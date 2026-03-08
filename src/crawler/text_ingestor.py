"""Wrap pasted text into the shared Document contract."""

from __future__ import annotations

import hashlib

from src.common.models import Document


def ingest_text(text: str, title: str, source_id: str, tenant_id: str) -> Document:
    """Create a Document from raw pasted text or markdown."""
    seed = f"{tenant_id}:{source_id}:{title}:{text}".encode("utf-8")
    doc_id = hashlib.sha256(seed).hexdigest()
    return Document(
        doc_id=doc_id,
        source_id=source_id,
        tenant_id=tenant_id,
        url=f"paste://{source_id}/{doc_id}",
        title=title,
        content_markdown=text.strip(),
        content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        metadata={"source_kind": "paste_text"},
    )