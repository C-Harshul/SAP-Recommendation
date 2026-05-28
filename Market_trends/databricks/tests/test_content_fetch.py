"""Local tests for URL content extraction (no Spark)."""

from __future__ import annotations

import pytest

from content_fetch import fetch_article_content


def test_no_url_uses_summary() -> None:
    r = fetch_article_content(None, feed_summary="RSS snippet")
    assert r["content_fetch_status"] == "no_url"
    assert r["body_text"] == "RSS snippet"


def test_invalid_url_handled() -> None:
    r = fetch_article_content("not-a-valid-url", feed_summary="x", delay_seconds=0)
    assert r["content_fetch_status"] in ("error", "http_error", "empty_extract", "skipped")
