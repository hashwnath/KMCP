# KnowledgeMCP — AWS Production Deployment

When you outgrow the local docker-compose stack (or just want a hosted
production endpoint), KnowledgeMCP ships with an AWS SAM template that
provisions everything Lambda-side. The application code is unchanged — only
`BACKEND=aws` flips the backend factory.

## Architecture

| Layer | AWS resource |
|---|---|
| API edge | API Gateway HTTP API (`/api/*` → Admin Lambda, `/mcp/*` → MCP Lambda) |
| Compute | 5 Lambda functions: `crawler`, `indexer`, `admin`, `scheduler`, `mcp` |
| Search | Managed OpenSearch (or OpenSearch Serverless) |
| Metadata | DynamoDB tables: `tenants`, `sources`, `analytics` (with GSIs) |
| Blobs | S3 bucket: `knowledgemcp-content-<account>-<stage>` |
| Queues | SQS: `crawl-<stage>`, `index-<stage>` (each with a DLQ) |
| Secrets | AWS Secrets Manager (per-source credentials) |
| Email | SES (magic-link delivery) |
| Embeddings | Amazon Bedrock Titan Embed v2 (default) or OpenAI |
| Monitoring | CloudWatch alarms for MCP errors, p99 latency, DLQ depth |

## Prerequisites

- AWS account with Bedrock access enabled in your region (for Titan embeddings)
- A managed OpenSearch domain or OpenSearch Serverless collection
- A verified SES sender identity (for magic-link auth)
- SAM CLI installed (`brew install aws-sam-cli` or pipx)

## Deploy

```bash
cd infra
sam build
sam deploy --guided \
  --parameter-overrides \
    Stage=prod \
    OpenSearchEndpoint=https://search-XXX.us-east-1.es.amazonaws.com \
    OpenSearchMasterUser=admin \
    OpenSearchMasterPassword='<your-os-password>' \
    EmbeddingProvider=bedrock \
    BedrockModelId=amazon.titan-embed-text-v2:0 \
    JwtSecretKey='<python -c "import secrets;print(secrets.token_urlsafe(64))">' \
    FrontendOrigin=https://app.your-domain.example \
    AppBaseUrl=https://app.your-domain.example \
    SesFromEmail=noreply@your-domain.example \
    SignupCode='<optional invite-only code>'
```

The first deploy prints the `AdminApiUrl` and `McpServerUrl` outputs. Point your frontend at the AdminApiUrl and configure your MCP clients with the McpServerUrl.

## Cost estimate (us-east-1, light usage)

| Resource | Monthly |
|---|---|
| Lambda (under free tier for <1M req/mo) | $0 |
| API Gateway HTTP API ($1.00 / million) | <$1 |
| DynamoDB on-demand (low traffic) | <$2 |
| SQS (free tier covers <1M req) | $0 |
| OpenSearch t3.small.search single node | ~$25 |
| S3 (1 GB) | <$0.10 |
| Bedrock Titan Embed (~$0.0001/1k tokens) | depends on ingest volume |

So roughly **$25–35/mo** at idle, plus per-document ingest costs.

## CloudWatch alarms (included)

- `knowledgemcp-mcp-errors-<stage>` — fires on >5 Lambda errors in 5 min
- `knowledgemcp-mcp-latency-<stage>` — fires on p99 > 3s
- `knowledgemcp-dlq-messages-<stage>` — fires on any message in the index DLQ

## Rollback

```bash
sam delete --stack-name knowledgemcp-prod
```

(DynamoDB tables and S3 bucket are protected — delete them manually if you really want a full teardown.)

## Switching back to local

You don't have to. The two modes are fully independent — you can keep AWS
prod and run `BACKEND=local` for development on the same checkout.
