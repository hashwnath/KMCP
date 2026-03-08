# KnowledgeMCP Scaffold

## Architecture Decisions
- Python backend kept as Lambda-friendly modules for crawler, indexer, admin API, and MCP runtime.
- Core MVP sources implemented directly: website URL, file upload from S3-backed uploads, pasted text.
- Cloud storage supports S3, Azure Blob, and GCS via a provider dispatcher.
- Wiki/KB supports Confluence, Notion, SharePoint, and GitBook fallback crawling.
- Search remains single OpenSearch index per tenant with top-level `is_code` and `source_id` fields for code filtering and source cleanup.
- MCP tool contract remains three-tool focused: `docs_search`, `code_sample_search`, `docs_fetch`.
- Scheduled sync execution is implemented via EventBridge-driven scheduler Lambda.
- Magic-link auth uses SES delivery and does not return raw link/token payloads.

## File Tree Status
- `src/common/config.py`: done
- `src/common/models.py`: done
- `src/common/dynamodb.py`: done
- `src/crawler/handler.py`: done
- `src/crawler/page_fetcher.py`: existing
- `src/crawler/sitemap_parser.py`: existing
- `src/crawler/html_to_markdown.py`: done
- `src/crawler/metadata_extractor.py`: done
- `src/crawler/code_extractor.py`: done
- `src/crawler/file_processor.py`: done
- `src/crawler/text_ingestor.py`: done
- `src/crawler/s3_connector.py`: done
- `src/crawler/wiki_connector.py`: done
- `src/crawler/git_connector.py`: done
- `src/indexer/chunker.py`: done
- `src/indexer/embedder.py`: done
- `src/indexer/opensearch_client.py`: done
- `src/indexer/code_indexer.py`: done
- `src/indexer/handler.py`: done
- `src/indexer/html_to_markdown.py`: done
- `src/mcp_server/retrieval.py`: done
- `src/mcp_server/tools/*`: done
- `src/mcp_server/middleware.py`: done
- `src/mcp_server/handler.py`: done
- `src/admin/auth.py`: done
- `src/admin/routes.py`: done
- `src/admin/handler.py`: existing
- `src/analytics/logger.py`: done
- `src/analytics/reporter.py`: existing
- `src/scheduler/handler.py`: done
- `requirements.txt`: done
- `pyproject.toml`: done

## Implementation Order
1. Stabilize config and shared models.
2. Add missing crawler and indexer helper modules.
3. Align queue payloads from crawler to indexer.
4. Align retrieval and MCP tool contracts.
5. Restore admin analytics/source-management coverage.
6. Add dependency declarations and state tracking.

## Current State
- Core backend MVP implementation is present in repo.
- Scheduled sync, tenant-safe auth context, and source-key fixes are implemented.
- CORS is configured by `FRONTEND_ORIGIN` instead of hardcoded wildcard in app code.
- Secrets in source config are redacted from API responses.
- Runtime verification is environment-limited in this workspace (no local Python/npm execution available).

## Deployment Config Needed
- `AWS_REGION`
- `AWS_ACCOUNT_ID`
- `TENANTS_TABLE`
- `SOURCES_TABLE`
- `ANALYTICS_TABLE`
- `CRAWL_QUEUE_URL`
- `INDEX_QUEUE_URL`
- `CONTENT_BUCKET`
- `OPENSEARCH_ENDPOINT`
- `EMBEDDING_PROVIDER`
- `BEDROCK_MODEL_ID` or `OPENAI_API_KEY`
- `JWT_SECRET_KEY`
- `APP_BASE_URL`
- `SES_FROM_EMAIL`
- `FRONTEND_ORIGIN`

## Known Issues / Tech Debt
- Source listing assumes a `tenant-index` GSI exists on the sources table (defined in SAM template).
- Tenant lookup by slug uses a `slug-index` GSI (defined in SAM template).
- The MCP runtime proxy is a minimal ASGI bridge and should be verified against the final FastMCP version used in deployment.
- Pre-indexed demo sites (Stripe, MongoDB, etc.) require running `seed_demo.py` post-deployment.
- Frontend component extraction: config forms are inline in page files rather than reusable component files.

## Resolved Issues
- Source credentials are stored in AWS Secrets Manager via `secret_ref` pattern (not inline in DynamoDB).
- CORS defaults to `http://localhost:3000` (not wildcard). Production deployments must set `FRONTEND_ORIGIN`.
- Dark mode is supported via CSS class toggle + system preference detection.
- Progress UI uses deterministic ratio when `pages_found` is available.

## Test Results
- Static code patching only.
- No package install, no runtime execution, no AWS calls, no local tests run in this environment.