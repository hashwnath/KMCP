#!/usr/bin/env python3
"""Seed KnowledgeMCP with popular documentation sites for demo/testing."""

import os
import sys
import httpx

ADMIN_API_URL = os.getenv("ADMIN_API_URL", "http://localhost:8081").rstrip("/")
DEMO_EMAIL = os.getenv("DEMO_EMAIL", "demo@knowledgemcp.io")
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "demo-password-123")
DEMO_NAME = os.getenv("DEMO_NAME", "Demo Tenant")

DEMO_SITES = [
    {"name": "Stripe API", "sitemap": "https://docs.stripe.com/sitemap.xml"},
    {"name": "MongoDB Docs", "sitemap": "https://docs.mongodb.com/manual/sitemap.xml"},
    {"name": "FastAPI", "sitemap": "https://fastapi.tiangolo.com/sitemap.xml"},
    {"name": "Tailwind CSS", "sitemap": "https://tailwindcss.com/sitemap.xml"},
    {"name": "Redis", "sitemap": "https://redis.io/sitemap.xml"},
]


def authenticate():
    resp = httpx.post(f"{ADMIN_API_URL}/api/auth/signup", json={
        "email": DEMO_EMAIL, "password": DEMO_PASSWORD, "name": DEMO_NAME,
    }, timeout=10)
    if resp.status_code == 201:
        data = resp.json()
        return data["token"], data["api_key"]
    if resp.status_code == 409:
        resp = httpx.post(f"{ADMIN_API_URL}/api/auth/login", json={
            "email": DEMO_EMAIL, "password": DEMO_PASSWORD,
        }, timeout=10)
        if resp.status_code == 200:
            token = resp.json()["token"]
            me = httpx.get(f"{ADMIN_API_URL}/api/tenants/me",
                           headers={"Authorization": f"Bearer {token}"}, timeout=10)
            return token, me.json().get("api_key", "")
    print(f"Auth failed: {resp.status_code} {resp.text}")
    sys.exit(1)


def main():
    print(f"Seeding against {ADMIN_API_URL}")
    token, api_key = authenticate()
    print(f"Authenticated. API key: {api_key[:20]}...")

    for site in DEMO_SITES:
        resp = httpx.post(f"{ADMIN_API_URL}/api/sources", json={
            "source_type": "website_url",
            "name": site["name"],
            "config": {"sitemap_url": site["sitemap"], "url": site["sitemap"].replace("/sitemap.xml", "")},
        }, headers={"Authorization": f"Bearer {token}"}, timeout=10)
        status = "ok" if resp.status_code == 201 else f"FAIL({resp.status_code})"
        print(f"  {site['name']}: {status}")

    print(f"\nDone. API key for MCP: {api_key}")


if __name__ == "__main__":
    main()
