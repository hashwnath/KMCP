FROM python:3.11-slim as build
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libxml2 libxslt1.1 curl && rm -rf /var/lib/apt/lists/*
COPY --from=build /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH PYTHONUNBUFFERED=1
COPY . .
EXPOSE 8000
CMD ["uvicorn", "src.mcp_server.handler:app", "--host", "0.0.0.0", "--port", "8000"]
