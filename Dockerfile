# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.11

# ---- build deps ------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS build
WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc curl libxml2 libxslt1.1 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Install into the system site-packages so any user can import them.
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir "bcrypt<4.0"

# ---- runtime ---------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime
WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends libxml2 libxslt1.1 curl \
 && rm -rf /var/lib/apt/lists/*

# Copy system site-packages and binaries from the build stage
COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=build /usr/local/bin /usr/local/bin

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    BACKEND=local \
    LOCAL_DATA_DIR=/data \
    EMBEDDING_PROVIDER=local

# Non-root user; ensure data + app are owned by it
RUN useradd -u 1000 -m kmcp \
 && mkdir -p /data /app/data \
 && chown -R kmcp:kmcp /data /app

COPY --chown=kmcp:kmcp . /app
USER kmcp

EXPOSE 8000 8081

# Default = MCP server. Compose overrides command: per service.
CMD ["uvicorn", "src.mcp_server.handler:app", "--host", "0.0.0.0", "--port", "8000"]
