# KnowledgeMCP — "Your MS Learn MCP Server, for Any Company"

> **One-liner**: Give your docs a URL. Every AI agent on earth can use them.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Market Gap — 117 Companies Without Docs MCP](#2-market-gap)
3. [Core Principles (from MS Learn Product Team)](#3-core-principles)
4. [MS Learn MCP Server — How It's Built (Official)](#4-ms-learn-architecture)
5. [KnowledgeMCP — Generic Architecture](#5-knowledgemcp-architecture)
6. [Novel Differentiators & USP](#6-novel-differentiators--usp)
7. [Competitive Landscape](#7-competitive-landscape)
8. [Enterprise Buying Criteria Scoring](#8-enterprise-buying-criteria)
9. [Investor Criteria](#9-investor-criteria)
10. [Appendix: Full Company Gap List](#10-appendix-full-company-gap-list)

---

## 1. Problem Statement

AI agents (GitHub Copilot, Cursor, Claude, Windsurf, etc.) need to ground their responses in official, up-to-date documentation. Today, only **Microsoft** (MS Learn MCP Server) and **AWS** (AWS Knowledge MCP + AWS Documentation MCP) have built dedicated **Knowledge/Docs MCP servers** — remote endpoints that AI agents can discover and use to search and read official docs.

**117 major companies** have no such equivalent. Many have active MCP programs (operational/management servers) but zero documentation/knowledge MCP servers.

**The opportunity**: A platform where any company plugs in their docs and gets back a production-grade remote MCP endpoint — their own "MS Learn MCP Server" — without building the RAG pipeline, the MCP protocol layer, or the operational infrastructure.

---

## 2. Market Gap

### Companies WITH Docs/Knowledge MCP (only 3)

| Company | Server | Type |
|---|---|---|
| Microsoft | MS Learn MCP Server (`https://learn.microsoft.com/api/mcp`) | Remote HTTP |
| AWS | AWS Knowledge MCP + AWS Documentation MCP | Remote + Local |
| LangChain | `https://docs.langchain.com/mcp` | Remote HTTP |

### Companies WITH Ops MCP but NO Docs MCP (46 companies)

| Company | Has Ops MCP? | Docs Size | Gap |
|---|---|---|---|
| Google Cloud (GCP) | Yes (Cloud Run, GKE, Gemini Cloud Assist) | Massive | No GCP docs search MCP |
| Oracle | Yes (oracle/mcp — OCI, DB tools) | Massive | No Oracle docs MCP |
| IBM | Yes (IBM/mcp — 20+ servers) | Massive | No IBM docs MCP |
| Alibaba Cloud | Yes (aliyun/* — CloudOps, ACK, etc.) | Large | No Alibaba docs MCP |
| Cloudflare | Yes (3.5K stars, Workers/KV/R2) | Large | No Cloudflare docs MCP |
| Snowflake | Yes (Snowflake-Labs/mcp) | Large | No Snowflake docs MCP |
| Databricks | Yes (databrickslabs/mcp) | Large | No Databricks docs MCP |
| MongoDB | Yes (mongodb-js, 940 stars) | Large | No MongoDB docs MCP |
| HashiCorp | Yes (Terraform + Vault MCP) | Large | No HashiCorp docs MCP |
| Elastic | Yes (mcp-server-elasticsearch) | Large | No Elastic docs MCP |
| Stripe | Yes (stripe/ai, 1.3K stars) | Large | No Stripe docs MCP |
| Confluent | Yes (mcp-confluent) | Large | No Confluent docs MCP |
| Atlassian | Yes (atlassian-mcp-server, 396 stars) | Large | No Atlassian docs MCP |
| PagerDuty | Yes (pagerduty-mcp-server) | Medium | No PagerDuty docs MCP |
| Okta | Yes (okta-mcp-server) | Large | No Okta docs MCP |
| CrowdStrike | Yes (falcon-mcp, 115 stars) | Medium | No CrowdStrike docs MCP |
| Vercel | Yes (mcp-handler, Next.js devtools) | Large | No Vercel docs MCP |
| Netlify | Yes (netlify-mcp) | Medium | No Netlify docs MCP |
| SAP | Yes (mdk-mcp-server) | Massive | No SAP docs MCP |
| Shopify | Yes (dev-mcp) | Large | No Shopify docs MCP |
| Grafana | Yes (mcp-grafana, official) | Large | No Grafana docs MCP |
| Sentry | Yes (sentry-mcp, official) | Medium | No Sentry docs MCP |
| Supabase | Yes (supabase-mcp, official) | Medium | No Supabase docs MCP |
| Docker | Yes (hub-mcp, official) | Large | No Docker docs MCP |
| Redis | Yes (mcp-redis, official) | Medium | No Redis docs MCP |
| Pulumi | Yes (mcp-server, official) | Medium | No Pulumi docs MCP |
| ClickHouse | Yes (mcp-clickhouse) | Medium | No ClickHouse docs MCP |
| Neo4j | Yes (mcp-neo4j) | Medium | No Neo4j docs MCP |
| Dynatrace | Yes (dynatrace-mcp, official) | Large | No Dynatrace docs MCP |
| Snyk | Yes (studio-mcp, official) | Medium | No Snyk docs MCP |
| PostHog | Yes (posthog/mcp) | Medium | No PostHog docs MCP |
| CircleCI | Yes (mcp-server-circleci) | Medium | No CircleCI docs MCP |
| Buildkite | Yes (buildkite-mcp-server) | Medium | No Buildkite docs MCP |
| Bitrise | Yes (bitrise-mcp) | Medium | No Bitrise docs MCP |
| Neon | Yes (mcp-server-neon) | Medium | No Neon docs MCP |
| PlanetScale | Yes (CLI MCP) | Medium | No PlanetScale docs MCP |
| Infobip | Yes (infobip/mcp, official) | Medium | No Infobip docs MCP |
| LINE | Yes (line-bot-mcp-server) | Medium | No LINE docs MCP |
| Chargebee | Yes (chargebee/mcp) | Medium | No Chargebee docs MCP |
| Couchbase | Yes (mcp-server-couchbase) | Medium | No Couchbase docs MCP |
| Weaviate | Yes (mcp-server-weaviate) | Medium | No Weaviate docs MCP |
| Qdrant | Yes (mcp-server-qdrant) | Medium | No Qdrant docs MCP |
| Pinecone | Yes (assistant-mcp) | Medium | No Pinecone docs MCP |
| dbt Labs | Yes (dbt-mcp, official) | Medium | No dbt docs MCP |
| JetBrains | Yes (mcpProxy, official) | Massive | No JetBrains docs MCP |
| Xero | Yes (xero-mcp-server) | Medium | No Xero docs MCP |

### Companies with NO MCP At All (71 companies)

| Company | Docs Size | Category |
|---|---|---|
| Apple | Massive | Big Tech |
| Meta / Facebook | Massive | Big Tech |
| Cisco | Very Large | Networking |
| VMware / Broadcom | Very Large | Infra/Cloud |
| Red Hat | Very Large | Linux/Cloud |
| Twilio | Large | Communication |
| Datadog | Large | Observability |
| ServiceNow | Very Large | ITSM |
| GitLab | Large | DevOps |
| Salesforce | Massive | CRM/Cloud |
| Huawei Cloud | Large | Cloud |
| DigitalOcean | Medium (archived MCP) | Cloud |
| Splunk | Large | Security/SIEM |
| Palantir | Medium | Data Analytics |
| Workday | Large | HR/ERP |
| Adobe | Very Large | Creative/Cloud |
| Autodesk | Large | CAD/Design |
| Intuit | Large | Finance |
| Zendesk | Large | Support |
| HubSpot | Large | CRM/Marketing |
| Zoom | Medium | Communication |
| Slack | Large | Communication |
| Akamai | Large | CDN/Security |
| Fastly | Medium | CDN |
| New Relic | Large | Observability |
| Palo Alto Networks | Large | Security |
| Fortinet | Large | Security |
| Zscaler | Medium | Security |
| SentinelOne | Medium | Security |
| Tencent Cloud | Very Large | Cloud |
| Baidu Cloud | Large | Cloud |
| Samsung (SmartThings/Knox) | Large | IoT/Mobile |
| NVIDIA | Very Large | AI/GPU |
| Intel | Large | Hardware/AI |
| AMD | Medium | Hardware/GPU |
| Arm | Large | Hardware |
| Unity | Large | Gaming |
| Epic Games (Unreal) | Large | Gaming |
| Spotify | Medium | Music/API |
| PayPal | Large | Payments |
| Square / Block | Large | Payments |
| Mapbox | Large | Mapping |
| Algolia | Medium | Search |
| Auth0 | Large | Identity |
| Firebase | Large | Mobile/Backend |
| Heroku | Large | PaaS |
| Linode/Akamai Cloud | Medium | Cloud |
| Rackspace | Medium | Cloud |
| OVHcloud | Medium | Cloud |
| Hetzner | Medium | Cloud |
| Vultr | Medium | Cloud |
| Nutanix | Large | Infra |
| Dell Technologies | Large | Hardware/Cloud |
| HPE | Large | Hardware/Cloud |
| Arista Networks | Medium | Networking |
| Juniper Networks | Large | Networking |
| F5 Networks | Medium | Networking |
| Puppet | Medium | DevOps |
| Chef / Progress | Medium | DevOps |
| Ansible (community) | Large | DevOps |
| Kong | Medium | API Gateway |
| MuleSoft (Salesforce) | Large | Integration |
| Tableau (Salesforce) | Large | BI/Analytics |
| Qlik | Large | BI/Analytics |
| Talend | Medium | Data Integration |
| Informatica | Large | Data Integration |
| Apigee (Google) | Medium | API Management |
| ThoughtSpot | Medium | BI/Analytics |
| Miro | Medium | Collaboration |

### Summary

| Category | Count |
|---|---|
| Companies WITH Docs/Knowledge MCP | **3** |
| Companies WITH Ops MCP but NO Docs MCP | **46** |
| Companies with NO MCP at all | **71** |
| **Total without Docs/Knowledge MCP** | **117** |

---

## 3. Core Principles

Source: [How we built the Microsoft Learn MCP Server](https://devblogs.microsoft.com/engineering-at-microsoft/how-we-built-the-microsoft-learn-mcp-server/) (official product team blog, Feb 2026) and [How we built Ask Learn](https://devblogs.microsoft.com/engineering-at-microsoft/how-we-built-ask-learn-the-rag-based-knowledge-service/) (Apr 2024).

### The "Search-and-Read" Principle

AI agents think like humans with browsers. A human researching a topic does two things:
1. **Search** — find relevant pages
2. **Read** — open and consume the best result

The MCP server compresses all RAG complexity (embeddings, hybrid search, semantic re-ranking, chunk management) behind this simple two-step contract.

### MS Learn's 6 Lessons

| # | Lesson | Detail |
|---|---|---|
| 1 | **"Your API is not an MCP tool"** | Design tools for agent workflow, not to mirror internal APIs. The knowledge service has many params (topK, OData, vector vs hybrid). Tools compress this into `search` and `fetch` matching the human "search-and-read" pattern. |
| 2 | **Remote servers = distributed systems** | Cross-region deployments, dynamic scaling, CORS, session affinity, statelessness, data protection. MCP is "just tools over JSONRPC" but operationally it's a full multi-region service. |
| 3 | **Tool descriptions are your agent UX** | Small wording changes swing tool activation rates materially. They built automated evaluation to iterate descriptions based on observed agent behavior. |
| 4 | **Compose tools for better outcomes** | Search + Fetch work better together. Descriptions explicitly teach this follow-up pattern, improving groundedness and citation quality. |
| 5 | **Defend against hardcoded callers** | When they renamed `question` → `query`, 2-5% of requests broke. They supported both names during deprecation. Used [MCP Interviewer](https://github.com/microsoft/mcp-interviewer). |
| 6 | **Let data drive iteration** | Most requests = coding tasks, explaining, troubleshooting. Prioritized description + retrieval changes against observed intents. |

---

## 4. MS Learn Architecture

### Official Tech Stack (confirmed from product team blog + diagram)

| Component | Technology |
|---|---|
| MCP Framework | Official C# MCP SDK (`ModelContextProtocol` NuGet) |
| Transport | Streamable HTTP Transport (remote, stateless) |
| Hosting | Cloud App Service |
| Search Backend | Cloud AI Search (Document Chunk Index + Code Sample Index) |
| Embeddings | Cloud LLM Embedding Models |
| Content Storage | Cloud Blob Storage (chunked content) |
| Content Source | Microsoft Learn Documentation (100K+ articles) |
| Content Pipeline | Ingestion → Chunking → Embedding → Indexing (continuous updates) |
| Auth | None (public, no API key) |

### 3 Tools Exposed

| Tool | Purpose | Output |
|---|---|---|
| `microsoft_docs_search` | Semantic search over docs | 10 chunks, max ~500 tokens each (title, URL, excerpt) |
| `microsoft_code_sample_search` | Code-specific search with language filter | 20 code snippets with context |
| `microsoft_docs_fetch` | Fetch full page as markdown | Complete page content, cleaned |

### Underlying RAG System ("Ask Learn")

Advanced RAG (not naive):
1. **Content Ingestion**: Docs → chunked → embedded → stored in search index + blob storage
2. **Continuous Updates**: When writers update docs, vector database is incrementally updated
3. **Inference Pipeline**:
   - Pre-retrieval: Query rewriting, expansion, clarification
   - Retrieval: Vector similarity via search index
   - Post-retrieval: Re-ranking, chunk expansion, filtering, compression
4. **Golden Dataset**: Curated Q&A pairs for continuous evaluation
5. **Feedback Loop**: Usage patterns → root cause analysis → pipeline improvements

---

## 5. KnowledgeMCP Architecture

### Cloud-Agnostic Design

All component names use generic terms. Implementation can use any cloud provider.

```
═══════════════════════════════════════════════════════════════════════
                    LAYER 1: INGEST PLANE
                  "Universal Content Ingestion"
═══════════════════════════════════════════════════════════════════════

 CUSTOMER CONTENT SOURCES              CONNECTOR FRAMEWORK
 ═══════════════════════              ══════════════════════

 ┌─────────────────────┐             ┌─────────────────────────────┐
 │ Drag & Drop Portal  │─────┐      │      SOURCE CONNECTORS       │
 │ (Web UI / CLI)      │     │      │                              │
 ├─────────────────────┤     │      │  • SharePoint Connector      │
 │ Cloud Blob Storage  │─────┤      │  • Confluence Connector      │
 │ (any provider)      │     │      │  • S3 / GCS / Blob Connector │
 ├─────────────────────┤     │      │  • Google Drive Connector    │
 │ S3 Buckets          │─────┤      │  • Git Repo Connector        │
 ├─────────────────────┤     ├─────►│  • Web Crawler (Sitemap)     │
 │ SharePoint Sites    │─────┤      │  • Notion / Docs Connector   │
 ├─────────────────────┤     │      │  • Database Connector        │
 │ Confluence / Notion │─────┤      │  • Direct Upload (API)       │
 ├─────────────────────┤     │      │  • Webhook Receiver          │
 │ Google Drive        │─────┤      │                              │
 ├─────────────────────┤     │      └──────────────┬──────────────┘
 │ Git Repos (docs/)   │─────┤                     │
 ├─────────────────────┤     │                     ▼
 │ Public Docs Sites   │─────┘      ┌─────────────────────────────┐
 │ (Sitemap / URL)     │            │   DOCUMENT INTELLIGENCE      │
 ├─────────────────────┤            │   (Pre-processing)           │
 │ Direct API/Webhook  │────────────│                              │
 └─────────────────────┘            │  • Format extraction         │
                                    │    (PDF, DOCX, PPTX, HTML,   │
                                    │     Markdown, XLSX, etc)     │
                                    │  • OCR for scanned docs      │
                                    │  • Code block detection &    │
                                    │    language classification   │
                                    │  • Metadata extraction       │
                                    │    (title, author, date,     │
                                    │     version, product/tag)    │
                                    │  • Language detection         │
                                    │  • Content deduplication     │
                                    └──────────────┬──────────────┘
                                                   │
                                                   ▼
                                    ┌─────────────────────────────┐
                                    │   CHANGE DETECTION SERVICE   │
                                    │                              │
                                    │  • Polls/webhooks on sources │
                                    │  • Content hash comparison   │
                                    │  • Incremental re-processing │
                                    │    (only changed/new docs)   │
                                    │  • Deletion tracking         │
                                    │  • Freshness SLA per tenant  │
                                    └──────────────┬──────────────┘
                                                   │
═══════════════════════════════════════════════════▼═══════════════
                    LAYER 2: INTELLIGENCE PLANE
                  "Chunking, Embedding, Indexing"
═══════════════════════════════════════════════════════════════════

 ┌───────────────────────────────────────────────────────────────┐
 │              CONTENT PROCESSING PIPELINE                       │
 │                                                                │
 │  ┌────────────────┐  ┌─────────────────┐  ┌────────────────┐ │
 │  │ SMART CHUNKER  │  │ EMBEDDING ENGINE│  │ INDEX BUILDER  │ │
 │  │                │  │                 │  │                │ │
 │  │ • Semantic     │  │ • Pluggable     │  │ • Doc Chunk    │ │
 │  │   chunking     │─►│   model support │─►│   Index        │ │
 │  │   (section/    │  │   (OpenAI,      │  │ • Code Sample  │ │
 │  │   paragraph)   │  │   Cohere,       │  │   Index        │ │
 │  │ • Sliding      │  │   Voyage,       │  │ • Metadata     │ │
 │  │   window with  │  │   local/OSS)    │  │   Index        │ │
 │  │   overlap      │  │ • Multi-lingual │  │ • Per-tenant   │ │
 │  │ • Code block   │  │   support       │  │   isolation    │ │
 │  │   preservation │  │ • Batch for     │  │ • Hybrid       │ │
 │  │ • Metadata     │  │   throughput    │  │   (vector +    │ │
 │  │   propagation  │  │                 │  │   keyword +    │ │
 │  │ • 512-1024 tok │  └─────────────────┘  │   semantic     │ │
 │  │ • 10% overlap  │                       │   re-ranking)  │ │
 │  └────────────────┘                       └────────────────┘ │
 │                                                                │
 │  STORAGE LAYER                                                 │
 │  ┌──────────────────────┐  ┌──────────────────────────────┐  │
 │  │ Search Index         │  │ Object/Blob Storage          │  │
 │  │ (per tenant)         │  │ (Raw + processed content)    │  │
 │  │                      │  │                              │  │
 │  │ • Doc chunks         │  │ • Original documents         │  │
 │  │   (vector + text     │  │ • Processed markdown         │  │
 │  │    + metadata)       │  │ • Chunk cache                │  │
 │  │ • Code samples       │  │ • Citation reference store   │  │
 │  │   (vector + lang     │  └──────────────────────────────┘  │
 │  │    + context)        │                                     │
 │  │ • Semantic ranking   │  ┌──────────────────────────────┐  │
 │  │   enabled            │  │ Metadata DB                  │  │
 │  │ • Hybrid search      │  │ (relational or document DB)  │  │
 │  │   (BM25 + vector)    │  │                              │  │
 │  └──────────────────────┘  │ • Tenant config              │  │
 │                             │ • Source manifest             │  │
 │                             │ • Processing state            │  │
 │                             │ • Freshness timestamps        │  │
 │                             │ • Usage analytics             │  │
 │                             └──────────────────────────────┘  │
 └───────────────────────────────────────────────────────────────┘
                                    │
═══════════════════════════════════▼═══════════════════════════════
                    LAYER 3: MCP RUNTIME PLANE
                  "The Agent-Facing Protocol Layer"
═══════════════════════════════════════════════════════════════════

 ┌───────────────────────────────────────────────────────────────┐
 │      MCP SERVER (per tenant; multi-tenant routing)            │
 │      Hosted on: Container Service (any cloud)                 │
 │      Framework: MCP SDK (C# or Python FastMCP)                │
 │                                                                │
 │  ┌──────────────────────────────────────────────────────┐     │
 │  │           PROTOCOL HANDLER                            │     │
 │  │                                                       │     │
 │  │  • JSON-RPC 2.0 over Streamable HTTP                  │     │
 │  │  • Session management (stateless)                     │     │
 │  │  • Tool discovery (tools/list)                        │     │
 │  │  • Tool invocation (tools/call)                       │     │
 │  │  • Multi-tenant routing (URL path or API key)         │     │
 │  │  • Rate limiting & throttling                         │     │
 │  │  • CORS handling                                      │     │
 │  └────────┬──────────────┬──────────────┬───────────────┘     │
 │           │              │              │                      │
 │  ┌────────▼─────┐ ┌─────▼───────┐ ┌───▼───────────┐         │
 │  │ {tenant}_    │ │ {tenant}_   │ │ {tenant}_     │         │
 │  │ docs_search  │ │ code_search │ │ docs_fetch    │         │
 │  │              │ │             │ │               │         │
 │  │ Returns:     │ │ Returns:    │ │ Returns:      │         │
 │  │ • 10 chunks  │ │ • 20 code   │ │ • Full page   │         │
 │  │ • title, url │ │   snippets  │ │   markdown    │         │
 │  │ • excerpt    │ │ • language  │ │ • metadata    │         │
 │  │ • max 500tok │ │ • context   │ │ • citations   │         │
 │  └──────┬───────┘ └──────┬──────┘ └───┬───────────┘         │
 │         │                │             │                      │
 │  ┌──────▼────────────────▼────┐   ┌───▼─────────────────┐   │
 │  │   RETRIEVAL SERVICE        │   │ CONTENT FETCH SVC   │   │
 │  │                            │   │                     │   │
 │  │ • Query rewriting          │   │ • Fetch from source │   │
 │  │ • Hybrid search            │   │   URL or blob cache │   │
 │  │   (BM25 + vector)          │   │ • HTML → Markdown   │   │
 │  │ • Semantic re-ranking      │   │   conversion        │   │
 │  │ • Result merging & dedup   │   │ • Nav/footer strip  │   │
 │  │ • Token-budget truncation  │   │ • Citation inject   │   │
 │  │ • Citation generation      │   │                     │   │
 │  └────────────────────────────┘   └─────────────────────┘   │
 │                                                                │
 │  ┌──────────────────────────────────────────────────────┐     │
 │  │         TOOL DESCRIPTION ENGINE                       │     │
 │  │                                                       │     │
 │  │  • A/B testable descriptions per tenant               │     │
 │  │  • Automated eval: activation rate,                   │     │
 │  │    groundedness, citation quality                     │     │
 │  │  • Deprecation windows for schema changes             │     │
 │  └──────────────────────────────────────────────────────┘     │
 └───────────────────────────────────────────────────────────────┘
                                    │
═══════════════════════════════════▼═══════════════════════════════
                    LAYER 4: OPERATIONS PLANE
                   "Observe, Evaluate, Evolve"
═══════════════════════════════════════════════════════════════════

 ┌───────────────────────────────────────────────────────────────┐
 │                                                                │
 │  ┌─────────────┐  ┌────────────────┐  ┌────────────────────┐ │
 │  │ TENANT       │  │ EVAL ENGINE    │  │ ADMIN PORTAL       │ │
 │  │ MANAGEMENT   │  │                │  │ (Web UI / API)     │ │
 │  │              │  │ • Golden       │  │                    │ │
 │  │ • Onboarding │  │   dataset eval │  │ • Add/remove       │ │
 │  │   wizard     │  │   per tenant   │  │   sources          │ │
 │  │ • Source     │  │ • Relevance,   │  │ • View indexing    │ │
 │  │   config     │  │   groundedness │  │   status           │ │
 │  │ • API key    │  │   citation     │  │ • Test MCP         │ │
 │  │   mgmt       │  │   scoring      │  │   endpoint         │ │
 │  │ • MCP URL    │  │ • Tool desc    │  │ • View usage       │ │
 │  │   generation │  │   optimization │  │ • Configure tools  │ │
 │  │ • RBAC       │  │ • Regression   │  │ • Billing          │ │
 │  │              │  │   detection    │  │                    │ │
 │  └─────────────┘  └────────────────┘  └────────────────────┘ │
 │                                                                │
 │  ┌──────────────────────────────────────────────────────┐     │
 │  │              OBSERVABILITY                            │     │
 │  │                                                       │     │
 │  │  • Request logging (tool calls, latency, errors)      │     │
 │  │  • Agent Analytics (top queries, activation rates)    │     │
 │  │  • Content gap detection (queries with no results)    │     │
 │  │  • Freshness monitoring (source sync status)          │     │
 │  │  • Cost tracking (embeddings, search, compute)        │     │
 │  │  • Alerting (degraded relevance, index lag, errors)   │     │
 │  └──────────────────────────────────────────────────────┘     │
 └───────────────────────────────────────────────────────────────┘
```

### Cloud-Agnostic Component Mapping

| Component | AWS Option | Azure Option | GCP Option | OSS Option |
|---|---|---|---|---|
| **Connectors** | Lambda + Step Functions | Functions + Logic Apps | Cloud Functions + Workflows | Airflow / Temporal |
| **Document Processing** | Textract | AI Document Intelligence | Document AI | Apache Tika / Unstructured.io |
| **Embeddings** | Bedrock (Titan/Cohere) | Azure OpenAI | Vertex AI | Sentence Transformers / Ollama |
| **Search Index** | OpenSearch + kNN | AI Search | Vertex AI Search | Elasticsearch / Typesense / Meilisearch |
| **Object Storage** | S3 | Blob Storage | Cloud Storage | MinIO |
| **Metadata DB** | DynamoDB / RDS | Cosmos DB / PostgreSQL | Firestore / Cloud SQL | PostgreSQL / MongoDB |
| **MCP Server Host** | ECS Fargate / Lambda | Container Apps / App Service | Cloud Run | Docker + any VPS |
| **CDN/Edge** | CloudFront | Front Door | Cloud CDN | Cloudflare |
| **Observability** | CloudWatch + X-Ray | Application Insights | Cloud Monitoring | Grafana + Prometheus |
| **Admin Portal** | Amplify + Lambda | Static Web App + Functions | Firebase Hosting + Functions | Next.js + any backend |

### Customer Flow (End-to-End)

```
STEP 1: Customer signs up at portal
        → Gets tenant ID & API key

STEP 2: Connects sources (any of):
        → Drag-and-drop docs via web UI
        → Point at SharePoint / Confluence URL
        → Provide S3/GCS/Blob bucket credentials
        → Give docs site sitemap URL
        → Connect Git repo docs/ folder

STEP 3: Platform automatically:
        → Crawls/pulls content via connector
        → Extracts text (Document Intelligence)
        → Detects code blocks, classifies language
        → Chunks (semantic, 512-1024 tokens, 10% overlap)
        → Generates embeddings
        → Builds hybrid search index (vector + BM25 + semantic ranking)
        → Stores processed content
        → Generates MCP endpoint URL

STEP 4: Customer gets their MCP endpoint:
        https://mcp.knowledgemcp.io/{tenant-id}

STEP 5: Add to any MCP client:
        {
          "MyCompanyDocs": {
            "url": "https://mcp.knowledgemcp.io/{tenant-id}",
            "type": "http",
            "headers": { "x-api-key": "sk-..." }
          }
        }

STEP 6: AI agents discover 3 tools:
        → {company}_docs_search
        → {company}_code_sample_search
        → {company}_docs_fetch

STEP 7: Continuous sync keeps content fresh.
```

---

## 6. Novel Differentiators & USP

### Ranked by Uniqueness + Impact

| # | Differentiator | Uniqueness | Impact | Score | Details |
|---|---|---|---|---|---|
| 1 | **Retrieval Quality Score** — public groundedness badge | 10 | 9 | **19** | Like SSL cert for MCP. Automated eval, publish score (0-100). Badge for docs sites. No competitor does this. |
| 2 | **Tool Description Optimizer** — A/B testing for MCP | 10 | 8 | **18** | MS Learn Lesson 3. Automate: observe queries, propose better descriptions. Measurable activation rate improvement. |
| 3 | **Agent Analytics Dashboard** | 9 | 9 | **18** | What queries do agents ask? Which docs are most retrieved? Which queries have no answer (content gaps)? Which agents call most? |
| 4 | **One-Click MCP for Public Docs** — paste URL, get MCP | 8 | 10 | **18** | For the 117 companies: paste `docs.stripe.com` → working MCP in 10 min. |
| 5 | **Docs Gap Detector** | 9 | 8 | **17** | Log low-confidence queries. Report: "Agents asked X 47 times but your docs don't cover it." Content strategy product. |
| 6 | **MCP Marketplace** — registry of Knowledge MCPs | 8 | 8 | **16** | Like npm for Knowledge MCP endpoints. Network effect. |
| 7 | **Code Intelligence** — separate code sample index | 7 | 9 | **16** | MS Learn proven pattern. Parse code blocks, classify language, index separately. |
| 8 | **Freshness SLA** — contractual sync guarantee | 7 | 8 | **15** | "Changes reflected within 15 minutes." Backed by webhooks + incremental indexing. |
| 9 | **Bring Your Own Embedding** | 6 | 7 | **13** | Model-agnostic. Enterprise compliance teams care. |
| 10 | **White-Label MCP** — custom branded endpoint | 6 | 7 | **13** | `mcp.stripe.dev` instead of `mcp.knowledgemcp.io/stripe`. Premium tier. |

### The USP

> **"Give your docs a URL. Every AI agent can use them. We measure and optimize the quality."**

Three pillars:
1. **Instant Knowledge MCP** — Paste URL → get MCP endpoint in minutes
2. **Retrieval Quality Score** — Public, measurable groundedness badge
3. **Agent Analytics** — See what agents ask, what they find, what's missing

### One-Liner (pitch deck)

> **"Cloudflare for Knowledge MCP — Give your docs a URL, and every AI agent in the world can use them. We measure and optimize the quality."**

---

## 7. Competitive Landscape

### Nobody is doing what MS Learn does as a service

| | **Ragie** | **Graphlit** | **Context7** | **git-mcp** | **KnowledgeMCP** |
|---|---|---|---|---|---|
| **What they sell** | RAG-as-a-Service (API) | Context layer (API) | Pre-indexed OSS docs | GitHub repo → MCP | **Docs → MCP endpoint** |
| **Customer** | Developers building AI apps | Developers building AI apps | Developers using OSS libs | GitHub users | **Companies with docs** |
| **MCP role** | Bolt-on feature | Bolt-on feature | Product | Product | **Core product** |
| **Custom enterprise docs** | Yes | Yes | No (pre-curated) | No (GitHub only) | **Yes** |
| **3-tool MS Learn pattern** | No | No | 1 tool | 1 tool | **Yes** |
| **Code sample extraction** | No | No | No | No | **Yes** |
| **Quality scoring** | No | No | No | No | **Yes** |
| **Agent analytics** | No | No | No | No | **Yes** |
| **Zero-code setup** | No (REST API coding) | No (GraphQL coding) | Yes (npx) | Yes (URL) | **Yes (URL)** |

### The Core Difference

- **Ragie** = plumbing. Developer buys it, writes code, builds their own product on top.
- **KnowledgeMCP** = faucet. Company points at docs, gets a working endpoint. No code. Every agent can use it.

Ragie's customer builds something *with* Ragie. KnowledgeMCP's customer gets something *from* KnowledgeMCP.

---

## 8. Enterprise Buying Criteria

| # | Factor | Importance (1-10) | Ragie | Graphlit | KnowledgeMCP |
|---|---|---|---|---|---|
| 1 | Zero infrastructure burden | 10 | 8 | 7 | **10** |
| 2 | Data sovereignty / residency | 9 | 7 | 5 | **9** |
| 3 | Security & compliance (SOC2, HIPAA) | 9 | 9 | 6 | 7* |
| 4 | Content freshness / auto-sync | 9 | 8 | 8 | **9** |
| 5 | Multi-source connectors | 8 | 9 | 9 | 8* |
| 6 | Time to value | 8 | 8 | 7 | **10** |
| 7 | Retrieval quality / groundedness | 10 | 8 | 7 | **9** |
| 8 | Agent-native (MCP-first) | 9 | 5 | 6 | **10** |
| 9 | Vendor lock-in avoidance | 7 | 4 | 5 | **10** |
| 10 | Cost predictability | 7 | 6 | 5 | **8** |
| 11 | Tenant isolation | 8 | 7 | 6 | **9** |
| 12 | Citation / provenance | 8 | 7 | 9 | **9** |
| | **TOTAL** | | **86/120** | **80/120** | **108/120** |

*Items marked with * need investment to reach parity.

---

## 9. Investor Criteria

| # | Factor | Assessment |
|---|---|---|
| 1 | **TAM** | 117 identified companies without docs MCP. Real TAM = every company with developer docs globally. |
| 2 | **Defensibility** | Network effects (more customers = better tool descriptions). Data pipeline moat. Switching cost (agents depend on endpoint). Quality data flywheel. |
| 3 | **Revenue model** | Usage-based + subscription: Free → Pro ($99/mo) → Enterprise (custom). Per-query overage. |
| 4 | **Gross margins** | 85-90% est. Content processed once (embed cost), served repeatedly (search is cheap). No LLM inference per query. |
| 5 | **NRR potential** | Strong expansion: customers add sources, docs grow, agent usage grows. Target 130%+ NRR. |
| 6 | **GTM** | Developer-led PLG: Free tier + instant URL. No sales call to start. Enterprise upsell. |
| 7 | **Category creation** | "Knowledge MCP" is a new category. First mover. |
| 8 | **Protocol tailwind** | MCP adopted by VS Code, Claude, Cursor, Windsurf, Cline. 18,337 servers on Glama.ai. Exponential growth. |
| 9 | **Acquisition potential** | Every big tech company without a docs MCP (Google, Oracle, IBM, Salesforce) is a potential acquirer. |

### Key Insight from a16z (source: "Who Owns the Generative AI Platform")

> "There don't appear, today, to be any systemic moats in generative AI... infrastructure vendors touch everything and reap the rewards."

Our positioning as **infrastructure** (not an app) aligns with where a16z says value accrues. The **Quality Score** creates a data flywheel moat that pure infrastructure doesn't have.

---

## 10. Appendix: Full Company Gap List

See Section 2 above for the complete 117-company breakdown.

### Top 10 Highest-Value Targets

1. **Google Cloud** — massive docs, active MCP program, no docs MCP
2. **Salesforce** — massive docs, no MCP at all
3. **Apple** — massive docs, no MCP at all
4. **Meta** — massive docs (React, PyTorch), no MCP at all
5. **SAP** — massive docs, has ops MCP but no docs MCP
6. **Adobe** — very large docs, no MCP at all
7. **ServiceNow** — very large docs, no MCP at all
8. **Oracle** — massive docs, has ops MCP but no docs MCP
9. **IBM** — massive docs, has ops MCP but no docs MCP
10. **NVIDIA** — very large docs, no MCP at all

---

## References

- [How we built the Microsoft Learn MCP Server](https://devblogs.microsoft.com/engineering-at-microsoft/how-we-built-the-microsoft-learn-mcp-server/) — Official MS product team blog (Feb 2026)
- [How we built Ask Learn, the RAG-based knowledge service](https://devblogs.microsoft.com/engineering-at-microsoft/how-we-built-ask-learn-the-rag-based-knowledge-service/) — Underlying RAG system (Apr 2024)
- [RAG in Azure AI Search](https://learn.microsoft.com/en-us/azure/search/retrieval-augmented-generation-overview) — RAG patterns reference
- [Build an MCP server in C#](https://devblogs.microsoft.com/dotnet/build-a-model-context-protocol-mcp-server-in-csharp/) — C# MCP SDK tutorial
- [Who Owns the Generative AI Platform](https://a16z.com/who-owns-the-generative-ai-platform/) — a16z market analysis
- [Emerging Architectures for LLM Applications](https://a16z.com/emerging-architectures-for-llm-applications/) — a16z reference architecture
- [awslabs/mcp](https://github.com/awslabs/mcp) — AWS MCP servers (GitHub, 8.4K stars)
- [awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers) — Community MCP directory (82.4K stars)
- [Glama.ai MCP Directory](https://glama.ai/mcp/servers) — 18,337 MCP servers indexed
- [Ragie.ai](https://ragie.ai) — Closest competitor (RAG-as-a-Service)
- [Graphlit](https://graphlit.com) — Context layer for AI agents
- [Model Context Protocol](https://modelcontextprotocol.io/) — MCP specification
