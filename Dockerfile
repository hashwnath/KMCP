# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.11

# ---- build deps ------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS build
WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc curl libxml2 libxslt1.1 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ---- runtime base ----------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime
WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends libxml2 libxslt1.1 curl \
 && rm -rf /var/lib/apt/lists/*

COPY --from=build /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Local-mode data dir owned by uid 1000 (matches default `node`/`runuser` style)
RUN useradd -u 1000 -m kmcp \
 && mkdir -p /data /app/data \
 && chown -R kmcp:kmcp /data /app

COPY --chown=kmcp:kmcp . /app
USER kmcp

ENV BACKEND=local \
    LOCAL_DATA_DIR=/data \
    EMBEDDING_PROVIDER=local

# Default ports per service (overridden by compose):
#   admin   8081
#   mcp     8000
EXPOSE 8000 8081

# Default entrypoint = MCP server. Compose overrides `command:` per service.
CMD ["uvicorn", "src.mcp_server.handler:app", "--host", "0.0.0.0", "--port", "8000"]
