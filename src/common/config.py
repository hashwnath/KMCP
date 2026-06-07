"""Environment configuration loader for KnowledgeMCP."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables with sensible defaults."""

    # Backend selector: "local" (default, zero AWS) or "aws"
    backend: Literal["local", "aws"] = Field(default="local", alias="BACKEND")
    local_data_dir: str = Field(default="./data", alias="LOCAL_DATA_DIR")
    # Dev convenience: bypass magic-link delivery in local mode
    dev_auth_allow: bool = Field(default=False, alias="DEV_AUTH_ALLOW")

    # AWS — Lambda reserves AWS_REGION, so we accept APP_AWS_REGION too
    aws_region: str = Field(
        default="us-east-1",
        validation_alias=AliasChoices("APP_AWS_REGION", "AWS_REGION", "aws_region"),
    )
    aws_account_id: str = Field(
        default="",
        validation_alias=AliasChoices("APP_AWS_ACCOUNT_ID", "AWS_ACCOUNT_ID", "aws_account_id"),
    )

    # OpenSearch
    opensearch_endpoint: str = Field(default="", alias="OPENSEARCH_ENDPOINT")
    opensearch_collection_name: str = Field(
        default="knowledgemcp", alias="OPENSEARCH_COLLECTION_NAME"
    )

    # Embedding
    embedding_provider: Literal["bedrock", "openai", "local"] = Field(
        default="local", alias="EMBEDDING_PROVIDER"
    )
    local_embedding_model: str = Field(
        default="BAAI/bge-small-en-v1.5", alias="LOCAL_EMBEDDING_MODEL"
    )
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    bedrock_model_id: str = Field(
        default="amazon.titan-embed-text-v2:0", alias="BEDROCK_MODEL_ID"
    )

    # MCP Server
    mcp_server_port: int = Field(default=8000, alias="MCP_SERVER_PORT")
    mcp_server_host: str = Field(default="0.0.0.0", alias="MCP_SERVER_HOST")
    mcp_base_url: str = Field(default="http://localhost:8000", alias="MCP_BASE_URL")
    frontend_origin: str = Field(default="http://localhost:3000", alias="FRONTEND_ORIGIN")
    app_base_url: str = Field(default="http://localhost:3000", alias="APP_BASE_URL")
    user_agent: str = Field(
        default="KnowledgeMCP/1.0 (+https://knowledgemcp.io)", alias="USER_AGENT"
    )
    crawl_delay_seconds: float = Field(default=0.5, alias="CRAWL_DELAY_SECONDS")
    debug: bool = Field(default=False, alias="DEBUG")
    skip_auth: bool = Field(default=False, alias="SKIP_AUTH")

    # Auth
    jwt_secret_key: str = Field(default="", alias="JWT_SECRET_KEY")
    admin_api_key: str = Field(default="", alias="ADMIN_API_KEY")
    ses_from_email: str = Field(default="", alias="SES_FROM_EMAIL")
    signup_code: str = Field(default="", alias="SIGNUP_CODE")

    # Rate Limits
    max_queries_per_hour: int = Field(default=100, alias="MAX_QUERIES_PER_HOUR")
    max_docs_per_tenant: int = Field(default=500, alias="MAX_DOCS_PER_TENANT")
    rate_limit_per_second: int = Field(default=10, alias="RATE_LIMIT_PER_SECOND")
    rate_limit_burst: int = Field(default=30, alias="RATE_LIMIT_BURST")

    # SQS Queues
    crawl_queue_url: str = Field(default="", alias="CRAWL_QUEUE_URL")
    index_queue_url: str = Field(default="", alias="INDEX_QUEUE_URL")

    # DynamoDB Tables
    tenants_table: str = Field(default="knowledgemcp-tenants", alias="TENANTS_TABLE")
    sources_table: str = Field(default="knowledgemcp-sources", alias="SOURCES_TABLE")
    analytics_table: str = Field(
        default="knowledgemcp-analytics", alias="ANALYTICS_TABLE"
    )

    # S3
    content_bucket: str = Field(default="knowledgemcp-content", alias="CONTENT_BUCKET")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "frozen": True,
        "populate_by_name": True,
    }


@lru_cache(maxsize=1)
def get_config() -> Settings:
    """Return a cached singleton of the application settings."""
    return Settings()


settings = get_config()
