"""Lambda entry point and standalone Starlette app for the admin API."""

from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware

from src.admin.routes import routes
from src.common.config import get_config

app = Starlette(routes=routes)

cfg = get_config()
origins = [o.strip() for o in cfg.frontend_origin.split(",") if o.strip()] or ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["authorization", "content-type", "x-api-key"],
)


# ---------------------------------------------------------------------------
# AWS Lambda handler (via Mangum)
# ---------------------------------------------------------------------------

def lambda_handler(event: dict, context: object) -> dict:
    """AWS Lambda entry point. Uses Mangum to translate API Gateway events."""
    try:
        from mangum import Mangum
        handler = Mangum(app, lifespan="off")
        return handler(event, context)
    except ImportError:
        # Mangum not installed — return a helpful error for local debugging
        return {
            "statusCode": 500,
            "body": '{"error":"mangum package is required for Lambda deployment"}',
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8081)
