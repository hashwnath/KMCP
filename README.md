# KnowledgeMCP

**Give your docs an MCP endpoint. Every AI agent can use them.**

KnowledgeMCP turns any documentation into a standards-compliant Model Context Protocol endpoint. AI agents like Claude, GitHub Copilot, Cursor, and more can search and fetch your docs instantly.

## Architecture

```
AI Agents (Claude, Cursor, Copilot)
        │
        ▼
┌──────────────────────────┐
│ MCP Server (FastMCP)     │  POST /mcp/{tenant}
│  • docs_search           │  x-api-key auth
│  • code_sample_search    │  JSON-RPC 2.0
│  • docs_fetch            │
└───────────┬──────────────┘
            │
  ┌─────────┼─────────┐
  ▼         ▼         ▼
OpenSearch  DynamoDB   S3
(vectors)  (metadata) (content)

Admin API (Starlette)
├── Signup / Login (JWT)
├── Source CRUD
├── Analytics (overview, gaps, top queries)
└── Settings (API key, slug)

Crawl Pipeline (SQS → Lambda)
  URL → sitemap → pages → markdown → chunks → embeddings → OpenSearch
```

## Quick Start (Docker)

```bash
cd knowledgemcp
cp .env.example .env   # Edit with your AWS/OpenSearch creds
docker-compose up
```

- MCP Server: http://localhost:8000
- Admin API: http://localhost:8081

Seed demo data:
```bash
ADMIN_API_URL=http://localhost:8081 python scripts/seed_demo.py
```

## AWS Deployment (SAM)

```bash
# First time
./scripts/deploy.sh

# Subsequent
./scripts/deploy.sh quickstart
```

Resources created: Lambda (crawler, indexer, admin, MCP), API Gateway, DynamoDB (3 tables), SQS (2 queues), S3 bucket.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `AWS_REGION` | us-east-1 | AWS region |
| `OPENSEARCH_ENDPOINT` | — | OpenSearch domain URL |
| `EMBEDDING_PROVIDER` | bedrock | bedrock or openai |
| `BEDROCK_MODEL_ID` | amazon.titan-embed-text-v2:0 | Bedrock model |
| `OPENAI_API_KEY` | — | Required if provider=openai |
| `JWT_SECRET_KEY` | *(required)* | Generate: `python -c \"import secrets; print(secrets.token_urlsafe(64))\"` |
| `SKIP_AUTH` | false | Bypass auth in dev |
| `RATE_LIMIT_PER_SECOND` | 10 | Per-tenant rate |
| `CRAWL_QUEUE_URL` | — | SQS crawl queue |
| `INDEX_QUEUE_URL` | — | SQS index queue |
| `TENANTS_TABLE` | knowledgemcp-tenants | DynamoDB table |
| `SOURCES_TABLE` | knowledgemcp-sources | DynamoDB table |
| `ANALYTICS_TABLE` | knowledgemcp-analytics | DynamoDB table |
| `CONTENT_BUCKET` | knowledgemcp-content | S3 bucket |

## MCP Endpoint Usage

Add to your editor's MCP config:

```json
{
  "mcpServers": {
    "MyDocs": {
      "url": "https://mcp.knowledgemcp.io/my-tenant",
      "type": "http",
      "headers": { "x-api-key": "kmcp_sk_..." }
    }
  }
}
```

The endpoint exposes 3 tools:
- **docs_search** — semantic + keyword search, returns 10 chunks with title/URL/excerpt
- **code_sample_search** — code-specific search with optional language filter, returns 20 snippets
- **docs_fetch** — fetch full page as clean markdown

## Admin API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | /api/auth/signup | Create tenant |
| POST | /api/auth/login | Get JWT token |
| GET | /api/tenants/me | Tenant profile |
| POST | /api/sources | Add documentation source |
| GET | /api/sources | List sources |
| POST | /api/sources/{id}/reindex | Re-crawl source |
| DELETE | /api/sources/{id} | Delete source |
| GET | /api/analytics/overview | Usage stats |
| GET | /api/analytics/gaps | Content gap queries |
| GET | /api/analytics/top-queries | Popular queries |
| GET | /api/settings | Tenant settings |
| PUT | /api/settings | Update settings |
| POST | /api/settings/regenerate-key | New API key |

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Next.js 14 dashboard with landing page, auth, source management, analytics, and integration guides.

## Testing

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Project Structure

```
knowledgemcp/
├── src/
│   ├── common/          # Config, models, AWS clients, DynamoDB helpers
│   ├── crawler/         # Content ingestion (website, files, S3, wiki, git, text)
│   ├── indexer/         # Chunking, embedding, OpenSearch indexing
│   ├── mcp_server/      # FastMCP tools, retrieval, middleware, ASGI handler
│   ├── admin/           # REST API for tenant/source management
│   └── analytics/       # Query logging and reporting
├── tests/               # pytest suite
├── scripts/             # seed_demo, test_mcp_endpoint, deploy.sh
├── infra/               # SAM template + config
├── frontend/            # Next.js 14 dashboard
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── pyproject.toml
```
