"""Tests for crawler modules."""

from src.crawler.html_to_markdown import html_to_markdown
from src.crawler.metadata_extractor import extract_metadata
from src.crawler.code_extractor import extract_code_blocks
from src.crawler.text_ingestor import ingest_text


class TestHtmlToMarkdown:
    def test_basic_conversion(self, test_html):
        md = html_to_markdown(test_html)
        assert "Main" in md
        assert "Content" in md

    def test_strips_nav_header_footer(self, test_html):
        md = html_to_markdown(test_html)
        assert "Nav" not in md
        assert "Foot" not in md

    def test_empty_html(self):
        assert html_to_markdown("").strip() == ""

    def test_accepts_url_param(self):
        md = html_to_markdown("<p>Test</p>", "https://example.com")
        assert "Test" in md


class TestMetadataExtractor:
    def test_title(self, test_html):
        meta = extract_metadata(test_html, "https://example.com")
        assert meta["title"] == "Example Page"

    def test_description(self, test_html):
        meta = extract_metadata(test_html, "https://example.com")
        assert meta["description"] == "Test page"

    def test_url_preserved(self):
        meta = extract_metadata("<html></html>", "https://x.com/docs/api")
        assert meta["url"] == "https://x.com/docs/api"

    def test_slug_from_path(self):
        meta = extract_metadata("<html></html>", "https://x.com/docs/api")
        assert meta["slug"] == "api"


class TestCodeExtractor:
    def test_extracts_python(self, test_markdown_with_code):
        blocks = extract_code_blocks(test_markdown_with_code)
        py = [b for b in blocks if b["language"] == "python"]
        assert len(py) >= 1

    def test_extracts_js(self, test_markdown_with_code):
        blocks = extract_code_blocks(test_markdown_with_code)
        js = [b for b in blocks if b["language"] == "javascript"]
        assert len(js) >= 1

    def test_no_code(self):
        assert extract_code_blocks("# Heading\n\nText") == []

    def test_skips_empty(self):
        blocks = extract_code_blocks("```python\n\n```\n\n```python\nreal()\n```")
        assert len(blocks) == 1


class TestTextIngestor:
    def test_creates_document(self, test_tenant):
        doc = ingest_text("# Hello", "Title", "src-1", test_tenant.tenant_id)
        assert doc.title == "Title"
        assert doc.tenant_id == test_tenant.tenant_id

    def test_deterministic_doc_id(self, test_tenant):
        a = ingest_text("Same", "T", "s1", test_tenant.tenant_id)
        b = ingest_text("Same", "T", "s1", test_tenant.tenant_id)
        assert a.doc_id == b.doc_id

    def test_strips_whitespace(self, test_tenant):
        doc = ingest_text("\n  Content  \n", "T", "s1", test_tenant.tenant_id)
        assert doc.content_markdown == "Content"
