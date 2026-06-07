"""Tests for the local (SQLite + filesystem) backend implementations."""

from __future__ import annotations

import os
import tempfile
import threading
import time
from pathlib import Path

import pytest


@pytest.fixture
def local_env(monkeypatch, tmp_path):
    """Switch to BACKEND=local with an isolated tmp data dir per test."""
    monkeypatch.setenv("BACKEND", "local")
    monkeypatch.setenv("LOCAL_DATA_DIR", str(tmp_path))
    from src.common.config import get_config
    get_config.cache_clear()
    import src.common.config as _cfg_mod
    _cfg_mod.settings = get_config()
    from src.common.backends.factory import reset_backend_factories
    reset_backend_factories()
    # Also reset the per-DB initialised flag so the schema is recreated
    from src.common.backends.local import sqlite_db as _sdb
    _sdb._DB_INITIALIZED.clear()
    yield tmp_path
    reset_backend_factories()
    _sdb._DB_INITIALIZED.clear()


class TestSqliteTenantRepository:
    def test_put_get_by_id(self, local_env):
        from src.common.backends.factory import get_tenant_repo
        repo = get_tenant_repo()
        repo.put({
            "tenant_id": "t1", "slug": "alpha", "name": "Alpha",
            "email": "a@a.com", "password_hash": "h", "api_key": "k",
            "created_at": "2026-01-01T00:00:00",
        })
        got = repo.get_by_id("t1")
        assert got["slug"] == "alpha"
        assert got["api_key"] == "k"
        assert got["rate_limit"] == 100  # default
        assert got["require_api_key"] is False

    def test_get_by_slug(self, local_env):
        from src.common.backends.factory import get_tenant_repo
        repo = get_tenant_repo()
        repo.put({"tenant_id": "t2", "slug": "beta", "email": "b@b.com"})
        assert repo.get_by_slug("beta")["tenant_id"] == "t2"
        assert repo.get_by_slug("missing") is None

    def test_get_by_email(self, local_env):
        from src.common.backends.factory import get_tenant_repo
        repo = get_tenant_repo()
        repo.put({"tenant_id": "t3", "slug": "g", "email": "c@c.com"})
        assert repo.get_by_email("c@c.com")["tenant_id"] == "t3"
        assert repo.get_by_email("nope@x.com") is None

    def test_update_and_delete(self, local_env):
        from src.common.backends.factory import get_tenant_repo
        repo = get_tenant_repo()
        repo.put({"tenant_id": "t4", "slug": "d", "email": "d@d.com"})
        repo.update("t4", {"slug": "new-d", "rate_limit": 500, "custom_field": "x"})
        got = repo.get_by_id("t4")
        assert got["slug"] == "new-d"
        assert got["rate_limit"] == 500
        assert got["custom_field"] == "x"  # extra fields persisted via extra_json
        repo.delete("t4")
        assert repo.get_by_id("t4") is None


class TestSqliteSourceRepository:
    def test_put_list_by_tenant(self, local_env):
        from src.common.backends.factory import get_source_repo
        repo = get_source_repo()
        for sid in ("s1", "s2", "s3"):
            repo.put({
                "source_id": sid,
                "tenant_id": "tenant-A" if sid != "s3" else "tenant-B",
                "source_type": "website_url",
                "name": sid,
                "config": {"url": f"https://{sid}.example"},
                "status": "pending",
                "sync_schedule": "manual",
            })
        sources = repo.list_by_tenant("tenant-A")
        assert {s["source_id"] for s in sources} == {"s1", "s2"}
        for s in sources:
            assert s["config"]["url"].startswith("https://")

    def test_list_by_schedule(self, local_env):
        from src.common.backends.factory import get_source_repo
        repo = get_source_repo()
        repo.put({"source_id": "h1", "tenant_id": "t", "source_type": "website_url", "name": "h1",
                  "config": {}, "status": "ready", "sync_schedule": "hourly"})
        repo.put({"source_id": "d1", "tenant_id": "t", "source_type": "website_url", "name": "d1",
                  "config": {}, "status": "ready", "sync_schedule": "daily"})
        repo.put({"source_id": "h2", "tenant_id": "t", "source_type": "website_url", "name": "h2",
                  "config": {}, "status": "ready", "sync_schedule": "hourly"})
        hourly = list(repo.list_by_schedule("hourly"))
        assert {s["source_id"] for s in hourly} == {"h1", "h2"}

    def test_update_with_config_payload(self, local_env):
        from src.common.backends.factory import get_source_repo
        repo = get_source_repo()
        repo.put({"source_id": "u1", "tenant_id": "t", "source_type": "website_url",
                  "name": "u1", "config": {"url": "old"}, "status": "pending"})
        repo.update("u1", {"config": {"url": "new"}, "status": "ready"})
        got = repo.get_by_id("u1")
        assert got["config"]["url"] == "new"
        assert got["status"] == "ready"


class TestSqliteAnalyticsRepository:
    def test_log_and_query(self, local_env):
        from src.common.backends.factory import get_analytics_repo
        repo = get_analytics_repo()
        for i in range(3):
            repo.log_query({
                "tenant_id": "t",
                "timestamp": f"2026-01-{i+1:02d}T00:00:00Z",
                "tool_name": "docs_search",
                "query": f"q{i}",
                "results_count": i,
                "latency_ms": 10 * i,
            })
        rows = repo.query_logs("t", "2026-01-01T00:00:00Z")
        assert len(rows) == 3
        # since filter excludes
        rows2 = repo.query_logs("t", "2026-01-03T00:00:00Z")
        assert len(rows2) == 1


class TestFilesystemStorage:
    def test_put_get_delete(self, local_env):
        from src.common.backends.factory import get_storage
        s = get_storage()
        key = "uploads/tenant-x/uuid-y/file.txt"
        s.put(key, b"hello world", "text/plain")
        assert s.get(key) == b"hello world"
        s.delete(key)
        # Delete is idempotent
        s.delete(key)

    def test_refuses_path_traversal(self, local_env):
        from src.common.backends.factory import get_storage
        s = get_storage()
        with pytest.raises(ValueError):
            s.put("../../etc/passwd", b"x")

    def test_presign_returns_descriptor(self, local_env):
        from src.common.backends.factory import get_storage
        s = get_storage()
        url = s.presigned_upload_url("k", "application/pdf", 3600)
        assert url.startswith("local://upload?")
        assert "key=k" in url


class TestSqliteSecretStore:
    def test_roundtrip(self, local_env):
        from src.common.backends.factory import get_secret_store
        store = get_secret_store()
        ref = store.put("test/sec/1", {"token": "abc", "user": "u"})
        assert ref == "test/sec/1"
        assert store.get("test/sec/1") == {"token": "abc", "user": "u"}
        store.delete("test/sec/1")
        assert store.get("test/sec/1") == {}


class TestSqliteJobQueue:
    def test_send_poll_ack(self, local_env):
        from src.common.backends.factory import get_queue
        q = get_queue()
        q.send("crawl", {"source_id": "s1"})
        q.send("crawl", {"source_id": "s2"})
        first = q.poll("crawl", 1)
        assert len(first) == 1
        assert first[0]["body"]["source_id"] == "s1"
        q.ack("crawl", first[0]["receipt"])
        second = q.poll("crawl", 1)
        assert second[0]["body"]["source_id"] == "s2"

    def test_fail_retries(self, local_env):
        from src.common.backends.factory import get_queue
        q = get_queue()
        q.send("index", {"x": 1})
        job = q.poll("index", 1)[0]
        q.fail("index", job["receipt"], "boom")
        # Retry returns to pending
        job2 = q.poll("index", 1)
        assert job2[0]["receipt"] == job["receipt"]
        assert job2[0]["attempts"] == 2

    def test_fail_terminal_after_max_attempts(self, local_env):
        from src.common.backends.factory import get_queue
        from src.common.backends.local.sqlite_queue import MAX_ATTEMPTS
        q = get_queue()
        q.send("crawl", {"y": 1})
        for _ in range(MAX_ATTEMPTS):
            job = q.poll("crawl", 1)
            assert job
            q.fail("crawl", job[0]["receipt"], "bad")
        # After MAX_ATTEMPTS, no longer pending
        assert q.poll("crawl", 1) == []


class TestJwtAutoInit:
    def test_creates_secret_in_local_mode(self, local_env, monkeypatch):
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        from src.common.backends.local.init_jwt import ensure_jwt_secret
        secret = ensure_jwt_secret()
        assert len(secret) > 32
        # Second call returns the same secret
        secret2 = ensure_jwt_secret()
        assert secret == secret2
        key_path = local_env / "jwt.key"
        assert key_path.exists()


class TestLogEmailSender:
    def test_writes_outbox(self, local_env):
        from src.common.backends.factory import get_email_sender
        sender = get_email_sender()
        sender.send("u@x.com", "Hi", "body text")
        import json
        outbox_path = local_env / "email_outbox.json"
        assert outbox_path.exists()
        data = json.loads(outbox_path.read_text())
        assert data["u@x.com"]["body"] == "body text"
