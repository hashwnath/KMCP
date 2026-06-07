"""REST API routes for tenant and source management."""

import json
import uuid
from datetime import timedelta
from datetime import datetime, timezone

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from src.admin.auth import (
    create_access_token,
    decode_access_token,
    generate_api_key,
    hash_password,
    verify_password,
)
from src.common.backends.factory import (
    get_email_sender,
    get_queue,
    get_source_repo,
    get_storage,
    get_tenant_repo,
)
from src.common.config import get_config
from src.common.source_secrets import (
    delete_source_secret as _delete_source_secret,
    migrate_source_item_if_needed as _migrate_source_item_if_needed,
    persist_source_secret as _persist_source_secret,
    redact_source_config as _redact_source_config,
    split_sensitive_config as _split_sensitive_config,
)


_SYNC_SCHEDULES = {"manual", "hourly", "daily", "weekly"}
_MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MB
_ALLOWED_UPLOAD_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".md", ".markdown", ".html", ".htm", ".txt",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_tenant_id(request: Request) -> str | None:
    """Extract and validate tenant_id from the Authorization: Bearer header."""
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return None
    claims = decode_access_token(auth[7:])
    if claims is None:
        return None
    return claims.get("tenant_id")


def _unauthorized() -> JSONResponse:
    return JSONResponse({"error": "Unauthorized"}, status_code=401)


def _bad_request(msg: str) -> JSONResponse:
    return JSONResponse({"error": msg}, status_code=400)


def _not_found(msg: str = "Not found") -> JSONResponse:
    return JSONResponse({"error": msg}, status_code=404)


def _find_tenant_by_email(email: str) -> dict | None:
    """Find first tenant row by email."""
    return get_tenant_repo().get_by_email(email)


def _validate_source_config(source_type: str, source_config: dict) -> str | None:
    """Return validation error message, or None when config is valid."""
    if source_type == "cloud_storage":
        provider = source_config.get("provider", "s3")
        if provider not in {"s3", "azure_blob", "gcs"}:
            return "cloud_storage provider must be one of: s3, azure_blob, gcs"
    if source_type == "wiki_kb":
        platform = source_config.get("platform", "confluence")
        if platform not in {"confluence", "notion", "sharepoint", "gitbook"}:
            return "wiki_kb platform must be one of: confluence, notion, sharepoint, gitbook"
    return None


def _redact_source_item(item: dict) -> dict:
    safe = dict(item)
    safe["config"] = _redact_source_config(item.get("config", {}))
    return safe


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

async def signup(request: Request) -> JSONResponse:
    """POST /api/auth/signup — Create a new tenant account."""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _bad_request("Invalid JSON body")

    config = get_config()
    if config.signup_code:
        invite_code = (body.get("invite_code") or "").strip()
        if invite_code != config.signup_code:
            return JSONResponse(
                {"error": "Invalid or missing invite code"}, status_code=403
            )

    email: str | None = body.get("email")
    password: str | None = body.get("password")
    name: str | None = body.get("name")

    if not email or not password or not name:
        return _bad_request("email, password, and name are required")

    tenants = get_tenant_repo()
    if tenants.get_by_email(email):
        return JSONResponse({"error": "Email already registered"}, status_code=409)

    tenant_id = str(uuid.uuid4())
    api_key = generate_api_key()

    tenants.put({
        "tenant_id": tenant_id,
        "email": email,
        "password_hash": hash_password(password),
        "name": name,
        "api_key": api_key,
        "slug": name.lower().replace(" ", "-"),
        "rate_limit": 100,
        "require_api_key": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    token = create_access_token({"tenant_id": tenant_id, "email": email})
    return JSONResponse(
        {"token": token, "tenant_id": tenant_id, "api_key": api_key},
        status_code=201,
    )


async def login(request: Request) -> JSONResponse:
    """POST /api/auth/login — Authenticate and return a JWT."""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _bad_request("Invalid JSON body")

    email: str | None = body.get("email")
    password: str | None = body.get("password")

    if not email or not password:
        return _bad_request("email and password are required")

    tenant = get_tenant_repo().get_by_email(email)
    if not tenant:
        return _unauthorized()

    if not verify_password(password, tenant["password_hash"]):
        return _unauthorized()

    token = create_access_token({
        "tenant_id": tenant["tenant_id"],
        "email": tenant["email"],
    })
    return JSONResponse({"token": token})


async def request_magic_link(request: Request) -> JSONResponse:
    """POST /api/auth/magic-link/request — Create a short-lived login token."""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _bad_request("Invalid JSON body")

    email: str | None = body.get("email")
    if not email:
        return _bad_request("email is required")

    cfg = get_config()
    # In AWS mode, require SES_FROM_EMAIL. In local mode the LogEmailSender
    # works without any config — it just prints the link to stdout.
    if cfg.backend == "aws" and not cfg.ses_from_email:
        return JSONResponse(
            {"error": "Magic link delivery is not configured"}, status_code=503
        )

    tenant = _find_tenant_by_email(email)
    if not tenant:
        # Avoid account enumeration by returning generic success.
        return JSONResponse({"sent": True})

    token = create_access_token(
        {
            "tenant_id": tenant["tenant_id"],
            "email": tenant["email"],
            "purpose": "magic_link",
        },
        expires_delta=timedelta(minutes=15),
    )
    link = f"{cfg.app_base_url.rstrip('/')}/login?magic_token={token}"
    get_email_sender().send(
        to_address=tenant["email"],
        subject="Your KnowledgeMCP sign-in link",
        body_text=(
            "Use this sign-in link (valid for 15 minutes):\n\n"
            f"{link}\n\n"
            "If you did not request this email, you can ignore it."
        ),
        from_address=cfg.ses_from_email,
    )
    return JSONResponse({"sent": True})


async def verify_magic_link(request: Request) -> JSONResponse:
    """POST /api/auth/magic-link/verify — Exchange magic token for access JWT."""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _bad_request("Invalid JSON body")

    token: str | None = body.get("token")
    if not token:
        return _bad_request("token is required")

    claims = decode_access_token(token)
    if not claims or claims.get("purpose") != "magic_link":
        return _unauthorized()

    access_token = create_access_token(
        {"tenant_id": claims["tenant_id"], "email": claims.get("email", "")},
        expires_delta=timedelta(hours=24),
    )
    return JSONResponse({"token": access_token})


async def get_me(request: Request) -> JSONResponse:
    """GET /api/tenants/me — Return the authenticated tenant's profile."""
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()

    tenant = get_tenant_repo().get_by_id(tenant_id)
    if not tenant:
        return _not_found("Tenant not found")

    tenant = dict(tenant)
    tenant.pop("password_hash", None)
    return JSONResponse(tenant)


# ---------------------------------------------------------------------------
# Source management endpoints
# ---------------------------------------------------------------------------

async def create_source(request: Request) -> JSONResponse:
    """POST /api/sources — Add a new documentation source and enqueue a crawl job."""
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _bad_request("Invalid JSON body")

    source_type: str | None = body.get("source_type")
    name: str | None = body.get("name")
    source_config: dict | None = body.get("config")
    sync_schedule: str = body.get("sync_schedule", "manual")

    if not source_type or not name or not source_config:
        return _bad_request("source_type, name, and config are required")
    if sync_schedule not in _SYNC_SCHEDULES:
        return _bad_request(
            "sync_schedule must be one of: manual, hourly, daily, weekly"
        )

    cfg_error = _validate_source_config(source_type, source_config)
    if cfg_error:
        return _bad_request(cfg_error)

    source_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    public_config, sensitive_config = _split_sensitive_config(source_config)
    if sensitive_config:
        secret_ref = _persist_source_secret(tenant_id, source_id, sensitive_config)
        public_config["secret_ref"] = secret_ref

    item = {
        "source_id": source_id,
        "tenant_id": tenant_id,
        "source_type": source_type,
        "name": name,
        "config": public_config,
        "status": "pending",
        "sync_schedule": sync_schedule,
        "created_at": now,
        "updated_at": now,
    }
    get_source_repo().put(item)

    get_queue().send(
        "crawl",
        {
            "tenant_id": tenant_id,
            "source_id": source_id,
            "source_type": source_type,
            "config": public_config,
            "action": "crawl",
        },
    )

    return JSONResponse(_redact_source_item(item), status_code=201)


async def list_sources(request: Request) -> JSONResponse:
    """GET /api/sources — List all sources for the authenticated tenant."""
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()

    repo = get_source_repo()
    items = []
    for item in repo.list_by_tenant(tenant_id):
        migrated = _migrate_source_item_if_needed(None, item)
        items.append(_redact_source_item(migrated))
    return JSONResponse({"sources": items})


async def get_source(request: Request) -> JSONResponse:
    """GET /api/sources/{source_id} — Get details for a single source."""
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()

    source_id = request.path_params["source_id"]
    item = get_source_repo().get_by_id(source_id)
    if not item or item.get("tenant_id") != tenant_id:
        return _not_found("Source not found")

    item = _migrate_source_item_if_needed(None, item)
    return JSONResponse(_redact_source_item(item))


async def reindex_source(request: Request) -> JSONResponse:
    """POST /api/sources/{source_id}/reindex — Trigger a re-crawl / re-index."""
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()

    source_id = request.path_params["source_id"]
    repo = get_source_repo()
    item = repo.get_by_id(source_id)
    if not item or item.get("tenant_id") != tenant_id:
        return _not_found("Source not found")

    item = _migrate_source_item_if_needed(None, item)

    repo.update(
        source_id,
        {
            "status": "reindexing",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    get_queue().send(
        "crawl",
        {
            "tenant_id": tenant_id,
            "source_id": source_id,
            "source_type": item["source_type"],
            "config": item["config"],
            "action": "reindex",
        },
    )

    return JSONResponse({"status": "reindexing", "source_id": source_id})


async def update_source_schedule(request: Request) -> JSONResponse:
    """PUT /api/sources/{source_id}/schedule — Update automatic sync cadence."""
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()

    source_id = request.path_params["source_id"]
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _bad_request("Invalid JSON body")

    sync_schedule = body.get("sync_schedule")
    if sync_schedule not in _SYNC_SCHEDULES:
        return _bad_request(
            "sync_schedule must be one of: manual, hourly, daily, weekly"
        )

    repo = get_source_repo()
    item = repo.get_by_id(source_id)
    if not item or item.get("tenant_id") != tenant_id:
        return _not_found("Source not found")

    repo.update(
        source_id,
        {
            "sync_schedule": sync_schedule,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return JSONResponse({"updated": True, "sync_schedule": sync_schedule})


async def delete_source(request: Request) -> JSONResponse:
    """DELETE /api/sources/{source_id} — Delete a source and its indexed content."""
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()

    source_id = request.path_params["source_id"]
    repo = get_source_repo()
    item = repo.get_by_id(source_id)
    if not item or item.get("tenant_id") != tenant_id:
        return _not_found("Source not found")

    secret_ref = item.get("config", {}).get("secret_ref")
    if secret_ref:
        _delete_source_secret(secret_ref)

    repo.delete(source_id)

    get_queue().send(
        "crawl",
        {
            "tenant_id": tenant_id,
            "source_id": source_id,
            "action": "delete",
        },
    )

    return JSONResponse({"deleted": True, "source_id": source_id})


# ---------------------------------------------------------------------------
# Analytics endpoints
# ---------------------------------------------------------------------------

async def analytics_overview(request: Request) -> JSONResponse:
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()
    from src.analytics.reporter import get_overview
    return JSONResponse(get_overview(tenant_id))


async def analytics_gaps(request: Request) -> JSONResponse:
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()
    from src.analytics.reporter import get_content_gaps
    days = int(request.query_params.get("days", "7"))
    limit = int(request.query_params.get("limit", "20"))
    return JSONResponse({"gaps": get_content_gaps(tenant_id, days=days, limit=limit)})


async def analytics_top_queries(request: Request) -> JSONResponse:
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()
    from src.analytics.reporter import get_top_queries
    days = int(request.query_params.get("days", "7"))
    limit = int(request.query_params.get("limit", "20"))
    return JSONResponse({"queries": get_top_queries(tenant_id, days=days, limit=limit)})


async def analytics_tool_usage(request: Request) -> JSONResponse:
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()
    from src.analytics.reporter import get_tool_usage_breakdown
    days = int(request.query_params.get("days", "7"))
    return JSONResponse({"usage": get_tool_usage_breakdown(tenant_id, days=days)})


# ---------------------------------------------------------------------------
# Settings endpoints
# ---------------------------------------------------------------------------

async def get_settings(request: Request) -> JSONResponse:
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()
    tenant = get_tenant_repo().get_by_id(tenant_id)
    if not tenant:
        return _not_found("Tenant not found")
    return JSONResponse({
        "slug": tenant.get("slug"),
        "rate_limit": tenant.get("rate_limit", 100),
        "api_key": tenant.get("api_key"),
        "max_docs": tenant.get("max_docs", 500),
        "require_api_key": tenant.get("require_api_key", False),
    })


async def update_settings(request: Request) -> JSONResponse:
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _bad_request("Invalid JSON body")

    updates: dict = {}
    if "slug" in body:
        updates["slug"] = body["slug"]
    if "rate_limit" in body:
        updates["rate_limit"] = int(body["rate_limit"])
    if "max_docs" in body:
        updates["max_docs"] = int(body["max_docs"])
    if "require_api_key" in body:
        updates["require_api_key"] = bool(body["require_api_key"])

    if not updates:
        return _bad_request("No valid fields to update")

    get_tenant_repo().update(tenant_id, updates)
    return JSONResponse({"updated": True})


async def regenerate_key(request: Request) -> JSONResponse:
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()

    new_key = generate_api_key()
    get_tenant_repo().update(tenant_id, {"api_key": new_key})
    return JSONResponse({"api_key": new_key})


# ---------------------------------------------------------------------------
# File upload (presigned URL — AWS) / direct upload (local)
# ---------------------------------------------------------------------------

async def upload_presign(request: Request) -> JSONResponse:
    """POST /api/upload/presign — Generate a presigned PUT URL for file upload."""
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _bad_request("Invalid JSON body")

    filename = body.get("filename", "file")
    content_type = body.get("content_type", "application/octet-stream")
    file_size_bytes = int(body.get("file_size_bytes", 0) or 0)
    batch_count = int(body.get("batch_count", 1) or 1)

    lower = str(filename).lower()
    dot = lower.rfind(".")
    ext = lower[dot:] if dot != -1 else ""
    if ext not in _ALLOWED_UPLOAD_EXTENSIONS:
        return _bad_request(
            "Unsupported file type. Allowed: PDF, DOCX, PPTX, MD, HTML, TXT"
        )
    if file_size_bytes <= 0:
        return _bad_request("file_size_bytes is required")
    if file_size_bytes > _MAX_UPLOAD_BYTES:
        return _bad_request("File exceeds maximum allowed size of 500MB")
    if batch_count > 100:
        return _bad_request("Batch upload supports up to 100 files")

    import uuid as _uuid
    key = f"uploads/{tenant_id}/{_uuid.uuid4()}/{filename}"

    upload_url = get_storage().presigned_upload_url(
        key=key, content_type=content_type, expires_in_seconds=3600
    )
    return JSONResponse({
        "upload_url": upload_url,
        "key": key,
        "bucket": get_config().content_bucket,
    })


async def upload_direct(request: Request) -> JSONResponse:
    """POST /api/upload/direct — Direct multipart upload for local mode.

    Body is multipart/form-data with `file` field. Returns the storage key
    that can be passed back as `config.key` to /api/sources.
    """
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()

    form = await request.form()
    upload = form.get("file")
    if upload is None or not hasattr(upload, "read"):
        return _bad_request("'file' field is required (multipart/form-data)")

    filename = getattr(upload, "filename", "file") or "file"
    lower = filename.lower()
    dot = lower.rfind(".")
    ext = lower[dot:] if dot != -1 else ""
    if ext not in _ALLOWED_UPLOAD_EXTENSIONS:
        return _bad_request(
            "Unsupported file type. Allowed: PDF, DOCX, PPTX, MD, HTML, TXT"
        )

    data = await upload.read()
    if len(data) > _MAX_UPLOAD_BYTES:
        return _bad_request("File exceeds maximum allowed size of 500MB")

    import uuid as _uuid
    key = f"uploads/{tenant_id}/{_uuid.uuid4()}/{filename}"
    content_type = getattr(upload, "content_type", None) or "application/octet-stream"
    get_storage().put(key, data, content_type)

    return JSONResponse({"key": key, "size_bytes": len(data)})


# ---------------------------------------------------------------------------
# Route table
# ---------------------------------------------------------------------------

routes = [
    # Auth
    Route("/api/auth/signup", signup, methods=["POST"]),
    Route("/api/auth/login", login, methods=["POST"]),
    Route("/api/auth/magic-link/request", request_magic_link, methods=["POST"]),
    Route("/api/auth/magic-link/verify", verify_magic_link, methods=["POST"]),
    Route("/api/tenants/me", get_me, methods=["GET"]),
    # Sources
    Route("/api/sources", create_source, methods=["POST"]),
    Route("/api/sources", list_sources, methods=["GET"]),
    Route("/api/sources/{source_id}", get_source, methods=["GET"]),
    Route("/api/sources/{source_id}/reindex", reindex_source, methods=["POST"]),
    Route("/api/sources/{source_id}/schedule", update_source_schedule, methods=["PUT"]),
    Route("/api/sources/{source_id}", delete_source, methods=["DELETE"]),
    # Upload
    Route("/api/upload/presign", upload_presign, methods=["POST"]),
    Route("/api/upload/direct", upload_direct, methods=["POST"]),
    # Analytics
    Route("/api/analytics/overview", analytics_overview, methods=["GET"]),
    Route("/api/analytics/gaps", analytics_gaps, methods=["GET"]),
    Route("/api/analytics/top-queries", analytics_top_queries, methods=["GET"]),
    Route("/api/analytics/tool-usage", analytics_tool_usage, methods=["GET"]),
    # Settings
    Route("/api/settings", get_settings, methods=["GET"]),
    Route("/api/settings", update_settings, methods=["PUT"]),
    Route("/api/settings/regenerate-key", regenerate_key, methods=["POST"]),
]
