"""End-to-end signup → create source → enqueue path in BACKEND=local mode."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from src.admin.routes import routes


@pytest.fixture
def local_app(monkeypatch, tmp_path):
    monkeypatch.setenv("BACKEND", "local")
    monkeypatch.setenv("LOCAL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-for-e2e")
    from src.common.config import get_config
    get_config.cache_clear()
    import src.common.config as _cfg
    _cfg.settings = get_config()
    from src.common.backends.factory import reset_backend_factories
    reset_backend_factories()
    from src.common.backends.local import sqlite_db as _sdb
    _sdb._DB_INITIALIZED.clear()
    app = Starlette(routes=routes)
    return TestClient(app)


def test_signup_creates_tenant_in_sqlite(local_app):
    resp = local_app.post(
        "/api/auth/signup",
        json={"email": "e2e@example.com", "password": "pass1234", "name": "E2E"},
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["token"]
    assert resp.json()["api_key"].startswith("kmcp_sk_")

    me = local_app.get(
        "/api/tenants/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == "e2e@example.com"


def test_create_source_enqueues_local_job(local_app):
    sign = local_app.post(
        "/api/auth/signup",
        json={"email": "src@example.com", "password": "pass1234", "name": "Src"},
    )
    token = sign.json()["token"]

    resp = local_app.post(
        "/api/sources",
        json={
            "source_type": "paste_text",
            "name": "test note",
            "config": {"text": "hello local mode", "title": "T"},
            "sync_schedule": "manual",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    source_id = resp.json()["source_id"]

    # The job should now exist in the SQLite jobs table
    from src.common.backends.local.sqlite_db import _connect
    rows = _connect().execute(
        "SELECT queue_name, status, payload_json FROM jobs"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["queue_name"] == "crawl"
    payload = json.loads(rows[0]["payload_json"])
    assert payload["source_id"] == source_id


def test_local_mode_magic_link_writes_outbox(local_app, tmp_path):
    sign = local_app.post(
        "/api/auth/signup",
        json={"email": "ml@example.com", "password": "p1234567", "name": "ML"},
    )
    assert sign.status_code == 201

    resp = local_app.post(
        "/api/auth/magic-link/request", json={"email": "ml@example.com"}
    )
    assert resp.status_code == 200
    assert resp.json() == {"sent": True}

    outbox = tmp_path / "email_outbox.json"
    assert outbox.exists()
    data = json.loads(outbox.read_text())
    assert "ml@example.com" in data
    assert "/login?magic_token=" in data["ml@example.com"]["body"]
