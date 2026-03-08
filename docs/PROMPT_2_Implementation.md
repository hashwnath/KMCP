# PROMPT 2: KnowledgeMCP — Full Autonomous Implementation on AWS

## YOUR ROLE

You are a senior full-stack engineer and AI infrastructure architect. You will build the complete **KnowledgeMCP MVP** — a platform that takes any documentation site URL and produces a working remote MCP endpoint, exactly like Microsoft's MS Learn MCP Server (`https://learn.microsoft.com/api/mcp`).

You must be **fully autonomous**: plan, scaffold, implement, test, and make it deployment-ready. I will deploy it separately on my AWS account after you're done.

---

## CRITICAL: SCAFFOLD FILE

Before writing ANY code, create and maintain a file called `SCAFFOLD.md` in the project root. This is the **implementation brain** — a living document that tracks:

1. **Architecture decisions** (what and why)
2. **File tree** (every file, its purpose, its status: planned/in-progress/done)
3. **Implementation order** (what to build first, dependencies)
4. **Current state** (what's done, what's next, what's blocked)
5. **Config needed for deployment** (AWS resources, env vars, secrets)
6. **Known issues / tech debt**
7. **Test results** (what was tested, what passed/failed)

**Update SCAFFOLD.md after EVERY significant code change.** It must always reflect the true state of the codebase.

---

## WHAT TO BUILD

### This is an END-TO-END PRODUCT — not just a backend.

A real user (DevRel lead, docs engineer, or developer) should be able to:
1. Land on the website and immediately understand what this does
2. Sign up (email + password or magic link)
3. Add content via ANY of these methods:
   - **Paste a docs site URL** (public docs crawl — the simplest path)
   - **Drag-and-drop files** (PDFs, DOCX, PPTX, Markdown, HTML, TXT — batch upload up to 100 files)
   - **Connect a cloud storage bucket** (AWS S3, Azure Blob Storage, Google Cloud Storage — provide bucket URL + credentials)
   - **Connect a wiki/knowledge base** (Confluence, Notion, SharePoint, GitBook — OAuth or API key)
   - **Connect a Git repo** (GitHub/GitLab — point at a `docs/` folder)
   - **Paste raw text/markdown** (for quick testing — inline editor)
4. Watch real-time indexing progress (regardless of source type)
5. Get their MCP endpoint URL + a ready-to-copy mcp.json snippet
6. See a "How to Connect" guide (VS Code, Cursor, Claude Code — with screenshots/instructions)
7. Come back later and see usage analytics (queries, top searches, content gaps)
8. Manage their sources (add/remove sources, re-index, delete, mix multiple source types in one endpoint)

The AI agent end-user (developer using Copilot/Cursor) should be able to:
1. Paste the mcp.json snippet into their editor config
2. Immediately discover 3 tools and start querying the docs

### The Full Product Breakdown

#### A. Landing Page & Marketing Site
- Hero: "Give your docs an MCP endpoint. Every AI agent can use them."
- How it works: 3 steps with visuals (Paste URL → We index → Copy MCP endpoint)
- Pre-indexed demo: "Try it now with Stripe Docs" (live demo link)
- Pricing section (Free tier: 500 pages, 1000 queries/mo | Pro: $99/mo)
- "Get Started" CTA → goes to signup

#### B. Auth & Onboarding
- Signup: Email + password (or magic link via SES)
- After signup → onboarding wizard:
  - Step 1: "How do you want to add your content?" — user picks one:
    ```
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │  🌐 Website  │ │  📄 Upload   │ │  ☁️ Cloud    │
    │  URL         │ │  Files       │ │  Storage     │
    │              │ │  (drag&drop) │ │  (S3/Blob/   │
    │  Paste your  │ │  PDF, DOCX,  │ │   GCS)       │
    │  docs URL    │ │  MD, HTML    │ │              │
    └──────────────┘ └──────────────┘ └──────────────┘
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │  📝 Wiki /   │ │  🔗 Git Repo │ │  ✏️ Paste    │
    │  Knowledge   │ │              │ │  Text        │
    │  Base        │ │  GitHub /    │ │              │
    │  Confluence, │ │  GitLab      │ │  Raw MD or   │
    │  Notion,     │ │  docs/folder │ │  text editor │
    │  SharePoint  │ │              │ │              │
    └──────────────┘ └──────────────┘ └──────────────┘
    ```
  - Step 2: Source-specific config:
    - **Website URL**: paste URL (we auto-detect sitemap)
    - **Upload Files**: drag-and-drop zone (accepts PDF, DOCX, PPTX, MD, HTML, TXT, up to 100 files / 500MB)
    - **Cloud Storage**: bucket URL + access key/secret (or IAM role ARN for S3)
    - **Wiki/KB**: select provider → OAuth flow or API key + workspace URL
    - **Git Repo**: repo URL + branch + folder path (e.g., `docs/`)
    - **Paste Text**: inline markdown editor with preview
  - Step 3: "Choose a name for your endpoint" (e.g., `stripe-docs`)
  - Step 4: Click "Start Indexing"
- JWT-based auth for admin dashboard API

#### C. Dashboard (the main product UI)
- **Home / Overview**
  - Status card: "Your MCP endpoint is READY" (green) or "Indexing... 347/1200 pages" (progress bar)
  - MCP endpoint URL: `https://mcp.knowledgemcp.io/{tenant-slug}`
  - Copy-paste mcp.json snippet (pre-formatted for VS Code, Cursor, Claude)
  - Quick stats: Total queries today, total pages indexed, last sync time

- **Sources Page**
  - List of ALL connected sources (mixed types in one endpoint)
  - Each source shows: type icon (🌐/📄/☁️/📝/🔗/✏️), name, status, doc count, last sync
  - **"Add Source" button** → opens same 6-option picker from onboarding (can add more sources to existing endpoint)
  - Per-source controls:
    - Status: pages found, pages indexed, last crawl/sync, errors
    - "Re-index now" button
    - "Delete source" button
    - Sync schedule: Manual only / Every hour / Every day / Every week
  - **Source types supported**:
    - 🌐 Website URL (sitemap crawl)
    - 📄 Uploaded Files (PDF, DOCX, PPTX, MD, HTML, TXT)
    - ☁️ Cloud Storage (S3 bucket, Azure Blob container, GCS bucket)
    - 📝 Wiki/KB (Confluence space, Notion workspace, SharePoint site)
    - 🔗 Git Repo (GitHub/GitLab repo + branch + path)
    - ✏️ Pasted Text (raw markdown/text snippets)
  - **Multiple sources merge into ONE search index** — agents search across all sources seamlessly

- **Analytics Page**
  - Query volume over time (chart)
  - Top 20 queries this week
  - "Content Gaps" — queries that returned low-confidence or zero results (THIS IS THE KILLER FEATURE)
  - Tool usage breakdown (docs_search vs code_search vs docs_fetch)

- **Settings Page**
  - API key management (regenerate key)
  - Endpoint slug customization
  - Rate limit config
  - Account info / billing

- **"How to Connect" Page** (always accessible)
  - Tab 1: VS Code / GitHub Copilot — step-by-step with mcp.json snippet
  - Tab 2: Cursor — step-by-step
  - Tab 3: Claude Code — step-by-step
  - Tab 4: Claude Desktop — step-by-step
  - Tab 5: Generic MCP client — raw URL + headers

#### D. MCP Server (the backend core)
- Remote MCP endpoint accessible at `https://mcp.knowledgemcp.io/{tenant-slug}`
- Streamable HTTP transport (JSON-RPC 2.0)
- 3 tools per tenant:
  - `docs_search` — semantic search (returns top 10 chunks, ~500 tokens each, with title + URL + excerpt)
  - `code_sample_search` — code-specific search with language filter (returns top 20 code snippets)
  - `docs_fetch` — fetch full page content as clean markdown
- API key auth via header (`x-api-key`)
- Rate limiting per tenant
- CORS headers for cross-origin MCP clients
- Request logging for analytics

#### E. Crawl + Index Pipeline (the engine)
- Async pipeline: User submits URL → SQS queue → Lambda crawls → Lambda chunks+embeds → OpenSearch indexed
- Real-time progress updates (WebSocket or polling from dashboard)
- Incremental re-indexing on schedule or manual trigger
- Code block extraction + language classification as separate index

#### F. Pre-indexed Public Docs (for instant gratification)
- On launch, pre-index 5-10 popular docs sites:
  - Stripe, MongoDB, Cloudflare, Tailwind CSS, Supabase, Redis, FastAPI, Next.js, Prisma, Hono
- These are available to ALL users without indexing wait
- Users can "claim" a pre-indexed site to get their own endpoint with analytics

---

## TECH STACK (AWS)

| Component | AWS Service | Why |
|---|---|---|
| **MCP Server** | Lambda + API Gateway (HTTP) OR ECS Fargate | Serverless for cost; Fargate if need persistent connections |
| **Search Index** | OpenSearch Serverless | Vector + keyword hybrid search, semantic ranking |
| **Embeddings** | Amazon Bedrock (Titan Embed v2) OR OpenAI API | Bedrock stays in AWS; OpenAI if quality matters more |
| **Object Storage** | S3 | Raw docs + processed chunks + markdown cache |
| **Metadata DB** | DynamoDB | Tenant config, indexing state, usage counters |
| **Web Crawler** | Lambda + SQS (async crawl pipeline) | Scale with queue, process pages independently |
| **Document Processing** | Built-in (HTML parsing + markdown conversion) | No need for Textract for public web pages |
| **Admin API** | Lambda + API Gateway (REST) | Simple CRUD for tenants/sources |
| **Admin UI** | Static site on S3 + CloudFront | React/Next.js or plain HTML |
| **Secrets** | SSM Parameter Store | API keys, OpenAI key if used |
| **IaC** | AWS CDK (Python) or SAM | Reproducible deployment |

### Language Choice

- **Python** for everything (crawler, embeddings, MCP server, admin API)
- Use **FastMCP** (Python MCP SDK) for the MCP server layer
- Use **BeautifulSoup + httpx** for crawling
- Use **boto3** for all AWS interactions

---

## ARCHITECTURE REFERENCE

Read this carefully — it's from the actual MS Learn product team:

### MS Learn's 3-Tool Pattern (replicate this exactly)
- `docs_search`: Hybrid search (keyword + vector). Returns title, URL, excerpt. Max 10 results, ~500 tokens each.
- `code_sample_search`: Separate index for code blocks. Language-classified. Returns code + surrounding context.
- `docs_fetch`: Fetch full page, convert to clean markdown, strip nav/header/footer.

### MS Learn's 6 Lessons (follow all of these)
1. **"Your API is not an MCP tool"** — Keep tools simple: search + fetch. Don't expose internal params.
2. **Remote servers = distributed systems** — Handle CORS, statelessness, graceful errors.
3. **Tool descriptions are your agent UX** — Spend time on descriptions. They determine if agents use the tool.
4. **Compose tools for better outcomes** — Descriptions should teach search→fetch pattern.
5. **Defend against hardcoded callers** — Support parameter aliases during changes.
6. **Let data drive iteration** — Log queries, track usage, identify patterns.

### RAG Best Practices (from Azure AI Search docs)
- Hybrid search: BM25 (keyword) + vector similarity for maximum recall
- Semantic re-ranking on top of hybrid results
- Chunk size: 512-1024 tokens with 10% overlap
- Preserve code blocks as complete units (don't split mid-code)
- Metadata propagation: every chunk carries source URL, title, section hierarchy

---

## PROJECT STRUCTURE

```
knowledgemcp/
├── SCAFFOLD.md                    # Living implementation brain (update constantly)
├── README.md                      # How to deploy, configure, use
├── requirements.txt               # Python dependencies
├── pyproject.toml                 # Project config
│
├── infra/                         # Infrastructure as Code
│   ├── template.yaml              # SAM template OR
│   └── cdk/                       # CDK app (if using CDK)
│       ├── app.py
│       └── stacks/
│           ├── crawl_stack.py
│           ├── search_stack.py
│           ├── mcp_stack.py
│           └── admin_stack.py
│
├── src/
│   ├── common/                    # Shared utilities
│   │   ├── config.py              # Environment config, constants
│   │   ├── models.py              # Data models (Tenant, Source, Document, Chunk)
│   │   └── aws_clients.py         # Boto3 client factories
│   │
│   ├── crawler/                   # Content ingestion pipeline
│   │   ├── handler.py             # Lambda handler for crawl/ingest jobs (routes by source type)
│   │   ├── sitemap_parser.py      # Parse sitemap.xml to get all URLs
│   │   ├── page_fetcher.py        # Fetch individual web pages (httpx)
│   │   ├── html_to_markdown.py    # Clean HTML → Markdown conversion
│   │   ├── code_extractor.py      # Detect and extract code blocks with language
│   │   ├── metadata_extractor.py  # Extract title, description, breadcrumbs
│   │   ├── file_processor.py      # Process uploaded files (PDF→text, DOCX→text, PPTX→text, MD passthrough)
│   │   ├── s3_connector.py        # List + fetch objects from S3/GCS/Azure Blob
│   │   ├── wiki_connector.py      # Confluence, Notion, SharePoint API connectors
│   │   ├── git_connector.py       # Clone repo, read docs/ folder, extract files
│   │   └── text_ingestor.py       # Handle raw pasted text/markdown
│   │
│   ├── indexer/                   # Chunking + Embedding + Indexing
│   │   ├── handler.py             # Lambda handler for index jobs
│   │   ├── chunker.py             # Semantic chunking (512-1024 tokens, 10% overlap)
│   │   ├── embedder.py            # Generate embeddings (Bedrock Titan or OpenAI)
│   │   ├── opensearch_client.py   # OpenSearch index management
│   │   └── code_indexer.py        # Separate code sample indexing
│   │
│   ├── mcp_server/                # The MCP endpoint (the core product)
│   │   ├── handler.py             # Lambda/Fargate entry point
│   │   ├── server.py              # FastMCP server setup + tool registration
│   │   ├── tools/
│   │   │   ├── docs_search.py     # docs_search tool implementation
│   │   │   ├── code_search.py     # code_sample_search tool implementation
│   │   │   └── docs_fetch.py      # docs_fetch tool implementation
│   │   ├── retrieval.py           # Search logic (hybrid: BM25 + vector + rerank)
│   │   └── middleware.py          # Auth, rate limiting, CORS, logging
│   │
│   ├── admin/                     # Admin API
│   │   ├── handler.py             # Lambda handler
│   │   ├── routes.py              # REST routes (create tenant, add source, status)
│   │   └── auth.py                # API key validation
│   │
│   └── analytics/                 # Usage tracking
│       ├── logger.py              # Log queries to DynamoDB/S3
│       └── reporter.py            # Basic stats (query count, top queries, gaps)
│
├── tests/
│   ├── test_crawler.py
│   ├── test_chunker.py
│   ├── test_embedder.py
│   ├── test_mcp_server.py
│   ├── test_retrieval.py
│   └── test_tools.py
│
├── scripts/
│   ├── seed_demo.py               # Pre-index popular docs (Stripe, MongoDB, etc.)
│   ├── test_mcp_endpoint.py       # Hit the MCP endpoint and verify tools work
│   └── deploy.sh                  # Deployment helper
│
├── frontend/                      # Full product web UI (Next.js)
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── public/
│   │   ├── favicon.ico
│   │   └── og-image.png
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx          # Root layout (nav, footer)
│   │   │   ├── page.tsx            # Landing page (hero, how-it-works, pricing, CTA)
│   │   │   ├── login/page.tsx      # Login page
│   │   │   ├── signup/page.tsx     # Signup page
│   │   │   ├── onboarding/page.tsx # "How do you want to add content?" 6-option picker → source config → name endpoint → start indexing
│   │   │   └── dashboard/
│   │   │       ├── page.tsx         # Overview (status, MCP URL, copy snippet, quick stats)
│   │   │       ├── sources/page.tsx # Manage sources (add, re-index, delete)
│   │   │       ├── analytics/page.tsx # Usage charts, top queries, content gaps
│   │   │       ├── connect/page.tsx # How to Connect guide (VS Code, Cursor, Claude tabs)
│   │   │       └── settings/page.tsx # API keys, endpoint config, account
│   │   ├── components/
│   │   │   ├── Navbar.tsx
│   │   │   ├── Footer.tsx
│   │   │   ├── McpSnippet.tsx      # Copy-paste mcp.json block with syntax highlight
│   │   │   ├── IndexingProgress.tsx # Real-time progress bar (polls API)
│   │   │   ├── QueryChart.tsx      # Usage chart (recharts or chart.js)
│   │   │   ├── ContentGaps.tsx     # Table of queries with no/low results
│   │   │   ├── SourceCard.tsx      # Source status card (shows type icon + status)
│   │   │   ├── SourcePicker.tsx    # 6-option grid (URL / Upload / Cloud / Wiki / Git / Paste)
│   │   │   ├── FileUploadZone.tsx  # Drag-and-drop zone for PDFs/DOCX/MD (with file list + progress)
│   │   │   ├── CloudStorageForm.tsx # Bucket URL + credentials form (S3/Blob/GCS)
│   │   │   ├── WikiConnectForm.tsx  # OAuth/API key form for Confluence/Notion/SharePoint
│   │   │   ├── GitRepoForm.tsx     # Repo URL + branch + path form
│   │   │   ├── TextEditor.tsx      # Inline markdown editor for paste-text source
│   │   │   └── ConnectGuide.tsx    # Tabbed guide for each MCP client
│   │   ├── lib/
│   │   │   ├── api.ts              # Fetch wrapper for admin API
│   │   │   └── auth.ts             # JWT token management
│   │   └── styles/
│   │       └── globals.css         # Tailwind base styles
│   └── tsconfig.json
│
└── .env.example                   # Required environment variables template
```

---

## IMPLEMENTATION ORDER (follow this strictly)

### Phase 1: Foundation (do first)
1. Create SCAFFOLD.md
2. Set up project structure + requirements.txt
3. Implement `common/` (config, models, AWS clients)
4. Implement `crawler/` core:
   a. `handler.py` — job router that dispatches by source type
   b. `sitemap_parser.py` + `page_fetcher.py` + `html_to_markdown.py` — website URL crawl path
   c. `file_processor.py` — uploaded file processing (PDF via PyMuPDF/pdfplumber, DOCX via python-docx, MD passthrough)
   d. `s3_connector.py` — list objects in S3/Blob/GCS bucket, fetch each, route to file_processor
   e. `wiki_connector.py` — Confluence REST API, Notion API, SharePoint Graph API (start with Confluence + Notion for MVP)
   f. `git_connector.py` — shallow clone, walk docs/ folder, read files
   g. `text_ingestor.py` — accept raw text, wrap with metadata
   h. `code_extractor.py` + `metadata_extractor.py` — shared across all source types
5. Test each connector:
   - Website: crawl `https://docs.stripe.com/sitemap.xml`
   - File upload: process a batch of 10 PDFs + 5 markdown files
   - S3: read from a test bucket with mixed file types
   - Raw text: ingest a pasted markdown document

### Phase 2: Intelligence (do second)
6. Implement `indexer/chunker.py` (semantic chunking)
7. Implement `indexer/embedder.py` (embedding generation)
8. Implement `indexer/opensearch_client.py` (create indexes, push chunks)
9. Implement `indexer/code_indexer.py` (separate code index)
10. Test: crawl + chunk + embed + index a real docs site

### Phase 3: MCP Server (the core — do third)
11. Implement `mcp_server/server.py` (FastMCP setup with Streamable HTTP)
12. Implement `mcp_server/tools/docs_search.py`
13. Implement `mcp_server/tools/code_search.py`
14. Implement `mcp_server/tools/docs_fetch.py`
15. Implement `mcp_server/retrieval.py` (hybrid search logic)
16. Implement `mcp_server/middleware.py` (auth, rate limit, CORS)
17. Test: connect from VS Code MCP client and verify all 3 tools work

### Phase 4: Admin + Ops (do fourth)
18. Implement `admin/` (tenant CRUD, source management, status)
19. Implement `analytics/` (query logging, basic stats)
20. Write deployment scripts / IaC

### Phase 5: Frontend — Full Product Web UI (do fifth)
21. Scaffold Next.js app in `frontend/` with Tailwind CSS
22. Build Landing Page (`page.tsx`): Hero, How-it-works (3 steps), pre-indexed demo links, pricing, CTA
23. Build Auth Pages: Signup + Login (call admin API, store JWT)
24. Build Onboarding Wizard: Paste URL → name endpoint → start indexing → redirect to dashboard
25. Build Dashboard Overview: Status card (ready/indexing), MCP URL display, copy-paste mcp.json snippet, quick stats
26. Build Sources Page: List sources, add new, re-index, delete. Show per-source status + progress.
27. Build Analytics Page: Query volume chart, top queries table, Content Gaps table (killer feature)
28. Build Connect Guide Page: Tabbed guide for VS Code, Cursor, Claude Code, Claude Desktop, Generic
29. Build Settings Page: API key management, endpoint slug, rate limits
30. Test: Full user journey from signup → paste URL → see indexing → copy snippet → use in VS Code

### Phase 6: Polish & Launch Prep (do last)
31. Pre-index 5-10 popular docs sites (Stripe, MongoDB, Cloudflare, Tailwind, Supabase, etc.)
32. Add "Try with Stripe Docs" instant demo button on landing page
33. Write README with full deployment instructions
34. Create Product Hunt assets: demo GIF, tagline, description
35. Final SCAFFOLD.md update

---

## QUALITY GATES (self-evaluate at each phase)

Before moving to the next phase, verify:

- [ ] All code follows Python best practices (type hints, docstrings, error handling)
- [ ] No hardcoded secrets or credentials anywhere
- [ ] All AWS interactions use boto3 with proper error handling and retries
- [ ] Chunking preserves code blocks as complete units
- [ ] Search results include source URL, title, and excerpt (for citations)
- [ ] MCP tool descriptions follow MS Learn's patterns (teach agents the search→fetch workflow)
- [ ] Rate limiting prevents abuse
- [ ] CORS headers allow cross-origin MCP clients
- [ ] Logging captures enough data to debug issues
- [ ] Tests pass for the completed phase

---

## RESEARCH BEFORE CODING

Before writing any implementation code, research:

1. **FastMCP Python SDK** — Read the docs/README at https://github.com/jlowin/fastmcp. Understand how to create tools, handle Streamable HTTP transport, and configure for remote hosting.
2. **OpenSearch vector search** — Read how to create a kNN index, hybrid queries (BM25 + kNN), and semantic re-ranking.
3. **Amazon Bedrock Titan Embeddings** — Read the API for `amazon.titan-embed-text-v2:0`. Understand input/output format and batch limits.
4. **MCP Streamable HTTP Transport** — Read the MCP spec for how remote HTTP servers work. Understand the JSON-RPC 2.0 message format.
5. **Sitemap.xml parsing** — Standard format for discovering all pages on a docs site.

---

## DEPLOYMENT CONFIG TEMPLATE

The final deliverable must include a `.env.example` with all required config:

```env
# AWS
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=

# OpenSearch
OPENSEARCH_ENDPOINT=
OPENSEARCH_COLLECTION_NAME=knowledgemcp

# Embeddings (choose one)
EMBEDDING_PROVIDER=bedrock  # or "openai"
OPENAI_API_KEY=             # only if using openai
BEDROCK_MODEL_ID=amazon.titan-embed-text-v2:0

# MCP Server
MCP_SERVER_PORT=8080
MCP_SERVER_HOST=0.0.0.0

# Admin
ADMIN_API_KEY=              # master admin key

# Rate Limiting
MAX_QUERIES_PER_HOUR=100
MAX_DOCS_PER_TENANT=500

# Pre-indexed sites (comma-separated sitemap URLs)
SEED_SITES=https://docs.stripe.com/sitemap.xml,https://docs.mongodb.com/sitemap.xml
```

---

## FINAL DELIVERABLE CHECKLIST

- [ ] `SCAFFOLD.md` fully up-to-date with final state
- [ ] All source code in `src/`
- [ ] IaC templates in `infra/`
- [ ] Tests in `tests/`
- [ ] `.env.example` with all required config
- [ ] `README.md` with:
  - What this is
  - How to deploy on AWS
  - How to add a docs site
  - How to connect from VS Code / Cursor / Claude
  - Example mcp.json snippet
- [ ] `scripts/seed_demo.py` to pre-index popular docs
- [ ] `scripts/deploy.sh` to deploy everything

---

## CONSTRAINTS

- **Backend: Python only** (crawler, indexer, MCP server, admin API)
- **Frontend: Next.js + TypeScript + Tailwind CSS** (the web UI)
- **AWS only** (no Azure/GCP services)
- **No Docker** required for development (Lambda functions via SAM CLI, Next.js via `npm run dev`)
- **Budget-conscious**: Use serverless where possible. OpenSearch Serverless OR a small self-managed instance on EC2. Frontend on S3 + CloudFront.
- **Self-contained**: After you're done, I should be able to:
  - Backend: `cd knowledgemcp && ./scripts/deploy.sh` → deploys all Lambda functions, API Gateway, OpenSearch, DynamoDB
  - Frontend: `cd knowledgemcp/frontend && npm run build && ./scripts/deploy-frontend.sh` → deploys to S3 + CloudFront
- **Mobile responsive**: Dashboard must work on tablet/mobile (Tailwind handles this)
- **Dark mode**: Support both light and dark mode (Tailwind dark: classes)

---

## START NOW

1. Create the `knowledgemcp/` folder
2. Create `SCAFFOLD.md` with initial plan
3. Begin Phase 1

Be autonomous. Be thorough. Research before implementing. Test after implementing. Update SCAFFOLD.md constantly.
