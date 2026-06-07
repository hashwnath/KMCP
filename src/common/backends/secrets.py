"""Secret storage Protocol for source-config credentials."""

from __future__ import annotations

from typing import Optional, Protocol


class SecretStore(Protocol):
    """CRUD for opaque secret blobs."""

    def get(self, secret_id: str) -> dict: ...
    def put(self, secret_id: str, value: dict) -> str:
        """Create or update; returns the canonical secret reference (ARN or id)."""
        ...
    def delete(self, secret_id: str) -> None: ...
