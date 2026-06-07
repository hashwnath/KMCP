"""Protocol definitions for the persistence layer (tenants, sources, analytics).

These Protocols define the contract that both the AWS adapters (DynamoDB)
and the local adapters (SQLite) must implement. Consumers depend on these
Protocols and obtain a concrete implementation via the factory.

NOTE: kept intentionally narrow — only the access patterns the running code
needs today. Add a new method here ONLY when adding a new query in callers.
"""

from __future__ import annotations

from typing import Any, Iterable, Iterator, Optional, Protocol


class TenantRepository(Protocol):
    """Tenant persistence operations."""

    def get_by_id(self, tenant_id: str) -> Optional[dict]: ...
    def get_by_slug(self, slug: str) -> Optional[dict]: ...
    def get_by_email(self, email: str) -> Optional[dict]: ...
    def put(self, item: dict) -> None: ...
    def update(
        self,
        tenant_id: str,
        updates: dict,
    ) -> None: ...
    def delete(self, tenant_id: str) -> None: ...


class SourceRepository(Protocol):
    """Source persistence operations."""

    def get_by_id(self, source_id: str) -> Optional[dict]: ...
    def list_by_tenant(self, tenant_id: str) -> list[dict]: ...
    def list_by_schedule(self, schedule: str) -> Iterator[dict]: ...
    def put(self, item: dict) -> None: ...
    def update(
        self,
        source_id: str,
        updates: dict,
    ) -> None: ...
    def delete(self, source_id: str) -> None: ...


class AnalyticsRepository(Protocol):
    """Analytics persistence operations."""

    def log_query(self, item: dict) -> None: ...
    def query_logs(
        self,
        tenant_id: str,
        since_iso: str,
    ) -> list[dict]: ...
