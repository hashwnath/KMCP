# KnowledgeMCP developer Makefile

SHELL := /bin/bash

.PHONY: help up down logs restart status test test-aws test-local clean fmt build

help:  ## Show this help
	@awk 'BEGIN { FS=":.*?## " } /^[a-zA-Z_-]+:.*?## / { printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

up:  ## Start the full local stack (opensearch + admin + mcp + worker + frontend)
	docker compose up -d --build
	@echo ""
	@echo "  Admin   http://localhost:8081"
	@echo "  MCP     http://localhost:8000"
	@echo "  UI      http://localhost:3000"
	@echo ""

down:  ## Stop all services (keeps volumes)
	docker compose down

clean:  ## Stop all services AND delete volumes (DESTROYS local data)
	docker compose down -v

restart:  ## Restart all services
	docker compose restart

status:  ## Show service status
	docker compose ps

logs:  ## Tail all logs
	docker compose logs -f --tail=200

build:  ## Build (or rebuild) all images
	docker compose build

test:  ## Run the full test suite locally (BACKEND=local)
	BACKEND=local EMBEDDING_PROVIDER=local LOCAL_DATA_DIR=$$PWD/.tmp/data \
		python -m pytest tests/ -v

test-aws:  ## Run the test suite in AWS-mock mode (no AWS account needed)
	BACKEND=aws JWT_SECRET_KEY=dev-secret python -m pytest tests/ -v

fmt:  ## Compile-check + (optional) ruff if installed
	python -m compileall src tests
	@which ruff >/dev/null 2>&1 && ruff check src tests || true
