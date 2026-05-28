"""
Generic RSS connector for news and learning blog feeds.

Uses feedparser; filters entries by optional keyword list in title/summary.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser
import httpx

from ingestion.connectors.base import BaseConnector
from ingestion.errors import ConnectorError, SourceUnavailableError


def _parse_published(entry: dict[str, Any]) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            return datetime(*parsed[:6], tzinfo=UTC)
    for key in ("published", "updated"):
        raw = entry.get(key)
        if raw:
            try:
                return parsedate_to_datetime(raw)
            except (TypeError, ValueError):
                pass
    return None


def _matches_keywords(text: str, keywords: list[str] | None) -> bool:
    if not keywords:
        return True
    lower = text.lower()
    return any(kw.lower() in lower for kw in keywords)


class RssGenericConnector(BaseConnector):
    """Data-driven RSS fetcher configured via sources.yaml."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._feed_url: str = self._config["url"]
        self._keyword_filter: list[str] | None = self._config.get("keyword_filter")

    def fetch(self, since: datetime | None) -> Iterator[dict[str, Any]]:
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                resp = client.get(self._feed_url)
                if resp.status_code >= 500:
                    raise SourceUnavailableError(
                        self.source_id, f"RSS feed returned {resp.status_code}"
                    )
                resp.raise_for_status()
                content = resp.text
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code >= 500:
                raise SourceUnavailableError(self.source_id, str(exc)) from exc
            raise ConnectorError(f"RSS fetch failed for {self.source_id}: {exc}") from exc
        except httpx.RequestError as exc:
            raise SourceUnavailableError(self.source_id, str(exc)) from exc

        feed = feedparser.parse(content)
        for entry in feed.entries:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            combined = f"{title} {summary}"
            if not _matches_keywords(combined, self._keyword_filter):
                continue

            published = _parse_published(entry)
            if since and published and published <= since:
                continue

            external_id = entry.get("id") or entry.get("link") or title
            if not external_id:
                continue

            link = entry.get("link")
            yield {
                "external_id": str(external_id),
                "source_published_at": published,
                "source_url": link,
                "raw": dict(entry),
            }
