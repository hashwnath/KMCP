# Security Policy

## Reporting a Vulnerability

Please report security vulnerabilities by opening a **private security
advisory** under the repository's **Security** tab:
<https://github.com/hashwnath/KMCP/security/advisories/new>.

Please do **not** open a public issue for security problems.

We aim to acknowledge reports within **3 business days** and to publish a
fix (or a clear mitigation) within **30 days** of confirmation.

## Supported versions

Only `main` is actively supported during the pre-1.0 phase. Once we tag a
1.0 release, the two most recent minor versions will receive security fixes.

## Security model — local mode

When running with `BACKEND=local` (the default for `docker compose up`):

- The SQLite database, model cache, JWT secret, uploaded blobs, and the
  email outbox all live under `LOCAL_DATA_DIR` (default `/data` in the
  container, mapped to the `app-data` Docker volume).
- The JWT secret is **auto-generated** on first run to `LOCAL_DATA_DIR/jwt.key`
  with permission `0600`.
- OpenSearch in the bundled compose runs with `DISABLE_SECURITY_PLUGIN=true`
  on a private Docker network. **Do not expose port 9200 to the public
  internet.** If you need that, switch to managed OpenSearch (AWS path).
- The local "magic link" email sender writes to stdout AND
  `LOCAL_DATA_DIR/email_outbox.json` — do not expose that file beyond the
  trusted operator.
- `SKIP_AUTH=true` and `DEV_AUTH_ALLOW=true` are convenience flags for
  development. They are unsafe in production.

## Security model — AWS mode

When running with `BACKEND=aws` (see `docs/AWS_DEPLOYMENT.md`):

- All credentials flow through AWS Secrets Manager.
- API Gateway terminates TLS; HTTP API CORS is locked to `FRONTEND_ORIGIN`.
- OpenSearch fine-grained access control (FGAC) is enabled by default.
- Lambda functions use least-privilege IAM policies defined in
  `infra/template.yaml`.

## Pre-existing leak disclosure (March 2026, pre-OSS scrub)

A pre-OSS audit found 7 secret leaks in commit history on the now-deleted
orphan branch `claude/deploy-knowledgemcp-aws-S6pu5`. Those commits referenced
files (`HANDOFF.md`, `HANDOFF_NEXT.md`) that were never on `main`. The branch
has been deleted from origin and the leaked credentials have been (or are
being) rotated by the project owner. Anyone who cloned the orphan branch
before its deletion should treat the embedded credentials as compromised.
