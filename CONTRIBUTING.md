# Contributing to KnowledgeMCP

Thanks for your interest! We welcome PRs, issues, and discussions.

## Quick start (5 minutes)

```bash
git clone https://github.com/hashwnath/KMCP.git
cd KMCP
make up        # docker compose up -d --build
# Admin    http://localhost:8081
# MCP      http://localhost:8000
# UI       http://localhost:3000
```

To run without Docker:

```bash
pip install -e ".[dev,local]"
pip install "bcrypt<4.0"            # see deps note below

# One terminal per service:
BACKEND=local EMBEDDING_PROVIDER=local uvicorn src.admin.handler:app --port 8081
BACKEND=local EMBEDDING_PROVIDER=local uvicorn src.mcp_server.handler:app --port 8000
BACKEND=local EMBEDDING_PROVIDER=local python -m src.common.backends.local.worker
```

## How the codebase is organised

```
src/
  common/
    backends/
      database.py     Tenant/Source/AnalyticsRepository protocols
      queue.py        JobQueue protocol
      storage.py      ObjectStorage protocol
      secrets.py      SecretStore protocol
      email.py        EmailSender protocol
      factory.py      get_X() — picks impl from BACKEND env (local|aws)
      aws/            AWS adapters (DynamoDB, SQS, S3, Secrets Manager, SES)
      local/          SQLite + filesystem + thread-worker + log email
  admin/              Starlette REST API for the dashboard
  mcp_server/         FastMCP server (the customer-facing endpoint)
  crawler/            Source-type connectors (web, S3, wiki, git, file, text)
  indexer/            Chunking, embedding, OpenSearch
  analytics/          Query logging + reporting
  scheduler/          Hourly/daily/weekly sync dispatcher

tests/                pytest suite (10 modules, ~70 tests)
frontend/             Next.js 14 dashboard (MIT-licensed, see frontend/LICENSE)
infra/                AWS SAM template (production deployment)
.github/workflows/    CI: pytest aws-mock + pytest local + opensearch + gitleaks + sam-validate + docker-build
```

## Adding a new source type

1. Add an enum entry to `src/common/models.SourceType`.
2. Implement a connector function in `src/crawler/` returning `list[Document]`.
3. Add a branch to `src/crawler/handler._dispatch_crawl`.
4. Add tests in `tests/test_crawler.py`.

## Switching the local backend (e.g. to Postgres)

Implement the Protocols in `src/common/backends/<your-impl>/` and add a branch
in `src/common/backends/factory.get_X()`. Existing handlers won't need changes.

## Coding conventions

- Python 3.11+, type annotations required
- Async only where the call genuinely awaits I/O
- All AWS calls go through the factory; no direct `boto3` in handlers
- Tests should run against `BACKEND=local` with a `tmp_path` fixture for isolation

## Pull request checklist

- [ ] `make test` passes locally
- [ ] CI is green on the PR (lanes: aws-mock, local, opensearch, gitleaks, sam-validate, docker-build)
- [ ] New behaviour has tests
- [ ] If you touched the admin or MCP API, update `README.md`
- [ ] If you touched the AWS path, leave `infra/template.yaml` and `docs/AWS_DEPLOYMENT.md` consistent

## Dependency note: `bcrypt<4.0`

`passlib 1.7.4` reads `bcrypt.__about__.__version__` which `bcrypt >= 4.0`
removed. Until we migrate off passlib, please keep the `bcrypt<4.0` pin.

## Reporting bugs / asking questions

- **Bugs**: open an issue with the *Bug report* template; include `docker compose logs --tail=100` output.
- **Features**: open an issue with the *Feature request* template.
- **Questions**: open an issue with the *Question* template.

## Security

If you believe you've found a security vulnerability, **do not open a public issue**. See `SECURITY.md`.

## License

By contributing you agree that your contributions are licensed under AGPL-3.0
for the backend and MIT for `frontend/`. By submitting a PR you assert that
you have the right to license your contribution under those terms.
