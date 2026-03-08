#!/usr/bin/env python3
"""Test a KnowledgeMCP endpoint with JSON-RPC 2.0 calls."""

import argparse
import json
import httpx


def call_rpc(url: str, api_key: str, tenant: str, method: str, params: dict = None):
    payload = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": 1}
    resp = httpx.post(
        f"{url}/mcp/{tenant}",
        json=payload,
        headers={"x-api-key": api_key, "content-type": "application/json"},
        timeout=30,
    )
    return resp.json()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:8000")
    p.add_argument("--api-key", required=True)
    p.add_argument("--tenant", default="demo")
    args = p.parse_args()

    print("=== tools/list ===")
    print(json.dumps(call_rpc(args.url, args.api_key, args.tenant, "tools/list"), indent=2)[:500])

    print("\n=== docs_search ===")
    print(json.dumps(call_rpc(args.url, args.api_key, args.tenant, "tools/call", {
        "name": "docs_search", "arguments": {"query": "authentication", "tenant_id": args.tenant},
    }), indent=2)[:500])

    print("\n=== code_sample_search ===")
    print(json.dumps(call_rpc(args.url, args.api_key, args.tenant, "tools/call", {
        "name": "code_sample_search", "arguments": {"query": "connection pooling", "tenant_id": args.tenant},
    }), indent=2)[:500])

    print("\n=== docs_fetch ===")
    print(json.dumps(call_rpc(args.url, args.api_key, args.tenant, "tools/call", {
        "name": "docs_fetch", "arguments": {"url": "https://docs.example.com/getting-started", "tenant_id": args.tenant},
    }), indent=2)[:500])

    print("\nAll tests completed.")


if __name__ == "__main__":
    main()
