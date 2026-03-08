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
from src.common.aws_clients import (
    get_dynamodb_resource,
    get_ses_client,
    get_sqs_client,
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
_ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".docx", ".pptx", ".md", ".markdown", ".html", ".htm", ".txt"}
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
    config = get_config()
    dynamo = get_dynamodb_resource()
    table = dynamo.Table(config.tenants_table)
    scan = table.scan(
        FilterExpression="email = :e",
        ExpressionAttributeValues={":e": email},
        Limit=1,
    )
    items = scan.get("Items", [])
    return items[0] if items else None


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
    """POST /api/auth/signup — Create a new tenant account.

    When SIGNUP_CODE is configured, the request must include a matching
    ``invite_code`` field to proceed (invite-only beta access).
    """
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _bad_request("Invalid JSON body")

    # Invite code gate (controlled beta)
    config = get_config()
    if config.signup_code:
        invite_code = (body.get("invite_code") or "").strip()
        if invite_code != config.signup_code:
            return JSONResponse({"error": "Invalid or missing invite code"}, status_code=403)

    email: str | None = body.get("email")
    password: str | None = body.get("password")
    name: str | None = body.get("name")

    if not email or not password or not name:
        return _bad_request("email, password, and name are required")

    config = get_config()
    dynamo = get_dynamodb_resource()
    table = dynamo.Table(config.tenants_table)

    # Check for existing tenant with same email
    scan = table.scan(
        FilterExpression="email = :e",
        ExpressionAttributeValues={":e": email},
        Limit=1,
    )
    if scan.get("Items"):
        return JSONResponse({"error": "Email already registered"}, status_code=409)

    tenant_id = str(uuid.uuid4())
    api_key = generate_api_key()

    table.put_item(Item={
        "tenant_id": tenant_id,
        "email": email,
        "password_hash": hash_password(password),
        "name": name,
        "api_key": api_key,
        "slug": name.lower().replace(" ", "-"),
        "rate_limit": 100,
        "require_api_key": False,  # MCP endpoint is public by default
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    token = create_access_token({"tenant_id": tenant_id, "email": email})
    return JSONResponse({
        "token": token,
        "tenant_id": tenant_id,
        "api_key": api_key,
    }, status_code=201)


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

    config = get_config()
    dynamo = get_dynamodb_resource()
    table = dynamo.Table(config.tenants_table)

    scan = table.scan(
        FilterExpression="email = :e",
        ExpressionAttributeValues={":e": email},
        Limit=1,
    )
    items = scan.get("Items", [])
    if not items:
        return _unauthorized()

    tenant = items[0]
    if not verify_password(password, tenant["password_hash"]):
        return _unauthorized()

    token = create_access_token({
        "tenant_id": tenant["tenant_id"],
        "email": tenant["email"],
    })
    return JSONResponse({"token": token})


async def request_magic_link(request: Request) -> JSONResponse:
    """POST /api/auth/magic-link/request — Create a short-lived login token.

    Sends the link via SES and never returns raw token material.
    """
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _bad_request("Invalid JSON body")

    email: str | None = body.get("email")
    if not email:
        return _bad_request("email is required")

    cfg = get_config()
    if not cfg.ses_from_email:
        return JSONResponse({"error": "Magic link delivery is not configured"}, status_code=503)

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
    ses = get_ses_client()
    ses.send_email(
        Source=cfg.ses_from_email,
        Destination={"ToAddresses": [tenant["email"]]},
        Message={
            "Subject": {"Data": "Your KnowledgeMCP sign-in link"},
            "Body": {
                "Text": {
                    "Data": (
                        "Use this sign-in link (valid for 15 minutes):\n\n"
                        f"{link}\n\n"
                        "If you did not request this email, you can ignore it."
                    )
                }
            },
        },
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

    config = get_config()
    dynamo = get_dynamodb_resource()
    table = dynamo.Table(config.tenants_table)

    resp = table.get_item(Key={"tenant_id": tenant_id})
    tenant = resp.get("Item")
    if not tenant:
        return _not_found("Tenant not found")

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
        return _bad_request("sync_schedule must be one of: manual, hourly, daily, weekly")

    cfg_error = _validate_source_config(source_type, source_config)
    if cfg_error:
        return _bad_request(cfg_error)

    config = get_config()
    dynamo = get_dynamodb_resource()
    table = dynamo.Table(config.sources_table)

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
    table.put_item(Item=item)

    # Enqueue crawl job
    sqs = get_sqs_client()
    sqs.send_message(
        QueueUrl=config.crawl_queue_url,
        MessageBody=json.dumps({
            "tenant_id": tenant_id,
            "source_id": source_id,
            "source_type": source_type,
            "config": public_config,
            "action": "crawl",
        }),
    )

    return JSONResponse(_redact_source_item(item), status_code=201)


async def list_sources(request: Request) -> JSONResponse:
    """GET /api/sources — List all sources for the authenticated tenant."""
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()

    config = get_config()
    dynamo = get_dynamodb_resource()
    table = dynamo.Table(config.sources_table)

    resp = table.query(
        IndexName="tenant-index",
        KeyConditionExpression="tenant_id = :tid",
        ExpressionAttributeValues={":tid": tenant_id},
    )
    items = []
    for item in resp.get("Items", []):
        migrated = _migrate_source_item_if_needed(table, item)
        items.append(_redact_source_item(migrated))
    return JSONResponse({"sources": items})


async def get_source(request: Request) -> JSONResponse:
    """GET /api/sources/{source_id} — Get details for a single source."""
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()

    source_id = request.path_params["source_id"]
    config = get_config()
    dynamo = get_dynamodb_resource()
    table = dynamo.Table(config.sources_table)

    resp = table.get_item(Key={"source_id": source_id})
    item = resp.get("Item")
    if not item or item.get("tenant_id") != tenant_id:
        return _not_found("Source not found")

    item = _migrate_source_item_if_needed(table, item)
    return JSONResponse(_redact_source_item(item))


async def reindex_source(request: Request) -> JSONResponse:
    """POST /api/sources/{source_id}/reindex — Trigger a re-crawl / re-index."""
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()

    source_id = request.path_params["source_id"]
    config = get_config()
    dynamo = get_dynamodb_resource()
    table = dynamo.Table(config.sources_table)

    resp = table.get_item(Key={"source_id": source_id})
    item = resp.get("Item")
    if not item or item.get("tenant_id") != tenant_id:
        return _not_found("Source not found")

    item = _migrate_source_item_if_needed(table, item)

    table.update_item(
        Key={"source_id": source_id},
        UpdateExpression="SET #s = :s, updated_at = :u",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":s": "reindexing",
            ":u": datetime.now(timezone.utc).isoformat(),
        },
    )

    sqs = get_sqs_client()
    sqs.send_message(
        QueueUrl=config.crawl_queue_url,
        MessageBody=json.dumps({
            "tenant_id": tenant_id,
            "source_id": source_id,
            "source_type": item["source_type"],
            "config": item["config"],
            "action": "reindex",
        }),
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
        return _bad_request("sync_schedule must be one of: manual, hourly, daily, weekly")

    config = get_config()
    table = get_dynamodb_resource().Table(config.sources_table)
    item = table.get_item(Key={"source_id": source_id}).get("Item")
    if not item or item.get("tenant_id") != tenant_id:
        return _not_found("Source not found")

    table.update_item(
        Key={"source_id": source_id},
        UpdateExpression="SET sync_schedule = :sc, updated_at = :u",
        ExpressionAttributeValues={
            ":sc": sync_schedule,
            ":u": datetime.now(timezone.utc).isoformat(),
        },
    )
    return JSONResponse({"updated": True, "sync_schedule": sync_schedule})


async def delete_source(request: Request) -> JSONResponse:
    """DELETE /api/sources/{source_id} — Delete a source and its indexed content."""
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()

    source_id = request.path_params["source_id"]
    config = get_config()
    dynamo = get_dynamodb_resource()
    table = dynamo.Table(config.sources_table)

    resp = table.get_item(Key={"source_id": source_id})
    item = resp.get("Item")
    if not item or item.get("tenant_id") != tenant_id:
        return _not_found("Source not found")

    secret_ref = item.get("config", {}).get("secret_ref")
    if secret_ref:
        _delete_source_secret(secret_ref)

    table.delete_item(Key={"source_id": source_id})

    # Enqueue cleanup job to remove indexed content
    sqs = get_sqs_client()
    sqs.send_message(
        QueueUrl=config.crawl_queue_url,
        MessageBody=json.dumps({
            "tenant_id": tenant_id,
            "source_id": source_id,
            "action": "delete",
        }),
    )

    return JSONResponse({"deleted": True, "source_id": source_id})


# ---------------------------------------------------------------------------
# Analytics endpoints
# ---------------------------------------------------------------------------

async def analytics_overview(request: Request) -> JSONResponse:
    """GET /api/analytics/overview — Usage summary stats."""
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()

    from src.analytics.reporter import get_overview

    return JSONResponse(get_overview(tenant_id))


async def analytics_gaps(request: Request) -> JSONResponse:
    """GET /api/analytics/gaps — Content gap queries."""
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()

    from src.analytics.reporter import get_content_gaps

    days = int(request.query_params.get("days", "7"))
    limit = int(request.query_params.get("limit", "20"))
    return JSONResponse({"gaps": get_content_gaps(tenant_id, days=days, limit=limit)})


async def analytics_top_queries(request: Request) -> JSONResponse:
    """GET /api/analytics/top-queries — Highest volume queries."""
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()

    from src.analytics.reporter import get_top_queries

    days = int(request.query_params.get("days", "7"))
    limit = int(request.query_params.get("limit", "20"))
    return JSONResponse({"queries": get_top_queries(tenant_id, days=days, limit=limit)})


async def analytics_tool_usage(request: Request) -> JSONResponse:
    """GET /api/analytics/tool-usage — Breakdown by tool name."""
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
    """GET /api/settings — Return current tenant settings."""
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()

    config = get_config()
    dynamo = get_dynamodb_resource()
    table = dynamo.Table(config.tenants_table)

    resp = table.get_item(Key={"tenant_id": tenant_id})
    tenant = resp.get("Item")
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
    """PUT /api/settings — Update tenant settings (slug, rate_limit)."""
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()

    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _bad_request("Invalid JSON body")

    config = get_config()
    dynamo = get_dynamodb_resource()
    table = dynamo.Table(config.tenants_table)

    update_parts: list[str] = []
    attr_values: dict = {}
    attr_names: dict = {}

    if "slug" in body:
        update_parts.append("#sl = :sl")
        attr_names["#sl"] = "slug"
        attr_values[":sl"] = body["slug"]

    if "rate_limit" in body:
        update_parts.append("rate_limit = :rl")
        attr_values[":rl"] = int(body["rate_limit"])

    if "max_docs" in body:
        update_parts.append("max_docs = :md")
        attr_values[":md"] = int(body["max_docs"])

    if "require_api_key" in body:
        update_parts.append("require_api_key = :rak")
        attr_values[":rak"] = bool(body["require_api_key"])

    if not update_parts:
        return _bad_request("No valid fields to update")

    table.update_item(
        Key={"tenant_id": tenant_id},
        UpdateExpression="SET " + ", ".join(update_parts),
        ExpressionAttributeValues=attr_values,
        **({"ExpressionAttributeNames": attr_names} if attr_names else {}),
    )
    return JSONResponse({"updated": True})


async def regenerate_key(request: Request) -> JSONResponse:
    """POST /api/settings/regenerate-key — Generate a new API key for the tenant."""
    tenant_id = _get_tenant_id(request)
    if not tenant_id:
        return _unauthorized()

    new_key = generate_api_key()
    config = get_config()
    dynamo = get_dynamodb_resource()
    table = dynamo.Table(config.tenants_table)

    table.update_item(
        Key={"tenant_id": tenant_id},
        UpdateExpression="SET api_key = :k",
        ExpressionAttributeValues={":k": new_key},
    )
    return JSONResponse({"api_key": new_key})


# ---------------------------------------------------------------------------
# File upload (presigned URL)
# ---------------------------------------------------------------------------

async def upload_presign(request: Request) -> JSONResponse:
    """POST /api/upload/presign — Generate a presigned S3 PUT URL for file upload.

    Body: {"filename": "guide.pdf", "content_type": "application/pdf"}
    Returns: {"upload_url": "https://s3...", "key": "uploads/tenant-id/uuid/guide.pdf"}
    """
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
        return _bad_request("Unsupported file type. Allowed: PDF, DOCX, PPTX, MD, HTML, TXT")
    if file_size_bytes <= 0:
        return _bad_request("file_size_bytes is required")
    if file_size_bytes > _MAX_UPLOAD_BYTES:
        return _bad_request("File exceeds maximum allowed size of 500MB")
    if batch_count > 100:
        return _bad_request("Batch upload supports up to 100 files")

    import uuid as _uuid
    key = f"uploads/{tenant_id}/{_uuid.uuid4()}/{filename}"

    config = get_config()
    from src.common.aws_clients import get_s3_client
    s3 = get_s3_client()
    upload_url = s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": config.content_bucket,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=3600,
    )

    return JSONResponse({"upload_url": upload_url, "key": key, "bucket": config.content_bucket})


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
