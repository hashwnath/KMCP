<div align="center">

# KnowledgeMCP

**Give your docs an MCP endpoint. Every AI agent can use them.**

[![CI](https://github.com/hashwnath/KMCP/actions/workflows/ci.yml/badge.svg)](https://github.com/hashwnath/KMCP/actions/workflows/ci.yml)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![MCP-native](https://img.shields.io/badge/MCP-native-purple.svg)](https://modelcontextprotocol.io)

</div>



https://github.com/user-attachments/assets/304fa31a-5138-4d02-b407-4c518f6a4145


---

KnowledgeMCP turns any documentation source (websites, PDFs, Confluence, Notion, S3, GitHub) into a **standards-compliant Model Context Protocol (MCP) endpoint**. Claude, GitHub Copilot, Cursor, and any other MCP-compatible agent can search and read those docs instantly — **with no LLM calls at query time** (we use a tiny local embedding model + hybrid BM25/kNN search in OpenSearch).

- 🔌 **MCP-native** — three tools (`docs_search`, `code_sample_search`, `docs_fetch`) any agent can plug into
- 💰 **Zero-cost query path** — local embeddings + OpenSearch hybrid search. No OpenAI/Bedrock fees per query.
- 🐳 **`docker compose up` works** — runs fully local, no AWS account, no credit card
- ☁️ **Production-ready AWS path** when you want it — Lambda + DynamoDB + SQS + S3 + managed OpenSearch via the bundled SAM template

## Quick start

```bash
git clone https://github.com/hashwnath/KMCP.git
cd KMCP
make up                # docker compose up -d --build
```

Then:
- **Dashboard** → http://localhost:3000 (signup → add a source → search)
- **Admin REST API** → http://localhost:8081
- **MCP endpoint** → http://localhost:8000/mcp/{your-tenant-slug}

First-time start downloads the fastembed model (~30 MB) and OpenSearch (~700 MB image).

## How agents use it

Point any MCP client at your tenant URL:

```json
{
  "mcpServers": {
    "MyDocs": {
      "url": "http://localhost:8000/mcp/your-tenant-slug",
      "type": "http"
    }
  }
}
```

The agent gets three tools:

| Tool | Purpose | Returns |
|---|---|---|
| `docs_search` | semantic + keyword search | up to 10 chunks with title, URL, ~500-token excerpt |
| `code_sample_search` | code-specific search with optional language filter | up to 20 snippets with language + context |
| `docs_fetch` | full page content | clean markdown |

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│   AI Agents  (Claude, Cursor, Copilot, Continue, ...)      │
└──────────────────────────┬─────────────────────────────────┘
                           │ POST /mcp/{tenant_slug}
┌──────────────────────────▼─────────────────────────────────┐
│   MCP Server (FastMCP)  — docs_search / code_search / fetch │
└──────────────────────────┬─────────────────────────────────┘
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
    ┌───────────────┐ ┌──────────┐ ┌──────────────┐
    │   OpenSearch  │ │  SQLite  │ │  Filesystem  │
    │ (BM25 + kNN)  │ │ tenants  │ │  blobs       │
    │  ~768 token   │ │ sources  │ │  uploads     │
    │  chunks       │ │ jobs     │ │              │
    └───────────────┘ └──────────┘ └──────────────┘
                           ▲
┌──────────────────────────┴─────────────────────────────────┐
│ Admin API (Starlette)  +  Background Worker                 │
│   signup/login (JWT)        crawl → markdown → chunk →      │
│   sources CRUD              embed → OpenSearch              │
│   analytics                                                 │
└────────────────────────────────────────────────────────────┘
```

(In AWS mode, swap SQLite → DynamoDB, Filesystem → S3, the worker queue → SQS,
and run each service as its own Lambda. The application code is unchanged
because every AWS call routes through `src/common/backends/`.)

## Supported source types

| Type | What it ingests |
|---|---|
| `website_url` | Full sitemap crawl → markdown |
| `paste_text` | Inline text |
| `file_upload` | PDF, DOCX, PPTX, MD, HTML, TXT |
| `cloud_storage` | S3, Azure Blob, GCS |
| `wiki_kb` | Confluence, Notion, SharePoint, GitBook |
| `git_repo` | Public or private GitHub/GitLab repos (token optional) |

## Configuration

Defaults work for local docker-compose. To customise, copy `.env.example` to `.env` and edit. The most useful knobs:

| Var | Default | Notes |
|---|---|---|
| `BACKEND` | `local` | `local` (default) or `aws` |
| `EMBEDDING_PROVIDER` | `local` | `local` (fastembed) / `bedrock` / `openai` |
| `LOCAL_EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Any [fastembed-supported](https://qdrant.github.io/fastembed/examples/Supported_Models/) model |
| `OPENSEARCH_ENDPOINT` | `http://opensearch:9200` | In compose; override for hosted OpenSearch |
| `MAX_DOCS_PER_TENANT` | `500` | Per-tenant quota |
| `RATE_LIMIT_PER_SECOND` | `10` | MCP endpoint rate limit (per tenant) |

## AWS production deployment

See **[docs/AWS_DEPLOYMENT.md](docs/AWS_DEPLOYMENT.md)** for the SAM template (Lambda + DynamoDB + SQS + S3 + OpenSearch + SES), cost estimate, and operational runbook.

## Contributing

PRs welcome. See **[CONTRIBUTING.md](CONTRIBUTING.md)** for the codebase tour and local dev setup.

```bash
make test        # full pytest suite (BACKEND=local)
make test-aws    # AWS-mocked suite
make up          # docker compose up -d --build
```

## License

- **Backend** (`src/`, `infra/`, top-level configs) — [AGPL-3.0](LICENSE)
- **Frontend** (`frontend/`) — [MIT](frontend/LICENSE)

The AGPL-3.0 license means hosted/SaaS use must publish modifications under the same license. If that's a problem for your use case, please [open an issue](https://github.com/hashwnath/KMCP/issues) so we can discuss commercial licensing.

## Why KnowledgeMCP?

| | KnowledgeMCP | Typical RAG tools |
|---|---|---|
| **Query cost** | $0 (local embeddings + OpenSearch) | $0.01-0.10/query (LLM reranking) |
| **Agent integration** | Native MCP — plug and play | REST API + custom glue code |
| **Self-hosted** | `docker compose up`, no cloud account | Usually needs cloud APIs |
| **Multi-tenant** | Per-tenant isolation built-in | Single-tenant, bolt-on later |
| **Latency** | ~100ms (no LLM in path) | 1-5s (LLM reranking) |

## Community

- [GitHub Discussions](https://github.com/hashwnath/KMCP/discussions) — questions, ideas, show-and-tell
- [Issues](https://github.com/hashwnath/KMCP/issues) — bug reports, feature requests

## Acknowledgements

- [FastMCP](https://github.com/jlowin/fastmcp) — the MCP server framework
- [fastembed](https://github.com/qdrant/fastembed) — ONNX-runtime embedding library
- [OpenSearch](https://opensearch.org) — hybrid BM25 + kNN search
- [Microsoft Learn MCP server team](https://devblogs.microsoft.com/engineering-at-microsoft/how-we-built-the-microsoft-learn-mcp-server/) — for documenting hard-earned lessons that shaped the tenant-context-via-middleware design

