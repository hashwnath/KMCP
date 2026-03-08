# KnowledgeMCP — AWS Deployment Runbook

> **For another agent/engineer deploying this codebase on a fresh AWS account.**
> All code is written and tested statically. This runbook covers the AWS-side setup.

---

## Prerequisites

| Tool | Min Version | Install |
|---|---|---|
| AWS CLI | v2 | `curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o aws.zip && unzip aws.zip && sudo ./aws/install` |
| AWS SAM CLI | v1.100+ | `pip install aws-sam-cli` |
| Python | 3.11+ | System package or pyenv |
| Node.js | 18+ | `nvm install 18` |
| Docker | 20+ | Required for `sam build --use-container` |

Ensure `aws configure` is done with Admin or PowerUser access for initial deployment.

---

## Step 1: Create OpenSearch Serverless Collection (Manual — not in SAM)

SAM doesn't support OpenSearch Serverless natively. Create it via CLI:

```bash
# Create collection
aws opensearchserverless create-collection \
  --name knowledgemcp \
  --type VECTORSEARCH \
  --description "KnowledgeMCP vector search"

# Create network policy (public access for MVP; restrict in production)
aws opensearchserverless create-security-policy \
  --name knowledgemcp-network \
  --type network \
  --policy '[{"Rules":[{"ResourceType":"collection","Resource":["collection/knowledgemcp"]},{"ResourceType":"dashboard","Resource":["collection/knowledgemcp"]}],"AllowFromPublic":true}]'

# Create encryption policy
aws opensearchserverless create-security-policy \
  --name knowledgemcp-encryption \
  --type encryption \
  --policy '{"Rules":[{"ResourceType":"collection","Resource":["collection/knowledgemcp"]}],"AWSOwnedKey":true}'

# Create data access policy (replace ACCOUNT_ID)
aws opensearchserverless create-access-policy \
  --name knowledgemcp-data \
  --type data \
  --policy '[{"Rules":[{"ResourceType":"index","Resource":["index/knowledgemcp/*"],"Permission":["aoss:*"]},{"ResourceType":"collection","Resource":["collection/knowledgemcp"],"Permission":["aoss:*"]}],"Principal":["arn:aws:iam::ACCOUNT_ID:root"]}]'
```

Wait for collection status = ACTIVE (~2-5 min):
```bash
aws opensearchserverless batch-get-collection --names knowledgemcp \
  --query 'collectionDetails[0].[status,collectionEndpoint]' --output text
```

Save the endpoint URL (e.g., `https://xxx.us-east-1.aoss.amazonaws.com`).

---

## Step 2: Verify SES Email (for Magic Links)

```bash
# Verify sender email
aws ses verify-email-identity --email-address noreply@yourdomain.com

# Check verification status
aws ses get-identity-verification-attributes --identities noreply@yourdomain.com
```

For production, move SES out of sandbox:
```bash
aws sesv2 put-account-details \
  --production-access-enabled \
  --mail-type TRANSACTIONAL \
  --use-case-description "Sending magic-link authentication emails for KnowledgeMCP platform"
```

---

## Step 3: Generate Secrets

```bash
# Generate JWT secret
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
echo "JWT_SECRET_KEY=$JWT_SECRET"

# Generate admin API key
ADMIN_KEY=$(python3 -c "import secrets; print('kmcp_admin_' + secrets.token_urlsafe(32))")
echo "ADMIN_API_KEY=$ADMIN_KEY"
```

---

## Step 4: Deploy the Backend Stack (SAM)

```bash
cd knowledgemcp

# Build (uses Docker to package Lambda layers)
sam build -t infra/template.yaml --use-container

# Deploy (first time — interactive)
sam deploy --guided \
  --parameter-overrides \
    Stage=prod \
    OpenSearchEndpoint=https://YOUR_OPENSEARCH_ENDPOINT \
    EmbeddingProvider=bedrock \
    BedrockModelId=amazon.titan-embed-text-v2:0 \
    JwtSecretKey=$JWT_SECRET \
    FrontendOrigin=https://app.yourdomain.com \
    AppBaseUrl=https://app.yourdomain.com \
    SesFromEmail=noreply@yourdomain.com

# Subsequent deploys (uses saved samconfig.toml)
sam deploy
```

**After deploy, capture outputs:**
```bash
aws cloudformation describe-stacks \
  --stack-name knowledgemcp-stack \
  --query 'Stacks[0].Outputs' --output table
```

You'll see:
- `AdminApiUrl` → e.g., `https://abc123.execute-api.us-east-1.amazonaws.com/prod`
- `McpApiUrl` → e.g., `https://abc123.execute-api.us-east-1.amazonaws.com/prod/mcp`

---

## Step 5: Create OpenSearch Indexes

Run once after first deploy to create the search indexes:

```bash
export PYTHONPATH=.
export OPENSEARCH_ENDPOINT=https://YOUR_OPENSEARCH_ENDPOINT
export AWS_REGION=us-east-1

python3 -c "
from src.indexer.opensearch_client import create_index_if_not_exists
create_index_if_not_exists()
print('Index created')
"
```

---

## Step 6: Deploy the Frontend

```bash
cd knowledgemcp/frontend

# Set the API URL
echo "NEXT_PUBLIC_API_URL=https://YOUR_ADMIN_API_URL" > .env.local

# Install & build
npm install
npm run build

# Option A: S3 + CloudFront (recommended)
aws s3 sync out/ s3://your-frontend-bucket/ --delete
aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*"

# Option B: Vercel (quickest)
npx vercel --prod
```

---

## Step 7: Seed Demo Data (Optional)

```bash
cd knowledgemcp
export PYTHONPATH=.
export ADMIN_API_URL=https://YOUR_ADMIN_API_URL

python3 scripts/seed_demo.py
```

---

## Step 8: Migrate Legacy Source Secrets (If Upgrading)

```bash
cd knowledgemcp
export PYTHONPATH=.
python3 scripts/migrate_legacy_source_secrets.py
```

---

## Step 9: Verify Deployment

```bash
# 1. Health check
curl https://YOUR_MCP_API_URL/health

# 2. Test MCP endpoint (after creating a tenant via signup)
python3 scripts/test_mcp_endpoint.py

# 3. Verify all Lambda functions are invocable
aws lambda invoke --function-name knowledgemcp-admin-prod /dev/null
aws lambda invoke --function-name knowledgemcp-crawler-prod /dev/null
```

---

## Custom Domain Setup (Production)

```bash
# API Gateway custom domain
aws apigatewayv2 create-domain-name \
  --domain-name api.yourdomain.com \
  --domain-name-configurations CertificateArn=arn:aws:acm:...,EndpointType=REGIONAL

# CloudFront for frontend
aws cloudfront create-distribution \
  --origin-domain-name your-frontend-bucket.s3.amazonaws.com \
  --default-root-object index.html \
  --aliases app.yourdomain.com
```

---

## Environment Variables Reference

| Variable | Where Set | Required | Example |
|---|---|---|---|
| `AWS_REGION` | SAM auto | Yes | `us-east-1` |
| `OPENSEARCH_ENDPOINT` | SAM param | Yes | `https://xxx.aoss.amazonaws.com` |
| `EMBEDDING_PROVIDER` | SAM param | Yes | `bedrock` or `openai` |
| `BEDROCK_MODEL_ID` | SAM param | If bedrock | `amazon.titan-embed-text-v2:0` |
| `OPENAI_API_KEY` | SAM param | If openai | `sk-...` |
| `JWT_SECRET_KEY` | SAM param | Yes | 64-char random string |
| `FRONTEND_ORIGIN` | SAM param | Yes | `https://app.yourdomain.com` |
| `APP_BASE_URL` | SAM param | Yes | `https://app.yourdomain.com` |
| `SES_FROM_EMAIL` | SAM param | Yes | `noreply@yourdomain.com` |
| `NEXT_PUBLIC_API_URL` | Frontend .env | Yes | `https://api.yourdomain.com` |

---

## Monitoring Checklist

After deployment, verify these CloudWatch alarms are active:
- `McpErrorAlarm` — Fires when MCP Lambda errors > 5 in 5 min
- `McpLatencyAlarm` — Fires when p99 latency > 3s
- `DlqAlarm` — Fires when dead-letter queue has messages (failed crawl/index jobs)

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `502` on MCP endpoint | Lambda cold start > 30s | Increase Lambda memory to 1024MB+ |
| `401` on admin API | JWT expired or wrong secret | Verify `JWT_SECRET_KEY` matches across deploys |
| OpenSearch timeout | Collection not ACTIVE | Wait or check `batch-get-collection` status |
| SES `MessageRejected` | Sender not verified | Run `ses verify-email-identity` |
| Crawl jobs stuck in DLQ | Missing IAM permission | Check CloudWatch logs for specific error |
| Frontend shows no data | Wrong `NEXT_PUBLIC_API_URL` | Rebuild frontend with correct value |
