"""Starlette middleware for KnowledgeMCP: auth, rate-limiting, logging, errors."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.common.config import get_config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# In-memory token-bucket state: {tenant_id: {"tokens": float, "last": float}}
_buckets: dict[str, dict[str, float]] = defaultdict(
    lambda: {"tokens": float(get_config().rate_limit_burst), "last": time.monotonic()}
)


def _jsonrpc_error(code: int, message: str, http_status: int = 400) -> JSONResponse:
    """Return a JSON-RPC 2.0 compliant error response."""
    return JSONResponse(
        {"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": None},
        status_code=http_status,
    )


def _extract_tenant_slug(path: str) -> str | None:
    """Pull the tenant slug from /mcp/{tenant_slug}[/sse]."""
    parts = path.strip("/").split("/")
    if len(parts) >= 2 and parts[0] == "mcp":
        return parts[1]
    return None


# ---------------------------------------------------------------------------
# API Key Authentication
# ---------------------------------------------------------------------------

class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    """Resolve tenant context and optionally enforce API key auth.

    MCP endpoints are **public by default** (like MS Learn MCP server).
    Any MCP client can plug & play with just the URL — no API key needed.

    If a tenant has ``require_api_key=True`` in their settings, the
    ``x-api-key`` header is required. Otherwise, the tenant is resolved
    from the URL slug alone.

    Skips entirely for health-check and CORS pre-flight requests.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip for non-MCP paths and CORS pre-flight
        if request.url.path == "/health" or request.method == "OPTIONS":
            return await call_next(request)

        tenant_slug = _extract_tenant_slug(request.url.path)
        if not tenant_slug:
            return await call_next(request)

        # Resolve tenant from slug
        from src.common.dynamodb import get_tenant_by_slug

        tenant_record = await get_tenant_by_slug(tenant_slug)
        if not tenant_record:
            return _jsonrpc_error(-32000, "Unknown tenant", http_status=404)

        # If tenant has opted in to API key auth, enforce it
        require_key = tenant_record.get("require_api_key", False)
        if require_key:
            settings = get_config()
            if not settings.skip_auth:
                api_key = request.headers.get("x-api-key")
                if not api_key:
                    return _jsonrpc_error(-32000, "Missing x-api-key header", http_status=401)
                if api_key != tenant_record.get("api_key"):
                    return _jsonrpc_error(-32000, "Invalid API key", http_status=403)

        # Set tenant context for downstream tools, analytics, and OpenSearch
        real_tenant_id = tenant_record["tenant_id"]
        tenant_rate_limit = int(tenant_record.get("rate_limit", 100))

        from src.mcp_server.tenant_context import set_current_tenant
        set_current_tenant(real_tenant_id)
        request.state.tenant_id = real_tenant_id
        request.state.tenant_rate_limit = tenant_rate_limit
        return await call_next(request)


# ---------------------------------------------------------------------------
# Rate Limiting (in-memory token bucket)
# ---------------------------------------------------------------------------

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-tenant token-bucket rate limiter.

    Refills at ``settings.RATE_LIMIT_PER_SECOND`` tokens/sec with a burst
    size of ``settings.RATE_LIMIT_BURST``.  Returns HTTP 429 when the
    bucket is empty.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path == "/health" or request.method == "OPTIONS":
            return await call_next(request)

        tenant_slug = _extract_tenant_slug(request.url.path)
        if not tenant_slug:
            return await call_next(request)

        tenant_key = getattr(request.state, "tenant_id", "") or tenant_slug
        bucket = _buckets[tenant_key]
        now = time.monotonic()
        elapsed = now - bucket["last"]
        bucket["last"] = now

        settings = get_config()
        # Use per-tenant rate_limit if set by auth middleware, else lazy-fetch by slug.
        tenant_rate = getattr(request.state, "tenant_rate_limit", None)
        if tenant_rate is None:
            from src.common.dynamodb import get_tenant_by_slug

            tenant_record = await get_tenant_by_slug(tenant_slug)
            if tenant_record:
                tenant_rate = int(tenant_record.get("rate_limit", 100))
        rate = float(tenant_rate) / 3600.0 if tenant_rate else float(settings.rate_limit_per_second)
        burst = float(settings.rate_limit_burst)
        bucket["tokens"] = min(burst, bucket["tokens"] + elapsed * rate)

        if bucket["tokens"] < 1.0:
            return _jsonrpc_error(
                -32000,
                "Rate limit exceeded. Please retry later.",
                http_status=429,
            )

        bucket["tokens"] -= 1.0
        return await call_next(request)


# ---------------------------------------------------------------------------
# Request Logging
# ---------------------------------------------------------------------------

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with tenant, path, method, status, and latency."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            # Let the error propagate but still log
            latency_ms = (time.perf_counter() - start) * 1000
            _log_request(request, 500, latency_ms)
            raise

        latency_ms = (time.perf_counter() - start) * 1000
        _log_request(request, response.status_code, latency_ms)
        return response


def _log_request(request: Request, status: int, latency_ms: float) -> None:
    """Emit a structured log line (import kept lazy for cold-start)."""
    import logging

    logger = logging.getLogger("knowledgemcp.access")

    tenant = _extract_tenant_slug(request.url.path) or "-"
    logger.info(
        "tenant=%s method=%s path=%s status=%d latency_ms=%.1f",
        tenant,
        request.method,
        request.url.path,
        status,
        latency_ms,
    )
