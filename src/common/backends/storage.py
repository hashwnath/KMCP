"""Object storage Protocol used for file uploads and crawler artifacts."""

from __future__ import annotations

from typing import Optional, Protocol


class ObjectStorage(Protocol):
    """Read/write blob storage."""

    def put(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None: ...
    def get(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...
    def presigned_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in_seconds: int = 3600,
    ) -> str: ...
