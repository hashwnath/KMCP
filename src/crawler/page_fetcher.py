"""Fetch individual web pages with rate limiting and robots.txt compliance."""

from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from src.common.config import get_config

logger = logging.getLogger(__name__)

_robots_cache: dict[str, RobotFileParser] = {}


async def _get_robots_parser(
    client: httpx.AsyncClient, url: str
) -> RobotFileParser:
    """Fetch and cache the robots.txt for the given URL's origin."""
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    if origin in _robots_cache:
        return _robots_cache[origin]

    rp = RobotFileParser()
    robots_url = f"{origin}/robots.txt"
    try:
        resp = await client.get(robots_url, follow_redirects=True, timeout=10.0)
        if resp.status_code == 200:
            rp.parse(resp.text.splitlines())
        else:
            rp.allow_all = True  # type: ignore[attr-defined]
    except httpx.HTTPError:
        rp.allow_all = True  # type: ignore[attr-defined]

    _robots_cache[origin] = rp
    return rp


def _is_allowed(rp: RobotFileParser, url: str, user_agent: str) -> bool:
    """Check if the URL is allowed by robots.txt."""
    try:
        return rp.can_fetch(user_agent, url)
    except Exception:
        return True


async def fetch_page(url: str) -> tuple[str, int]:
    """Fetch a single web page, returning (html, status_code).

    Returns empty string and status 0 on network errors.
    """
    config = get_config()
    headers = {"User-Agent": config.user_agent}

    async with httpx.AsyncClient(headers=headers) as client:
        rp = await _get_robots_parser(client, url)
        if not _is_allowed(rp, url, config.user_agent):
            logger.info("Robots.txt disallows %s", url)
            return "", 403

        try:
            resp = await client.get(url, follow_redirects=True, timeout=30.0)
            return resp.text, resp.status_code
        except httpx.HTTPError as exc:
            logger.warning("Failed to fetch %s: %s", url, exc)
            return "", 0


async def fetch_pages_batch(
    urls: list[str], concurrency: int = 5
) -> list[tuple[str, str, int]]:
    """Fetch multiple pages concurrently with rate limiting.

    Returns list of (url, html, status_code) tuples.
    """
    config = get_config()
    delay = config.crawl_delay_seconds
    headers = {"User-Agent": config.user_agent}
    semaphore = asyncio.Semaphore(concurrency)
    results: list[tuple[str, str, int]] = []

    async with httpx.AsyncClient(headers=headers) as client:

        async def _fetch_one(target_url: str) -> tuple[str, str, int]:
            async with semaphore:
                rp = await _get_robots_parser(client, target_url)
                if not _is_allowed(rp, target_url, config.user_agent):
                    logger.info("Robots.txt disallows %s", target_url)
                    return target_url, "", 403
                try:
                    resp = await client.get(
                        target_url, follow_redirects=True, timeout=30.0
                    )
                    await asyncio.sleep(delay)
                    return target_url, resp.text, resp.status_code
                except httpx.HTTPError as exc:
                    logger.warning("Failed to fetch %s: %s", target_url, exc)
                    return target_url, "", 0

        tasks = [_fetch_one(u) for u in urls]
        results = await asyncio.gather(*tasks)

    return list(results)
