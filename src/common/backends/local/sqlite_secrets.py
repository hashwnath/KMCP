"""SQLite-backed implementation of SecretStore.

Persists encrypted-by-OS-only secrets in the same DB as the rest of the
local metadata. NOT suitable for shared/multi-user environments; KnowledgeMCP
local mode is single-tenant, single-host by design.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from src.common.backends.local.sqlite_db import _connect


class SqliteSecretStore:
    def get(self, secret_id: str) -> dict:
        row = _connect().execute(
            "SELECT value_json FROM secrets WHERE secret_id = ?", (secret_id,)
        ).fetchone()
        if not row:
            return {}
        try:
            value = json.loads(row["value_json"])
        except Exception:
            return {}
        return value if isinstance(value, dict) else {}

    def put(self, secret_id: str, value: dict) -> str:
        _connect().execute(
            "INSERT OR REPLACE INTO secrets (secret_id, value_json, updated_at) "
            "VALUES (?, ?, ?)",
            (
                secret_id,
                json.dumps(value),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        return secret_id

    def delete(self, secret_id: str) -> None:
        _connect().execute("DELETE FROM secrets WHERE secret_id = ?", (secret_id,))
