"""KnowledgeMCP — ASGI entry point.

Mounts the FastMCP ``http_app()`` under the tenant-routed path and wires its
lifespan into the parent Starlette so the StreamableHTTPSessionManager is
initialised correctly. Tenant resolution happens in ``ApiKeyAuthMiddleware``
which writes the resolved tenant_id into a contextvar that the tools read.
"""

from __future__ import annotations

import uvicorn
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from src.common.config import get_config
from src.mcp_server.middleware import (
    ApiKeyAuthMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
)
from src.mcp_server.server import mcp


async def health(request: Request) -> JSONResponse:
    """Lightweight health-check endpoint."""
    return JSONResponse({"status": "ok"})


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> Starlette:
    """Build the Starlette ASGI app with FastMCP mounted per tenant."""
    cfg = get_config()
    origins = [
        o.strip() for o in cfg.frontend_origin.split(",") if o.strip()
    ] or ["http://localhost:3000"]

    # Build the FastMCP HTTP app once at module load. Its lifespan must be
    # passed to the parent Starlette below so the session manager initialises.
    mcp_app = mcp.http_app(path="/")

    routes = [
        Route("/health", health, methods=["GET"]),
        # Mount the FastMCP app under each tenant slug. The slug is captured
        # by the auth middleware (which sets the contextvar) before the
        # mounted app handles the request.
        Mount("/mcp/{tenant_slug:str}", app=mcp_app),
    ]

    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["x-api-key", "content-type", "authorization", "accept"],
            allow_credentials=False,
        ),
        Middleware(RequestLoggingMiddleware),
        Middleware(ApiKeyAuthMiddleware),
        Middleware(RateLimitMiddleware),
    ]

    return Starlette(
        routes=routes,
        middleware=middleware,
        lifespan=mcp_app.lifespan,
    )


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "src.mcp_server.handler:app",
        host=get_config().mcp_server_host,
        port=get_config().mcp_server_port,
        reload=get_config().debug,
        log_level="info",
    )
