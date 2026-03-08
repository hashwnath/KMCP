"""Tests for chunker."""

from src.indexer.chunker import chunk_document


class TestChunkDocument:
    def test_produces_chunks(self, test_document):
        chunks = chunk_document(
            test_document.doc_id, test_document.tenant_id,
            "# Intro\n\nParagraph.\n\n## Section\n\nMore text.\n\n```python\nprint(1)\n```",
            test_document.metadata,
        )
        assert len(chunks) > 0

    def test_code_blocks_marked(self, test_document):
        chunks = chunk_document(
            test_document.doc_id, test_document.tenant_id,
            "# Intro\n\n```python\ndef f(): pass\n```",
            test_document.metadata,
        )
        code = [c for c in chunks if c.is_code]
        assert len(code) >= 1

    def test_unique_chunk_ids(self, test_document):
        chunks = chunk_document(
            test_document.doc_id, test_document.tenant_id,
            "# A\n\nPara 1.\n\n## B\n\nPara 2.",
            test_document.metadata,
        )
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_token_count_positive(self, test_document):
        chunks = chunk_document(
            test_document.doc_id, test_document.tenant_id,
            "# A\n\nSome text here.",
            test_document.metadata,
        )
        for c in chunks:
            assert c.token_count > 0

    def test_empty_markdown(self, test_document):
        chunks = chunk_document(test_document.doc_id, test_document.tenant_id, "", test_document.metadata)
        assert isinstance(chunks, list)
