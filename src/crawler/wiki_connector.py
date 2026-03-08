"""Wiki/KB connectors — Confluence (REST API) and Notion (API).

Confluence: Uses REST API v2 with basic auth (email + API token).
Notion: Uses Notion API with bearer token.
Both convert HTML/rich content to markdown via the shared html_to_markdown util.
"""

from __future__ import annotations

import hashlib
import logging

import httpx

from src.common.models import Document
from src.crawler.html_to_markdown import html_to_markdown
from src.crawler.metadata_extractor import extract_metadata
from src.crawler.page_fetcher import fetch_pages_batch
from src.crawler.sitemap_parser import parse_sitemap

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Confluence (Atlassian Cloud REST API)
# ---------------------------------------------------------------------------

async def crawl_confluence(
    base_url: str,
    space_key: str,
    email: str,
    api_token: str,
    source_id: str,
    tenant_id: str,
) -> list[Document]:
    """Crawl a Confluence space and return Documents.

    Uses the Confluence REST API to list all pages in a space,
    then fetches each page's body in storage format (HTML) and
    converts to markdown.

    Args:
        base_url: Confluence instance URL (e.g., https://mycompany.atlassian.net/wiki)
        space_key: Space key (e.g., "ENG", "DOCS")
        email: Atlassian account email for basic auth
        api_token: Atlassian API token (not password)
        source_id: KnowledgeMCP source identifier
        tenant_id: Owning tenant
    """
    base_url = base_url.rstrip("/")
    documents: list[Document] = []

    async with httpx.AsyncClient(
        auth=(email, api_token),
        timeout=30.0,
        headers={"Accept": "application/json"},
    ) as client:
        # Paginate through all pages in the space
        start = 0
        limit = 50
        while True:
            url = (
                f"{base_url}/rest/api/content"
                f"?spaceKey={space_key}"
                f"&type=page"
                f"&expand=body.storage,metadata.labels"
                f"&start={start}&limit={limit}"
            )
            try:
                resp = await client.get(url)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                logger.error("Confluence API error: %s", exc)
                break

            data = resp.json()
            results = data.get("results", [])

            for page in results:
                page_id = page["id"]
                title = page.get("title", "")
                html_body = page.get("body", {}).get("storage", {}).get("value", "")
                page_url = f"{base_url}/pages/{page_id}"

                if not html_body.strip():
                    continue

                markdown = html_to_markdown(html_body, page_url)
                content_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()

                documents.append(
                    Document(
                        doc_id=hashlib.sha256(f"{tenant_id}:{source_id}:{page_id}".encode()).hexdigest(),
                        source_id=source_id,
                        tenant_id=tenant_id,
                        url=page_url,
                        title=title,
                        content_markdown=markdown,
                        content_hash=content_hash,
                        metadata={
                            "source_kind": "confluence",
                            "space_key": space_key,
                            "confluence_page_id": page_id,
                        },
                    )
                )

            # Check if there are more pages
            if data.get("size", 0) < limit:
                break
            start += limit

    logger.info("Crawled %d Confluence pages from space %s", len(documents), space_key)
    return documents


# ---------------------------------------------------------------------------
# Notion (Official API v1)
# ---------------------------------------------------------------------------

async def crawl_notion(
    api_key: str,
    root_page_id: str,
    source_id: str,
    tenant_id: str,
) -> list[Document]:
    """Crawl a Notion workspace starting from a root page.

    Uses the Notion API to recursively fetch child pages and their
    block content, converting rich text blocks to markdown.

    Args:
        api_key: Notion integration API key (secret_xxx)
        root_page_id: Starting page ID (or empty to search all)
        source_id: KnowledgeMCP source identifier
        tenant_id: Owning tenant
    """
    documents: list[Document] = []
    visited: set[str] = set()

    async with httpx.AsyncClient(
        timeout=30.0,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
    ) as client:
        # If root_page_id given, start there; otherwise search all pages
        page_ids_to_crawl: list[str] = []

        if root_page_id:
            page_ids_to_crawl.append(root_page_id)
        else:
            # Search for all pages the integration can access
            try:
                resp = await client.post(
                    "https://api.notion.com/v1/search",
                    json={"filter": {"property": "object", "value": "page"}, "page_size": 100},
                )
                resp.raise_for_status()
                for result in resp.json().get("results", []):
                    page_ids_to_crawl.append(result["id"])
            except httpx.HTTPError as exc:
                logger.error("Notion search error: %s", exc)
                return documents

        # Process each page
        for page_id in page_ids_to_crawl:
            if page_id in visited:
                continue
            visited.add(page_id)

            try:
                # Get page metadata
                page_resp = await client.get(f"https://api.notion.com/v1/pages/{page_id}")
                page_resp.raise_for_status()
                page_data = page_resp.json()

                # Extract title from properties
                title = _extract_notion_title(page_data)
                page_url = page_data.get("url", f"https://notion.so/{page_id}")

                # Get all blocks (content)
                blocks_content = await _fetch_notion_blocks(client, page_id)

                if not blocks_content.strip():
                    continue

                content_hash = hashlib.sha256(blocks_content.encode("utf-8")).hexdigest()

                documents.append(
                    Document(
                        doc_id=hashlib.sha256(f"{tenant_id}:{source_id}:{page_id}".encode()).hexdigest(),
                        source_id=source_id,
                        tenant_id=tenant_id,
                        url=page_url,
                        title=title,
                        content_markdown=blocks_content,
                        content_hash=content_hash,
                        metadata={"source_kind": "notion", "notion_page_id": page_id},
                    )
                )

                # Find child pages to crawl recursively
                child_resp = await client.get(
                    f"https://api.notion.com/v1/blocks/{page_id}/children",
                    params={"page_size": 100},
                )
                if child_resp.status_code == 200:
                    for block in child_resp.json().get("results", []):
                        if block.get("type") == "child_page":
                            child_id = block["id"]
                            if child_id not in visited:
                                page_ids_to_crawl.append(child_id)

            except httpx.HTTPError as exc:
                logger.warning("Failed to fetch Notion page %s: %s", page_id, exc)
                continue

    logger.info("Crawled %d Notion pages", len(documents))
    return documents


def _extract_notion_title(page_data: dict) -> str:
    """Extract page title from Notion page properties."""
    props = page_data.get("properties", {})
    for prop in props.values():
        if prop.get("type") == "title":
            title_parts = prop.get("title", [])
            return "".join(t.get("plain_text", "") for t in title_parts)
    return "Untitled"


async def _fetch_notion_blocks(client: httpx.AsyncClient, block_id: str) -> str:
    """Fetch all blocks for a page and convert to markdown."""
    lines: list[str] = []
    cursor = None

    while True:
        params: dict = {"page_size": 100}
        if cursor:
            params["start_cursor"] = cursor

        try:
            resp = await client.get(
                f"https://api.notion.com/v1/blocks/{block_id}/children",
                params=params,
            )
            resp.raise_for_status()
        except httpx.HTTPError:
            break

        data = resp.json()
        for block in data.get("results", []):
            line = _notion_block_to_markdown(block)
            if line:
                lines.append(line)

        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")

    return "\n\n".join(lines)


def _notion_block_to_markdown(block: dict) -> str:
    """Convert a single Notion block to a markdown line."""
    btype = block.get("type", "")
    bdata = block.get(btype, {})

    def _rich_text(rt_list: list) -> str:
        return "".join(t.get("plain_text", "") for t in rt_list)

    if btype == "paragraph":
        return _rich_text(bdata.get("rich_text", []))
    if btype == "heading_1":
        return f"# {_rich_text(bdata.get('rich_text', []))}"
    if btype == "heading_2":
        return f"## {_rich_text(bdata.get('rich_text', []))}"
    if btype == "heading_3":
        return f"### {_rich_text(bdata.get('rich_text', []))}"
    if btype == "bulleted_list_item":
        return f"- {_rich_text(bdata.get('rich_text', []))}"
    if btype == "numbered_list_item":
        return f"1. {_rich_text(bdata.get('rich_text', []))}"
    if btype == "code":
        lang = bdata.get("language", "")
        code = _rich_text(bdata.get("rich_text", []))
        return f"```{lang}\n{code}\n```"
    if btype == "quote":
        return f"> {_rich_text(bdata.get('rich_text', []))}"
    if btype == "callout":
        return f"> {_rich_text(bdata.get('rich_text', []))}"
    if btype == "divider":
        return "---"
    if btype == "to_do":
        checked = "x" if bdata.get("checked") else " "
        return f"- [{checked}] {_rich_text(bdata.get('rich_text', []))}"
    if btype == "toggle":
        return _rich_text(bdata.get("rich_text", []))
    if btype == "image":
        url = bdata.get("external", {}).get("url") or bdata.get("file", {}).get("url", "")
        return f"![image]({url})" if url else ""

    return ""


# ---------------------------------------------------------------------------
# SharePoint / GitBook (website crawl fallback)
# ---------------------------------------------------------------------------

async def _crawl_site_urls(
    urls: list[str],
    source_id: str,
    tenant_id: str,
    source_kind: str,
) -> list[Document]:
    """Shared site crawler for providers without dedicated API client in MVP."""
    documents: list[Document] = []
    if not urls:
        return documents

    results = await fetch_pages_batch(urls, concurrency=5)
    for url, html, status in results:
        if status != 200 or not html:
            continue
        markdown = html_to_markdown(html, url)
        if not markdown.strip():
            continue
        meta = extract_metadata(html, url)
        documents.append(
            Document(
                doc_id=hashlib.sha256(f"{tenant_id}:{source_id}:{url}".encode()).hexdigest(),
                source_id=source_id,
                tenant_id=tenant_id,
                url=url,
                title=meta.get("title", ""),
                content_markdown=markdown,
                content_hash=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
                metadata={**meta, "source_kind": source_kind},
            )
        )
    return documents


async def crawl_sharepoint(
    site_url: str,
    source_id: str,
    tenant_id: str,
) -> list[Document]:
    """Crawl a SharePoint site via sitemap crawl fallback."""
    site_url = site_url.rstrip("/")
    sitemap_url = f"{site_url}/sitemap.xml"
    try:
        urls = await parse_sitemap(sitemap_url)
    except Exception:
        urls = [site_url]
    return await _crawl_site_urls(urls[:500], source_id, tenant_id, "sharepoint")


async def crawl_gitbook(
    base_url: str,
    source_id: str,
    tenant_id: str,
) -> list[Document]:
    """Crawl a GitBook docs site via sitemap crawl fallback."""
    base_url = base_url.rstrip("/")
    sitemap_url = f"{base_url}/sitemap.xml"
    try:
        urls = await parse_sitemap(sitemap_url)
    except Exception:
        urls = [base_url]
    return await _crawl_site_urls(urls[:500], source_id, tenant_id, "gitbook")
