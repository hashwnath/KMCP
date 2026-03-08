"""KnowledgeMCP — ASGI entry point.

Creates a Starlette app that routes MCP requests by tenant slug,
applies auth / CORS / rate-limit middleware, and delegates to FastMCP.
"""

from __future__ import annotations

import uvicorn
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from src.common.config import get_config
from src.mcp_server.middleware import (
    ApiKeyAuthMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
)
from src.mcp_server.server import mcp


async def mcp_endpoint(request: Request) -> Response:
    """Route POST /mcp/{tenant_slug} to the FastMCP handler.

    The tenant_slug is extracted from the URL path and injected into the
    request state so that individual tools can read it.
    """
    tenant_slug: str = request.path_params["tenant_slug"]

    # Stash tenant context so middleware / tools can access it.
    request.state.tenant_id = tenant_slug

    # Delegate to the FastMCP ASGI handler.
    # FastMCP exposes an .handle() coroutine that accepts a raw ASGI scope.
    asgi_app = mcp.get_asgi_app()
    body = await request.body()
    messages: list[dict] = []
    body_sent = False

    async def receive() -> dict:
        nonlocal body_sent
        if body_sent:
            return {"type": "http.disconnect"}
        body_sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict) -> None:
        messages.append(message)

    scope = dict(request.scope)
    scope["path"] = "/mcp"
    scope["raw_path"] = b"/mcp"
    await asgi_app(scope, receive, send)

    status = 200
    headers: list[tuple[bytes, bytes]] = []
    chunks: list[bytes] = []
    for message in messages:
        if message["type"] == "http.response.start":
            status = message["status"]
            headers = message.get("headers", [])
        elif message["type"] == "http.response.body":
            chunks.append(message.get("body", b""))

    return Response(
        content=b"".join(chunks),
        status_code=status,
        headers={key.decode("utf-8"): value.decode("utf-8") for key, value in headers},
    )


async def health(request: Request) -> JSONResponse:
    """Lightweight health-check endpoint."""
    return JSONResponse({"status": "ok"})


# -- Application factory -----------------------------------------------------

def create_app() -> Starlette:
    """Build the Starlette ASGI application with all middleware."""

    cfg = get_config()
    origins = [o.strip() for o in cfg.frontend_origin.split(",") if o.strip()] or ["http://localhost:3000"]

    routes = [
        Route("/health", health, methods=["GET"]),
        Route("/mcp/{tenant_slug:str}", mcp_endpoint, methods=["POST"]),
        # SSE variant for streaming transport
        Route("/mcp/{tenant_slug:str}/sse", mcp_endpoint, methods=["GET", "POST"]),
    ]

    middleware = [
        # CORS — MCP clients are cross-origin; allow broad access.
        Middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["x-api-key", "content-type", "authorization"],
            allow_credentials=False,
        ),
        # Custom middleware (applied inside-out: logging -> auth -> rate-limit).
        Middleware(RequestLoggingMiddleware),
        Middleware(ApiKeyAuthMiddleware),
        Middleware(RateLimitMiddleware),
    ]

    return Starlette(routes=routes, middleware=middleware)


app = create_app()

# ---------------------------------------------------------------------------
# Local development
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(
        "src.mcp_server.handler:app",
        host=get_config().mcp_server_host,
        port=get_config().mcp_server_port,
        reload=get_config().debug,
        log_level="info",
    )
