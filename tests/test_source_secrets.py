"""Tests for source secret splitting/redaction helpers."""

from unittest.mock import MagicMock

from src.admin.routes import _split_sensitive_config, _redact_source_config
from src.common.source_secrets import migrate_source_item_if_needed


def test_split_sensitive_config_moves_secret_fields():
    public, sensitive = _split_sensitive_config(
        {
            "provider": "s3",
            "bucket": "docs-bucket",
            "aws_access_key": "AKIA...",
            "aws_secret_key": "super-secret",
            "token": "abc",
        }
    )

    assert public["provider"] == "s3"
    assert public["bucket"] == "docs-bucket"
    assert "aws_secret_key" not in public
    assert "token" not in public
    assert sensitive["aws_secret_key"] == "super-secret"
    assert sensitive["token"] == "abc"


def test_redact_source_config_masks_sensitive_values():
    redacted = _redact_source_config(
        {
            "provider": "gcs",
            "service_account_json": "{\"private_key\":\"...\"}",
            "secret_ref": "arn:aws:secretsmanager:...",
        }
    )

    assert redacted["provider"] == "gcs"
    assert redacted["service_account_json"] == "***"
    assert redacted["secret_ref"].startswith("arn:")


def test_migrate_source_item_moves_inline_secrets(monkeypatch):
    table = MagicMock()
    source = {
        "source_id": "s1",
        "tenant_id": "t1",
        "config": {
            "provider": "s3",
            "bucket": "docs",
            "token": "old-token",
        },
    }

    monkeypatch.setattr(
        "src.common.source_secrets.persist_source_secret",
        lambda tenant_id, source_id, sensitive_config, existing_secret_ref=None: "arn:sm:secret:s1",
    )

    migrated = migrate_source_item_if_needed(table, source)

    assert migrated["config"]["provider"] == "s3"
    assert "token" not in migrated["config"]
    assert migrated["config"]["secret_ref"] == "arn:sm:secret:s1"
    assert table.update_item.call_count == 1
