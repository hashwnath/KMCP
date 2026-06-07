# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **Local mode** (`BACKEND=local`): full stack runs without any AWS account
  via `docker compose up -d`.
  - SQLite for tenant / source / analytics / secrets / jobs metadata
    (WAL mode, automatic schema init)
  - Filesystem for blob storage with atomic writes + path-traversal guard
  - In-process thread worker for crawl + index jobs with at-least-once
    retry semantics
  - fastembed (`BAAI/bge-small-en-v1.5`, 384-d) as the default embedding
    provider — zero LLM cost at query time
  - LogEmailSender for magic-link delivery (stdout + outbox JSON)
  - Auto-generated JWT secret on first run
- **Backend abstraction layer** (`src/common/backends/`): Protocols for
  every persistence + I/O contract; pluggable adapters for AWS and local
- **Index dimension safety**: `ensure_index` persists provider/model/dim in
  the OpenSearch index `_meta` and raises `IndexProviderMismatch` if the
  live config disagrees
- **`POST /api/upload/direct`** endpoint for multipart upload in local mode
- **3 docker-compose services + a worker** instead of the previous single
  container that ran multiple uvicorn processes with `&`
- **CI**: 6 parallel lanes (aws-mock pytest, local pytest, opensearch
  integration, gitleaks, sam-validate, docker-build)
- **LICENSE**: AGPL-3.0 for the backend, MIT for `frontend/`
- **Docs**: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`,
  `docs/AWS_DEPLOYMENT.md`, `.github/ISSUE_TEMPLATE/` + PR template

### Changed
- All AWS handler calls now route through `src/common/backends/factory.py`;
  no direct `boto3` calls in handlers
- README rewritten for an open-source audience
- `.gitignore` hardened for local data dir / model cache / HANDOFF files

### Fixed
- `bcrypt<4.0` pin works around `passlib 1.7.4` reading the removed
  `bcrypt.__about__.__version__` attribute
- OpenSearch HNSW engine switched from `nmslib` to `lucene` for compatibility
  with the OpenSearch 2.x OSS Docker image used in compose / CI

### Security
- Deleted orphan branch `claude/deploy-knowledgemcp-aws-S6pu5` from origin
  (7 historical secret leaks in HANDOFF docs that were never on `main`).
  See `SECURITY.md` for full disclosure.

## [0.1.0] — initial AWS-only release

- FastMCP-based MCP server with docs_search, code_sample_search, docs_fetch
- DynamoDB + S3 + SES + SQS + OpenSearch (managed) + Bedrock-only embeddings
- Lambda-only deployment via SAM
