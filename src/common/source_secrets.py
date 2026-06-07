"""Utilities for handling source credentials via the SecretStore backend.

This module never talks to AWS directly anymore. Storage is delegated to
src.common.backends.factory.get_secret_store(), which dispatches to either
AWS Secrets Manager or a local SQLite-backed store depending on BACKEND.
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.common.backends.factory import get_secret_store


SENSITIVE_CONFIG_KEYS = {
    "api_token",
    "api_key",
    "token",
    "password",
    "secret",
    "aws_secret_key",
    "connection_string",
    "service_account_json",
}


def redact_source_config(config: dict | None) -> dict:
    """Return a safe-to-return copy of source config with secret fields masked."""
    if not isinstance(config, dict):
        return {}
    redacted: dict = {}
    for key, value in config.items():
        if key.lower() in SENSITIVE_CONFIG_KEYS:
            redacted[key] = "***"
        else:
            redacted[key] = value
    return redacted


def split_sensitive_config(config: dict | None) -> tuple[dict, dict]:
    """Split source config into public and sensitive dictionaries."""
    if not isinstance(config, dict):
        return {}, {}
    public: dict = {}
    sensitive: dict = {}
    for key, value in config.items():
        if key.lower() in SENSITIVE_CONFIG_KEYS:
            sensitive[key] = value
        else:
            public[key] = value
    return public, sensitive


def persist_source_secret(
    tenant_id: str,
    source_id: str,
    sensitive_config: dict,
    existing_secret_ref: str | None = None,
) -> str:
    """Store or update sensitive source credentials. Returns canonical ref/ARN."""
    secret_id = existing_secret_ref or f"knowledgemcp/source/{tenant_id}/{source_id}"
    return get_secret_store().put(secret_id, sensitive_config)


def fetch_source_secret(secret_ref: str) -> dict:
    """Read a previously-persisted source secret. Returns empty dict on error."""
    if not secret_ref:
        return {}
    try:
        return get_secret_store().get(secret_ref)
    except Exception:
        return {}


def delete_source_secret(secret_ref: str) -> None:
    """Delete source secret (best-effort)."""
    try:
        get_secret_store().delete(secret_ref)
    except Exception:
        # Keep source deletion idempotent even if secret cleanup fails.
        pass


def migrate_source_item_if_needed(table: object, item: dict) -> dict:
    """Move inline sensitive fields to the SecretStore and persist redacted config.

    `table` is accepted for backwards compatibility with the previous API.
    When provided AND it exposes ``update_item`` (i.e., still a DynamoDB Table),
    we call it directly to preserve existing test expectations. Otherwise we
    fall back to the SourceRepository.
    """
    config = item.get("config", {})
    public_config, sensitive_config = split_sensitive_config(config)
    if not sensitive_config:
        return item

    source_id = item.get("source_id")
    tenant_id = item.get("tenant_id")
    if not source_id or not tenant_id:
        return item

    secret_ref = persist_source_secret(
        tenant_id,
        source_id,
        sensitive_config,
        existing_secret_ref=config.get("secret_ref"),
    )
    public_config["secret_ref"] = secret_ref
    now = datetime.now(timezone.utc).isoformat()

    if table is not None and hasattr(table, "update_item"):
        table.update_item(
            Key={"source_id": source_id},
            UpdateExpression="SET config = :cfg, updated_at = :u",
            ExpressionAttributeValues={":cfg": public_config, ":u": now},
        )
    else:
        from src.common.backends.factory import get_source_repo
        get_source_repo().update(
            source_id,
            {"config": public_config, "updated_at": now},
        )

    migrated = dict(item)
    migrated["config"] = public_config
    migrated["updated_at"] = now
    return migrated
