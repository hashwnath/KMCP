# KnowledgeMCP — AWS Deployment Rewire Guide

> **What this file is**: Context for the deploying agent/engineer. Covers what's already built,
> what's wired vs stubbed, and the exact steps to go from this repo to a live AWS deployment.

---

## 1. What's Already Done (Lift-and-Shift Ready)

### Backend (Python 3.11)
| Module | Path | Status | Notes |
|---|---|---|---|
| **Shared config** | `src/common/config.py` | Done | Pydantic Settings, reads all env vars |
| **Data models** | `src/common/models.py` | Done | Tenant, Source, CrawlJob, Document, Chunk, SearchResult, CodeSearchResult, QueryLog |
| **AWS clients** | `src/common/aws_clients.py` | Done | Cached singletons for DynamoDB, S3, SQS, Bedrock, OpenSearch (IAM AOSS auth) |
| **DynamoDB helper** | `src/common/dynamodb.py` | Done | Tenant lookup by slug (scan-based — needs GSI for production) |
| **Crawler handler** | `src/crawler/handler.py` | Done | Lambda handler, routes by SourceType, sends docs to INDEX_QUEUE |
| **Sitemap parser** | `src/crawler/sitemap_parser.py` | Done | Async, recursive sitemap index support |
| **Page fetcher** | `src/crawler/page_fetcher.py` | Done | Concurrent with semaphore, robots.txt compliance |
| **HTML→Markdown** | `src/crawler/html_to_markdown.py` | Done | BeautifulSoup + markdownify, strips nav/header/footer |
| **Metadata extractor** | `src/crawler/metadata_extractor.py` | Done | title, description, og:title, slug |
| **Code extractor** | `src/crawler/code_extractor.py` | Done | Regex fenced blocks with language detection |
| **File processor** | `src/crawler/file_processor.py` | Done | PDF (PyMuPDF), DOCX, PPTX, plaintext |
| **S3 connector** | `src/crawler/s3_connector.py` | Done | Lists objects, processes via file_processor |
| **Text ingestor** | `src/crawler/text_ingestor.py` | Done | Raw paste→Document |
| **Wiki connector** | `src/crawler/wiki_connector.py` | Stubbed | Returns empty list — needs Confluence/Notion API impl |
| **Git connector** | `src/crawler/git_connector.py` | Stubbed | Returns empty list — needs git clone + fs walk impl |
| **Chunker** | `src/indexer/chunker.py` | Done | Heading-first, 512-1024 tokens, 10% overlap, code preserved |
| **Embedder** | `src/indexer/embedder.py` | Done | Bedrock Titan v2 or OpenAI, parallel ThreadPoolExecutor(8) |
| **OpenSearch client** | `src/indexer/opensearch_client.py` | Done | Index lifecycle, bulk index, hybrid search (BM25 0.4 + vector 0.6), chunk reassembly by chunk_index |
| **Indexer handler** | `src/indexer/handler.py` | Done | Lambda handler, chunks→embeds→indexes, updates DynamoDB status |
| **MCP server** | `src/mcp_server/server.py` | Done | FastMCP, 3 tools registered |
| **ASGI handler** | `src/mcp_server/handler.py` | Done | Starlette app, /mcp/{tenant_slug}, /health, CORS, SSE route |
| **Lambda handler** | `src/mcp_server/lambda_handler.py` | Done | Mangum adapter wrapping ASGI app |
| **Retrieval** | `src/mcp_server/retrieval.py` | Done | 3-phase RAG: expand→hybrid search→MMR re-rank→dedup→token-truncate |
| **Tenant context** | `src/mcp_server/tenant_context.py` | Done | ContextVar-based, set by middleware, read by tools |
| **Middleware** | `src/mcp_server/middleware.py` | Done | API key auth, token-bucket rate limit, request logging |
| **Tools** | `src/mcp_server/tools/` | Done | docs_search, code_sample_search, docs_fetch — all with latency tracking, error wrapping, no tenant_id param |
| **Admin API** | `src/admin/handler.py` + `routes.py` + `auth.py` | Done | Signup, login, JWT, source CRUD, analytics, settings, key regen |
| **Analytics** | `src/analytics/logger.py` + `reporter.py` | Done | Non-blocking DynamoDB logging, overview, top queries, content gaps |

### Infrastructure
| File | Status | Notes |
|---|---|---|
| `infra/template.yaml` | Done | SAM template: 4 Lambdas, API Gateway HTTP API, 3 DynamoDB tables, 2 SQS queues, S3 bucket, IAM roles |
| `infra/samconfig.toml` | Done | Default dev config |
| `Dockerfile` | Done | Multi-stage Python 3.11 |
| `docker-compose.yml` | Done | MCP server (8000) + Admin API (8081) |
| `.env.example` | Done | All env vars documented |

### Frontend
| File | Status | Notes |
|---|---|---|
| Next.js 14 App Router | Done | Landing page, login, signup, dashboard, sources (6-type picker), analytics, connect (5 editor tabs), settings |

### Tests
| File | Status |
|---|---|
| `tests/conftest.py` | Done — fixtures for all models + mocks |
| `tests/test_crawler.py` | Done — HTML→MD, metadata, code extractor, text ingestor |
| `tests/test_chunker.py` | Done — chunking, code preservation, overlap, uniqueness |
| `tests/test_auth.py` | Done — bcrypt, JWT roundtrip, API key generation |
| `tests/test_models.py` | Done — all Pydantic models |
| `tests/test_retrieval.py` | Done — search_docs, search_code, fetch_page with mocks |

### Scripts
| File | Purpose |
|---|---|
| `scripts/seed_demo.py` | Creates demo tenant + indexes Stripe/MongoDB/FastAPI/Tailwind/Redis |
| `scripts/test_mcp_endpoint.py` | JSON-RPC 2.0 endpoint tester |
| `scripts/deploy.sh` | SAM build + deploy wrapper |

---

## 2. AWS Resources to Create BEFORE Deployment

These must exist before `sam deploy`. The SAM template creates most of them, but **OpenSearch Serverless** must be pre-provisioned.

### 2a. OpenSearch Serverless Collection (Manual)

SAM cannot create AOSS collections. Create via Console or CLI:

```bash
# Create security policy
aws opensearchserverless create-security-policy \
  --name knowledgemcp-encryption \
  --type encryption \
  --policy '{"Rules":[{"ResourceType":"collection","Resource":["collection/knowledgemcp"]}],"AWSOwnedKey":true}'

# Create network policy (public access for MVP, restrict later)
aws opensearchserverless create-security-policy \
  --name knowledgemcp-network \
  --type network \
  --policy '[{"Rules":[{"ResourceType":"collection","Resource":["collection/knowledgemcp"]},{"ResourceType":"dashboard","Resource":["collection/knowledgemcp"]}],"AllowFromPublic":true}]'

# Create data access policy (replace ACCOUNT_ID and ROLE_ARN)
aws opensearchserverless create-access-policy \
  --name knowledgemcp-data \
  --type data \
  --policy '[{"Rules":[{"ResourceType":"index","Resource":["index/knowledgemcp/*"],"Permission":["aoss:*"]},{"ResourceType":"collection","Resource":["collection/knowledgemcp"],"Permission":["aoss:*"]}],"Principal":["arn:aws:iam::ACCOUNT_ID:role/knowledgemcp-*"]}]'

# Create collection
aws opensearchserverless create-collection \
  --name knowledgemcp \
  --type VECTORSEARCH \
  --description "KnowledgeMCP vector store"
```

After creation, note the **collection endpoint** (e.g., `https://abc123.us-east-1.aoss.amazonaws.com`). This goes into the `OPENSEARCH_ENDPOINT` parameter.

### 2b. Bedrock Model Access (One-Time)

Enable Titan Embed v2 in the Bedrock console:
1. Go to AWS Console → Bedrock → Model access
2. Request access to `amazon.titan-embed-text-v2:0`
3. Wait for approval (usually instant for Titan)

### 2c. SAM Deployment

```bash
cd knowledgemcp

# First deployment (interactive — will ask for parameter values)
./scripts/deploy.sh

# You'll be prompted for:
#   Stack name: knowledgemcp-stack
#   Region: us-east-1
#   OpenSearchEndpoint: <paste from 2a>
#   EmbeddingProvider: bedrock
#   BedrockModelId: amazon.titan-embed-text-v2:0
#   JwtSecretKey: <generate a strong random string>

# Subsequent deployments
./scripts/deploy.sh quickstart
```

### 2d. Post-Deploy: Note the Outputs

After `sam deploy`, CloudFormation outputs:

| Output | Use |
|---|---|
| `AdminApiUrl` | Frontend `NEXT_PUBLIC_API_URL` |
| `McpServerUrl` | What tenants put in their mcp.json |
| `CrawlQueueUrl` | Already wired via env vars in Lambda |
| `IndexQueueUrl` | Already wired via env vars in Lambda |
| `ContentBucketName` | For file upload destinations |

---

## 3. Rewiring Checklist (What the Deploying Agent Must Do)

### Critical Path (blocks everything)

- [ ] **Create OpenSearch Serverless collection** (Step 2a above)
- [ ] **Enable Bedrock Titan Embed v2** (Step 2b above)
- [ ] **Run `sam deploy --guided`** with correct parameter values
- [ ] **Verify health**: `curl https://<McpServerUrl>/health` → `{"status":"ok"}`

### Post-Deploy Verification

- [ ] **Create a tenant**: `POST <AdminApiUrl>/api/auth/signup` with `{name, email, password}`
- [ ] **Add a source**: `POST <AdminApiUrl>/api/sources` with `{source_type: "website_url", name: "FastAPI", config: {url: "https://fastapi.tiangolo.com", sitemap_url: "https://fastapi.tiangolo.com/sitemap.xml"}}`
- [ ] **Wait for indexing**: Poll `GET <AdminApiUrl>/api/sources` until status is `ready`
- [ ] **Test MCP endpoint**: `python scripts/test_mcp_endpoint.py --url <McpServerUrl> --api-key <tenant_api_key> --tenant <tenant_slug>`
- [ ] **Run seed script**: `ADMIN_API_URL=<AdminApiUrl> python scripts/seed_demo.py`

### Frontend Deployment

```bash
cd knowledgemcp/frontend
npm install

# Set the API URL
echo "NEXT_PUBLIC_API_URL=<AdminApiUrl>" > .env.local

# Build and deploy to S3 + CloudFront (or Vercel/Amplify)
npm run build

# Option A: S3 + CloudFront
aws s3 sync out/ s3://knowledgemcp-frontend-bucket --delete
aws cloudfront create-invalidation --distribution-id <DIST_ID> --paths "/*"

# Option B: Vercel (simpler)
npx vercel --prod
```

---

## 4. Known Gaps to Address During Deployment

### Must Fix Before Production

| Gap | Impact | Fix |
|---|---|---|
| **Rate limiting is in-memory** | Resets per Lambda cold start; useless at scale | Replace `_buckets` dict in `middleware.py` with DynamoDB atomic counter or ElastiCache Redis `INCR` |
| **Tenant slug lookup is a DynamoDB scan** | O(n) on tenant count; slow at >1000 tenants | Add a GSI on `slug` to the TenantsTable (add to `template.yaml`) |
| **No custom domain** | MCP endpoint URL is an ugly API Gateway URL | Add a Route53 record + ACM cert + API Gateway custom domain mapping for `mcp.knowledgemcp.io` |
| **No WAF** | API Gateway is publicly exposed with no DDoS protection | Attach AWS WAF to the HttpApi with rate-limiting rules |

### Should Fix Before Scale

| Gap | Impact | Fix |
|---|---|---|
| **No incremental re-indexing** | Re-index re-crawls everything; slow and wasteful | Before indexing each URL, query DynamoDB for existing `content_hash`. Skip if unchanged. |
| **No dead letter queue** | Failed SQS messages retry forever then vanish | Add DLQs to both `CrawlQueue` and `IndexQueue` in `template.yaml` |
| **No CloudWatch alarms** | Silent failures in Lambda/OpenSearch | Add alarms for Lambda errors, SQS age, OpenSearch 5xx |
| **Crawler Lambda timeout** | 300s may not be enough for large sitemaps (10K+ pages) | Split large sitemaps into batches of 100 URLs per SQS message, fan-out pattern |
| **File upload path** | Frontend uses S3 key, but no presigned URL generation endpoint | Add `POST /api/upload/presign` to admin routes that returns a presigned S3 PUT URL |
| **Wiki/Git connectors are stubs** | Confluence/Notion/GitHub don't work | Implement using `atlassian-python-api`, `notion-client`, and `gitpython` |

### Nice to Have (Post-Launch)

| Feature | Architecture Doc Reference |
|---|---|
| Retrieval Quality Score (public groundedness badge) | Differentiator #1 — needs golden evaluation dataset per tenant |
| Tool Description A/B testing | Differentiator #2 — needs traffic volume to measure activation rates |
| White-label MCP endpoints (`mcp.stripe.dev`) | Differentiator #10 — custom domain per tenant via API Gateway domain mapping |
| Pre-indexed public docs marketplace | Section F — seed 10 popular docs as shared sources |

---

## 5. Environment Variables Reference (Complete)

Copy `.env.example` to `.env` and fill in:

```bash
# Required for AWS
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=<your-account-id>

# Required for search
OPENSEARCH_ENDPOINT=<from step 2a>

# Required for embeddings
EMBEDDING_PROVIDER=bedrock
BEDROCK_MODEL_ID=amazon.titan-embed-text-v2:0
# OR
# EMBEDDING_PROVIDER=openai
# OPENAI_API_KEY=sk-...

# Required for auth (CHANGE THIS)
JWT_SECRET_KEY=<random-64-char-string>

# Created by SAM deploy (auto-populated in Lambda env)
CRAWL_QUEUE_URL=<from CloudFormation output>
INDEX_QUEUE_URL=<from CloudFormation output>
CONTENT_BUCKET=<from CloudFormation output>
TENANTS_TABLE=knowledgemcp-tenants-dev
SOURCES_TABLE=knowledgemcp-sources-dev
ANALYTICS_TABLE=knowledgemcp-analytics-dev

# Optional
SKIP_AUTH=false
DEBUG=false
RATE_LIMIT_PER_SECOND=10
RATE_LIMIT_BURST=30
MAX_QUERIES_PER_HOUR=100
MAX_DOCS_PER_TENANT=500
USER_AGENT=KnowledgeMCP/1.0 (+https://knowledgemcp.io)
CRAWL_DELAY_SECONDS=0.5
```

---

## 6. Architecture Decisions Log

| Decision | Rationale | Trade-off |
|---|---|---|
| Python + FastMCP | MS Learn uses C# MCP SDK; Python FastMCP is the equivalent for the Python ecosystem. Matches team skills. | Slightly higher Lambda cold-start than compiled C# |
| Single OpenSearch index per tenant | Simplest multi-tenant isolation model. Each tenant gets `knowledgemcp-{tenant_id}` index. | Index count grows linearly with tenants — AOSS has a 100-index soft limit |
| Hybrid search (BM25 0.4 + vector 0.6) via script_score | Proven weights from MS Learn team. Avoids OpenSearch neural search plugin dependency. | `script_score` is slower than native neural plugin for very large indexes |
| MMR re-ranking in application layer | Avoids OpenSearch plugin dependency, gives full control over diversity tuning | Adds ~10ms Python-side compute per query |
| Rule-based query expansion (not LLM) | Avoids extra API call latency and cost per query | Less capable than LLM rewriting for complex queries |
| Tenant context via contextvars | Thread-safe, async-safe, no global state. Same pattern as Django/Flask request context. | Tools must be called within a request context |
| Code blocks in same index (is_code flag) | Simpler than maintaining two indexes. Code search is just a filter. | Large indexes with many code blocks may benefit from a separate index |
| Mangum for Lambda ASGI | Standard adapter, minimal overhead, supports API Gateway v2 | Adds ~20ms cold-start overhead |

---

## 7. File Tree (For Quick Reference)

```
knowledgemcp/
├── docs/
│   ├── KnowledgeMCP_Architecture.md    # Product architecture reference
│   └── PROMPT_2_Implementation.md      # Original implementation brief
├── infra/
│   ├── template.yaml                   # AWS SAM template
│   └── samconfig.toml                  # SAM deploy config
├── src/
│   ├── common/                         # Config, models, AWS clients, DynamoDB
│   ├── crawler/                        # Ingestion: sitemap, page fetch, file proc, connectors
│   ├── indexer/                        # Chunking, embedding, OpenSearch indexing
│   ├── mcp_server/                     # FastMCP tools, retrieval, middleware, ASGI handler
│   ├── admin/                          # REST API for tenant/source management
│   └── analytics/                      # Query logging and reporting
├── tests/                              # pytest suite
├── scripts/                            # seed_demo, test_mcp_endpoint, deploy.sh
├── frontend/                           # Next.js 14 dashboard
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
├── .env.example
├── SCAFFOLD.md
└── README.md
```
