"""Lambda entry point for the KnowledgeMCP MCP server (Mangum adapter)."""

from __future__ import annotations

from src.mcp_server.handler import create_app

app = create_app()


def lambda_handler(event: dict, context: object) -> dict:
    """AWS Lambda handler via Mangum ASGI adapter."""
    try:
        from mangum import Mangum

        handler = Mangum(app, lifespan="off")
        return handler(event, context)
    except ImportError:
        return {
            "statusCode": 500,
            "body": '{"error":"mangum package is required for Lambda deployment"}',
            "headers": {"content-type": "application/json"},
        }
