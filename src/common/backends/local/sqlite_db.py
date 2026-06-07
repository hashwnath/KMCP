"""SQLite implementation of TenantRepository, SourceRepository, AnalyticsRepository.

One database file under ``LOCAL_DATA_DIR/knowledgemcp.db``. WAL mode for safe
multi-process reads (worker + admin + mcp + frontend's API hits).
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Iterator, Optional

from src.common.config import get_config


_DB_LOCK = threading.Lock()
_DB_INITIALIZED: dict[str, bool] = {}


def _db_path() -> Path:
    base = Path(get_config().local_data_dir).expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    return base / "knowledgemcp.db"


def _connect() -> sqlite3.Connection:
    path = _db_path()
    conn = sqlite3.connect(
        str(path),
        isolation_level=None,        # autocommit; each statement is its own txn
        detect_types=sqlite3.PARSE_DECLTYPES,
        timeout=30.0,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    if not _DB_INITIALIZED.get(str(path)):
        with _DB_LOCK:
            if not _DB_INITIALIZED.get(str(path)):
                _init_schema(conn)
                _DB_INITIALIZED[str(path)] = True
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS tenants (
            tenant_id TEXT PRIMARY KEY,
            slug TEXT,
            name TEXT,
            email TEXT,
            password_hash TEXT,
            api_key TEXT,
            rate_limit INTEGER DEFAULT 100,
            max_docs INTEGER DEFAULT 500,
            require_api_key INTEGER DEFAULT 0,
            extra_json TEXT,
            created_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_tenants_slug ON tenants(slug);
        CREATE INDEX IF NOT EXISTS idx_tenants_email ON tenants(email);
        CREATE INDEX IF NOT EXISTS idx_tenants_api_key ON tenants(api_key);

        CREATE TABLE IF NOT EXISTS sources (
            source_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            source_type TEXT,
            name TEXT,
            config_json TEXT,
            status TEXT,
            sync_schedule TEXT DEFAULT 'manual',
            doc_count INTEGER DEFAULT 0,
            pages_found INTEGER,
            pages_indexed INTEGER,
            error_message TEXT,
            last_scheduled_at TEXT,
            extra_json TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_sources_tenant ON sources(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_sources_schedule ON sources(sync_schedule);

        CREATE TABLE IF NOT EXISTS analytics (
            tenant_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            tool_name TEXT,
            query TEXT,
            results_count INTEGER,
            latency_ms INTEGER,
            PRIMARY KEY (tenant_id, timestamp)
        );
        CREATE INDEX IF NOT EXISTS idx_analytics_tenant_ts ON analytics(tenant_id, timestamp);

        CREATE TABLE IF NOT EXISTS secrets (
            secret_id TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS jobs (
            job_id INTEGER PRIMARY KEY AUTOINCREMENT,
            queue_name TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',  -- pending|in_flight|done|failed
            attempts INTEGER NOT NULL DEFAULT 0,
            error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_jobs_status_queue ON jobs(status, queue_name);

        CREATE TABLE IF NOT EXISTS index_meta (
            tenant_id TEXT PRIMARY KEY,
            embedding_provider TEXT NOT NULL,
            embedding_model TEXT NOT NULL,
            embedding_dim INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Columns that live as their own physical column in the tenants table. Any
# other key in the input dict is rolled into the JSON blob ``extra_json``.
_TENANT_COLS = {
    "tenant_id", "slug", "name", "email", "password_hash", "api_key",
    "rate_limit", "max_docs", "require_api_key", "created_at",
}
_SOURCE_COLS = {
    "source_id", "tenant_id", "source_type", "name", "config", "config_json",
    "status", "sync_schedule", "doc_count", "pages_found", "pages_indexed",
    "error_message", "last_scheduled_at", "created_at", "updated_at",
}


def _row_to_tenant(row: sqlite3.Row | None) -> Optional[dict]:
    if row is None:
        return None
    d = dict(row)
    extra = d.pop("extra_json", None)
    if extra:
        try:
            d.update(json.loads(extra))
        except Exception:
            pass
    d["require_api_key"] = bool(d.get("require_api_key"))
    return d


def _row_to_source(row: sqlite3.Row | None) -> Optional[dict]:
    if row is None:
        return None
    d = dict(row)
    cfg = d.pop("config_json", None)
    if cfg:
        try:
            d["config"] = json.loads(cfg)
        except Exception:
            d["config"] = {}
    else:
        d["config"] = {}
    extra = d.pop("extra_json", None)
    if extra:
        try:
            d.update(json.loads(extra))
        except Exception:
            pass
    return d


def _split_tenant(item: dict) -> tuple[dict, dict]:
    """Split a tenant input dict into (column_values, extra_json_payload)."""
    cols: dict = {}
    extra: dict = {}
    for k, v in item.items():
        if k in _TENANT_COLS:
            if k == "require_api_key":
                cols[k] = 1 if v else 0
            else:
                cols[k] = v
        else:
            extra[k] = v
    return cols, extra


def _split_source(item: dict) -> tuple[dict, dict]:
    cols: dict = {}
    extra: dict = {}
    for k, v in item.items():
        if k == "config":
            cols["config_json"] = json.dumps(v) if v is not None else None
        elif k in _SOURCE_COLS:
            cols[k] = v
        else:
            extra[k] = v
    return cols, extra


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------

class SqliteTenantRepository:
    def _conn(self) -> sqlite3.Connection:
        return _connect()

    def get_by_id(self, tenant_id: str) -> Optional[dict]:
        row = self._conn().execute(
            "SELECT * FROM tenants WHERE tenant_id = ?", (tenant_id,)
        ).fetchone()
        return _row_to_tenant(row)

    def get_by_slug(self, slug: str) -> Optional[dict]:
        row = self._conn().execute(
            "SELECT * FROM tenants WHERE slug = ?", (slug,)
        ).fetchone()
        return _row_to_tenant(row)

    def get_by_email(self, email: str) -> Optional[dict]:
        row = self._conn().execute(
            "SELECT * FROM tenants WHERE email = ?", (email,)
        ).fetchone()
        return _row_to_tenant(row)

    def put(self, item: dict) -> None:
        cols, extra = _split_tenant(item)
        # tenant_id is required
        if "tenant_id" not in cols:
            raise ValueError("tenant_id is required")
        cols.setdefault("rate_limit", 100)
        cols.setdefault("max_docs", 500)
        cols.setdefault("require_api_key", 0)
        cols["extra_json"] = json.dumps(extra) if extra else None
        col_names = list(cols.keys())
        placeholders = ", ".join(["?"] * len(col_names))
        self._conn().execute(
            f"INSERT OR REPLACE INTO tenants ({', '.join(col_names)}) "
            f"VALUES ({placeholders})",
            list(cols.values()),
        )

    def update(self, tenant_id: str, updates: dict) -> None:
        if not updates:
            return
        cols, extra = _split_tenant(updates)
        conn = self._conn()
        if cols:
            set_clause = ", ".join(f"{k} = ?" for k in cols.keys())
            conn.execute(
                f"UPDATE tenants SET {set_clause} WHERE tenant_id = ?",
                [*cols.values(), tenant_id],
            )
        if extra:
            existing_row = conn.execute(
                "SELECT extra_json FROM tenants WHERE tenant_id = ?", (tenant_id,)
            ).fetchone()
            current = {}
            if existing_row and existing_row["extra_json"]:
                try:
                    current = json.loads(existing_row["extra_json"])
                except Exception:
                    current = {}
            current.update(extra)
            conn.execute(
                "UPDATE tenants SET extra_json = ? WHERE tenant_id = ?",
                (json.dumps(current), tenant_id),
            )

    def delete(self, tenant_id: str) -> None:
        self._conn().execute(
            "DELETE FROM tenants WHERE tenant_id = ?", (tenant_id,)
        )


class SqliteSourceRepository:
    def _conn(self) -> sqlite3.Connection:
        return _connect()

    def get_by_id(self, source_id: str) -> Optional[dict]:
        row = self._conn().execute(
            "SELECT * FROM sources WHERE source_id = ?", (source_id,)
        ).fetchone()
        return _row_to_source(row)

    def list_by_tenant(self, tenant_id: str) -> list[dict]:
        rows = self._conn().execute(
            "SELECT * FROM sources WHERE tenant_id = ?", (tenant_id,)
        ).fetchall()
        return [d for d in (_row_to_source(r) for r in rows) if d is not None]

    def list_by_schedule(self, schedule: str) -> Iterator[dict]:
        for row in self._conn().execute(
            "SELECT * FROM sources WHERE sync_schedule = ?", (schedule,)
        ):
            item = _row_to_source(row)
            if item is not None:
                yield item

    def put(self, item: dict) -> None:
        cols, extra = _split_source(item)
        if "source_id" not in cols:
            raise ValueError("source_id is required")
        cols["extra_json"] = json.dumps(extra) if extra else None
        col_names = list(cols.keys())
        placeholders = ", ".join(["?"] * len(col_names))
        self._conn().execute(
            f"INSERT OR REPLACE INTO sources ({', '.join(col_names)}) "
            f"VALUES ({placeholders})",
            list(cols.values()),
        )

    def update(self, source_id: str, updates: dict) -> None:
        if not updates:
            return
        cols, extra = _split_source(updates)
        conn = self._conn()
        if cols:
            set_clause = ", ".join(f"{k} = ?" for k in cols.keys())
            conn.execute(
                f"UPDATE sources SET {set_clause} WHERE source_id = ?",
                [*cols.values(), source_id],
            )
        if extra:
            existing_row = conn.execute(
                "SELECT extra_json FROM sources WHERE source_id = ?", (source_id,)
            ).fetchone()
            current = {}
            if existing_row and existing_row["extra_json"]:
                try:
                    current = json.loads(existing_row["extra_json"])
                except Exception:
                    current = {}
            current.update(extra)
            conn.execute(
                "UPDATE sources SET extra_json = ? WHERE source_id = ?",
                (json.dumps(current), source_id),
            )

    def delete(self, source_id: str) -> None:
        self._conn().execute(
            "DELETE FROM sources WHERE source_id = ?", (source_id,)
        )


class SqliteAnalyticsRepository:
    def _conn(self) -> sqlite3.Connection:
        return _connect()

    def log_query(self, item: dict) -> None:
        self._conn().execute(
            "INSERT OR REPLACE INTO analytics "
            "(tenant_id, timestamp, tool_name, query, results_count, latency_ms) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                item.get("tenant_id", ""),
                item.get("timestamp", ""),
                item.get("tool_name", ""),
                item.get("query", ""),
                int(item.get("results_count", 0) or 0),
                int(item.get("latency_ms", 0) or 0),
            ),
        )

    def query_logs(self, tenant_id: str, since_iso: str) -> list[dict]:
        rows = self._conn().execute(
            "SELECT tenant_id, timestamp, tool_name, query, results_count, latency_ms "
            "FROM analytics WHERE tenant_id = ? AND timestamp >= ? "
            "ORDER BY timestamp DESC",
            (tenant_id, since_iso),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Index metadata helpers (used by the indexer for dim-mismatch safety)
# ---------------------------------------------------------------------------

def get_index_meta(tenant_id: str) -> Optional[dict]:
    row = _connect().execute(
        "SELECT * FROM index_meta WHERE tenant_id = ?", (tenant_id,)
    ).fetchone()
    return dict(row) if row else None


def put_index_meta(tenant_id: str, provider: str, model: str, dim: int) -> None:
    from datetime import datetime, timezone
    _connect().execute(
        "INSERT OR REPLACE INTO index_meta "
        "(tenant_id, embedding_provider, embedding_model, embedding_dim, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            tenant_id,
            provider,
            model,
            int(dim),
            datetime.now(timezone.utc).isoformat(),
        ),
    )


def delete_index_meta(tenant_id: str) -> None:
    _connect().execute("DELETE FROM index_meta WHERE tenant_id = ?", (tenant_id,))
