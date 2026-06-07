"""AWS Secrets Manager implementation of the SecretStore Protocol."""

from __future__ import annotations

import json

from src.common.aws_clients import get_secretsmanager_client


class SecretsManagerStore:
    def get(self, secret_id: str) -> dict:
        payload = get_secretsmanager_client().get_secret_value(SecretId=secret_id)
        raw = payload.get("SecretString", "{}")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            value = {}
        return value if isinstance(value, dict) else {}

    def put(self, secret_id: str, value: dict) -> str:
        sm = get_secretsmanager_client()
        body = json.dumps(value)
        try:
            resp = sm.create_secret(
                Name=secret_id,
                SecretString=body,
                Description="KnowledgeMCP source credentials",
            )
            return resp.get("ARN", secret_id)
        except Exception as exc:
            code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            if code != "ResourceExistsException":
                raise
        resp = sm.put_secret_value(SecretId=secret_id, SecretString=body)
        return resp.get("ARN", secret_id)

    def delete(self, secret_id: str) -> None:
        try:
            get_secretsmanager_client().delete_secret(
                SecretId=secret_id,
                ForceDeleteWithoutRecovery=True,
            )
        except Exception:
            # Idempotent: callers expect best-effort delete
            pass
