"""Filesystem implementation of ObjectStorage.

Files are stored under ``LOCAL_DATA_DIR/storage/<key>``. The presigned-URL
contract is fulfilled by exposing a local HTTP upload endpoint
(``/api/upload/direct`` in admin/routes); the URL we hand back is just a
descriptor that admin clients use to call that endpoint.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from src.common.config import get_config


def _storage_root() -> Path:
    base = Path(get_config().local_data_dir).expanduser().resolve() / "storage"
    base.mkdir(parents=True, exist_ok=True)
    return base


class FilesystemStorage:
    def _resolve(self, key: str) -> Path:
        # Defense in depth: refuse path traversal.
        key = key.lstrip("/")
        full = (_storage_root() / key).resolve()
        if not str(full).startswith(str(_storage_root())):
            raise ValueError(f"Refusing to write outside storage root: {key!r}")
        full.parent.mkdir(parents=True, exist_ok=True)
        return full

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        path = self._resolve(key)
        # Atomic write: tmp file in same dir, then rename
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            os.replace(tmp, path)
        except Exception:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass
            raise

    def get(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    def delete(self, key: str) -> None:
        try:
            self._resolve(key).unlink()
        except FileNotFoundError:
            pass

    def presigned_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in_seconds: int = 3600,
    ) -> str:
        # Local mode has no presigning. Return a descriptor URL that the
        # admin client can POST to via /api/upload/direct.
        return (
            f"local://upload?key={key}"
            f"&content_type={content_type}"
            f"&expires_in={expires_in_seconds}"
        )
