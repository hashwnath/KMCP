"""Request-scoped tenant context using Python contextvars.

The auth middleware sets the tenant_id after validating the API key.
MCP tools read it instead of accepting tenant_id as a user parameter.
This prevents tenant isolation breaches where an agent could pass
another tenant's ID.
"""

from __future__ import annotations

from contextvars import ContextVar

_tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default="")


def set_current_tenant(tenant_id: str) -> None:
    """Set the tenant for the current request (called by auth middleware)."""
    _tenant_id_var.set(tenant_id)


def get_current_tenant() -> str:
    """Get the tenant for the current request (called by tools)."""
    tid = _tenant_id_var.get()
    if not tid:
        raise RuntimeError("Tenant context not set — request not authenticated")
    return tid
