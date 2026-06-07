"""Small persistence helpers used by the runtime edge.

Thin wrappers around the TenantRepository so existing callers in middleware
keep their async signature. The actual storage backend is selected via the
BACKEND env (see src.common.backends.factory).
"""

from __future__ import annotations

import asyncio

from src.common.backends.factory import get_tenant_repo


async def get_tenant_by_slug(slug: str) -> dict | None:
    """Look up a full tenant record by slug.

    Returns the full tenant dict (tenant_id, slug, api_key, rate_limit, ...) or
    None if not found.
    """
    return await asyncio.to_thread(get_tenant_repo().get_by_slug, slug)


async def get_tenant_api_key(slug: str) -> str | None:
    """Look up a tenant API key by slug (convenience wrapper)."""
    tenant = await get_tenant_by_slug(slug)
    return tenant.get("api_key") if tenant else None
