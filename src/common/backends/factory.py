"""Backend factory — single point that maps BACKEND env to concrete adapters.

Usage in callers::

    from src.common.backends.factory import get_tenant_repo
    repo = get_tenant_repo()
    tenant = repo.get_by_id(tid)

In tests::

    from src.common.backends.factory import reset_backend_factories
    reset_backend_factories()  # clear cache between BACKEND switches
"""

from __future__ import annotations

from functools import lru_cache

from src.common.backends.database import (
    AnalyticsRepository,
    SourceRepository,
    TenantRepository,
)
from src.common.backends.email import EmailSender
from src.common.backends.queue import JobQueue
from src.common.backends.secrets import SecretStore
from src.common.backends.storage import ObjectStorage
from src.common.config import get_config


# ---------------------------------------------------------------------------
# Cached factory functions
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_tenant_repo() -> TenantRepository:
    backend = get_config().backend.lower()
    if backend == "aws":
        from src.common.backends.aws.dynamo_repos import DynamoTenantRepository
        return DynamoTenantRepository()
    if backend == "local":
        from src.common.backends.local.sqlite_db import SqliteTenantRepository
        return SqliteTenantRepository()
    raise ValueError(f"Unknown BACKEND: {backend!r}")


@lru_cache(maxsize=1)
def get_source_repo() -> SourceRepository:
    backend = get_config().backend.lower()
    if backend == "aws":
        from src.common.backends.aws.dynamo_repos import DynamoSourceRepository
        return DynamoSourceRepository()
    if backend == "local":
        from src.common.backends.local.sqlite_db import SqliteSourceRepository
        return SqliteSourceRepository()
    raise ValueError(f"Unknown BACKEND: {backend!r}")


@lru_cache(maxsize=1)
def get_analytics_repo() -> AnalyticsRepository:
    backend = get_config().backend.lower()
    if backend == "aws":
        from src.common.backends.aws.dynamo_repos import DynamoAnalyticsRepository
        return DynamoAnalyticsRepository()
    if backend == "local":
        from src.common.backends.local.sqlite_db import SqliteAnalyticsRepository
        return SqliteAnalyticsRepository()
    raise ValueError(f"Unknown BACKEND: {backend!r}")


@lru_cache(maxsize=1)
def get_queue() -> JobQueue:
    backend = get_config().backend.lower()
    if backend == "aws":
        from src.common.backends.aws.sqs_queue import SqsJobQueue
        return SqsJobQueue()
    if backend == "local":
        from src.common.backends.local.sqlite_queue import SqliteJobQueue
        return SqliteJobQueue()
    raise ValueError(f"Unknown BACKEND: {backend!r}")


@lru_cache(maxsize=1)
def get_storage() -> ObjectStorage:
    backend = get_config().backend.lower()
    if backend == "aws":
        from src.common.backends.aws.s3_storage import S3ObjectStorage
        return S3ObjectStorage()
    if backend == "local":
        from src.common.backends.local.fs_storage import FilesystemStorage
        return FilesystemStorage()
    raise ValueError(f"Unknown BACKEND: {backend!r}")


@lru_cache(maxsize=1)
def get_secret_store() -> SecretStore:
    backend = get_config().backend.lower()
    if backend == "aws":
        from src.common.backends.aws.secrets_manager import SecretsManagerStore
        return SecretsManagerStore()
    if backend == "local":
        from src.common.backends.local.sqlite_secrets import SqliteSecretStore
        return SqliteSecretStore()
    raise ValueError(f"Unknown BACKEND: {backend!r}")


@lru_cache(maxsize=1)
def get_email_sender() -> EmailSender:
    backend = get_config().backend.lower()
    if backend == "aws":
        from src.common.backends.aws.ses_email import SesEmailSender
        return SesEmailSender()
    if backend == "local":
        from src.common.backends.local.log_email import LogEmailSender
        return LogEmailSender()
    raise ValueError(f"Unknown BACKEND: {backend!r}")


# ---------------------------------------------------------------------------
# Reset (tests)
# ---------------------------------------------------------------------------

def reset_backend_factories() -> None:
    """Clear cached factory results — call when BACKEND or LOCAL_DATA_DIR changes."""
    get_tenant_repo.cache_clear()
    get_source_repo.cache_clear()
    get_analytics_repo.cache_clear()
    get_queue.cache_clear()
    get_storage.cache_clear()
    get_secret_store.cache_clear()
    get_email_sender.cache_clear()
