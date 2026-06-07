"""Targeted tests for admin route hardening behavior."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from starlette.applications import Starlette
from starlette.testclient import TestClient
from starlette.routing import Route

from src.admin.routes import _validate_source_config, request_magic_link


def test_validate_source_config_rejects_unknown_cloud_provider():
    err = _validate_source_config("cloud_storage", {"provider": "dropbox"})
    assert err is not None


def test_validate_source_config_rejects_unknown_wiki_platform():
    err = _validate_source_config("wiki_kb", {"platform": "mediawiki"})
    assert err is not None


def test_magic_link_returns_503_when_ses_not_configured_in_aws_mode(monkeypatch):
    app = Starlette(routes=[Route("/magic", request_magic_link, methods=["POST"])])

    monkeypatch.setattr(
        "src.admin.routes._find_tenant_by_email",
        lambda email: {"tenant_id": "t1", "email": email},
    )
    monkeypatch.setattr(
        "src.admin.routes.get_config",
        lambda: SimpleNamespace(
            backend="aws",
            ses_from_email="",
            app_base_url="https://app.example",
        ),
    )

    client = TestClient(app)
    resp = client.post("/magic", json={"email": "user@example.com"})

    assert resp.status_code == 503
    assert "not configured" in resp.json()["error"].lower()


def test_magic_link_sends_email_and_hides_token(monkeypatch):
    app = Starlette(routes=[Route("/magic", request_magic_link, methods=["POST"])])
    sender = MagicMock()

    monkeypatch.setattr(
        "src.admin.routes._find_tenant_by_email",
        lambda email: {"tenant_id": "t1", "email": email},
    )
    monkeypatch.setattr(
        "src.admin.routes.get_config",
        lambda: SimpleNamespace(
            backend="aws",
            ses_from_email="noreply@example.com",
            app_base_url="https://app.example",
        ),
    )
    monkeypatch.setattr("src.admin.routes.get_email_sender", lambda: sender)

    client = TestClient(app)
    resp = client.post("/magic", json={"email": "user@example.com"})

    assert resp.status_code == 200
    assert resp.json() == {"sent": True}
    assert sender.send.call_count == 1
    # token must NOT appear in the response body
    assert "token" not in resp.json()


def test_magic_link_works_in_local_mode_without_ses_email(monkeypatch):
    app = Starlette(routes=[Route("/magic", request_magic_link, methods=["POST"])])
    sender = MagicMock()

    monkeypatch.setattr(
        "src.admin.routes._find_tenant_by_email",
        lambda email: {"tenant_id": "t1", "email": email},
    )
    monkeypatch.setattr(
        "src.admin.routes.get_config",
        lambda: SimpleNamespace(
            backend="local",
            ses_from_email="",
            app_base_url="http://localhost:3000",
        ),
    )
    monkeypatch.setattr("src.admin.routes.get_email_sender", lambda: sender)

    client = TestClient(app)
    resp = client.post("/magic", json={"email": "user@example.com"})

    assert resp.status_code == 200
    assert resp.json() == {"sent": True}
    sender.send.assert_called_once()
