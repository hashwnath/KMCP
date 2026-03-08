"""Utilities for handling source credentials without storing inline secrets."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from src.common.aws_clients import get_secretsmanager_client


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
    """Store or update sensitive source credentials in Secrets Manager."""
    sm = get_secretsmanager_client()
    secret_id = existing_secret_ref or f"knowledgemcp/source/{tenant_id}/{source_id}"
    payload = json.dumps(sensitive_config)

    try:
        response = sm.create_secret(
            Name=secret_id,
            SecretString=payload,
            Description="KnowledgeMCP source credentials",
            Tags=[
                {"Key": "app", "Value": "knowledgemcp"},
                {"Key": "tenant_id", "Value": tenant_id},
                {"Key": "source_id", "Value": source_id},
            ],
        )
        return response.get("ARN", secret_id)
    except Exception as exc:  # pragma: no cover - boto3 errors are runtime-specific
        code = getattr(exc, "response", {}).get("Error", {}).get("Code")
        if code != "ResourceExistsException":
            raise

    response = sm.put_secret_value(SecretId=secret_id, SecretString=payload)
    return response.get("ARN", secret_id)


def delete_source_secret(secret_ref: str) -> None:
    """Delete source secret from Secrets Manager (best-effort)."""
    try:
        sm = get_secretsmanager_client()
        sm.delete_secret(SecretId=secret_ref, ForceDeleteWithoutRecovery=True)
    except Exception:
        # Keep source deletion idempotent even if secret cleanup fails.
        pass


def migrate_source_item_if_needed(table: object, item: dict) -> dict:
    """Move inline sensitive fields to Secrets Manager and persist redacted config."""
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
    table.update_item(
        Key={"source_id": source_id},
        UpdateExpression="SET config = :cfg, updated_at = :u",
        ExpressionAttributeValues={":cfg": public_config, ":u": now},
    )

    migrated = dict(item)
    migrated["config"] = public_config
    migrated["updated_at"] = now
    return migrated