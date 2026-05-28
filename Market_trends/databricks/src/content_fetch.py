"""
Fetch and extract article text from URLs (used on Databricks workers).

Respects a simple per-process delay to avoid hammering publishers.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx

_LAST_FETCH_BY_HOST: dict[str, float] = {}
_DEFAULT_DELAY = 2.0
_MAX_BODY_CHARS = 80_000
_USER_AGENT = (
    "ExperienceGarage-MarketTrends/1.0 (+https://sap.com; research ingestion; "
    "contact: experience-garage-internal)"
)


def _host(url: str) -> str:
    try:
        return urlparse(url).netloc or "unknown"
    except Exception:
        return "unknown"


def _rate_limit(url: str, delay_seconds: float) -> None:
    host = _host(url)
    now = time.monotonic()
    last = _LAST_FETCH_BY_HOST.get(host, 0.0)
    wait = delay_seconds - (now - last)
    if wait > 0:
        time.sleep(wait)
    _LAST_FETCH_BY_HOST[host] = time.monotonic()


def fetch_article_content(
    url: str | None,
    feed_summary: str | None = None,
    delay_seconds: float = _DEFAULT_DELAY,
) -> dict[str, Any]:
    """
    Return dict with body_text, content_fetch_status, content_fetch_error, content_fetched_at.
    Falls back to feed_summary when URL is missing or fetch fails.
    """
    fetched_at = datetime.now(UTC).isoformat()
    if not url or not str(url).strip():
        return {
            "body_text": (feed_summary or "")[:_MAX_BODY_CHARS] or None,
            "content_fetch_status": "no_url",
            "content_fetch_error": None,
            "content_fetched_at": fetched_at,
        }

    url = str(url).strip()
    try:
        import trafilatura
    except ImportError:
        return {
            "body_text": (feed_summary or "")[:_MAX_BODY_CHARS] or None,
            "content_fetch_status": "skipped",
            "content_fetch_error": "trafilatura not installed on cluster",
            "content_fetched_at": fetched_at,
        }

    _rate_limit(url, delay_seconds)
    try:
        with httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            resp = client.get(url)
            if resp.status_code >= 400:
                return {
                    "body_text": (feed_summary or "")[:_MAX_BODY_CHARS] or None,
                    "content_fetch_status": "http_error",
                    "content_fetch_error": f"HTTP {resp.status_code}",
                    "content_fetched_at": fetched_at,
                }
            html = resp.text
        text = trafilatura.extract(html, url=url, include_comments=False, include_tables=False)
        if text and text.strip():
            return {
                "body_text": text.strip()[:_MAX_BODY_CHARS],
                "content_fetch_status": "ok",
                "content_fetch_error": None,
                "content_fetched_at": fetched_at,
            }
        return {
            "body_text": (feed_summary or "")[:_MAX_BODY_CHARS] or None,
            "content_fetch_status": "empty_extract",
            "content_fetch_error": "trafilatura returned no text",
            "content_fetched_at": fetched_at,
        }
    except Exception as exc:
        return {
            "body_text": (feed_summary or "")[:_MAX_BODY_CHARS] or None,
            "content_fetch_status": "error",
            "content_fetch_error": str(exc)[:500],
            "content_fetched_at": fetched_at,
        }
