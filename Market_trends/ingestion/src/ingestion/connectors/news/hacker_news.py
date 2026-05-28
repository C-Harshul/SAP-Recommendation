"""Hacker News Firebase API — AI-related stories above score threshold."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Any

import httpx

from ingestion.connectors.base import BaseConnector
from ingestion.errors import SourceUnavailableError


class HackerNewsConnector(BaseConnector):
    requests_per_minute = 30.0

    def fetch(self, since: datetime | None) -> Iterator[dict[str, Any]]:
        keywords: list[str] = self._config.get("keywords", [])
        min_score: int = int(self._config.get("min_score", 50))
        base = "https://hacker-news.firebaseio.com/v0"

        try:
            with httpx.Client(timeout=30.0) as client:
                top = client.get(f"{base}/topstories.json").json()
                # TODO: paginate beyond first N ids for production volume
                for story_id in (top or [])[:200]:
                    self._rate_limit()
                    item_resp = client.get(f"{base}/item/{story_id}.json")
                    if item_resp.status_code >= 500:
                        raise SourceUnavailableError(self.source_id)
                    item = item_resp.json()
                    if not item or item.get("type") != "story":
                        continue
                    title = (item.get("title") or "").lower()
                    if not any(kw.lower() in title for kw in keywords):
                        continue
                    if (item.get("score") or 0) < min_score:
                        continue
                    # TODO: map Unix time to timezone-aware datetime for since filter
                    yield {
                        "external_id": str(item["id"]),
                        "source_url": item.get("url"),
                        "source_published_at": None,
                        "raw": item,
                    }
        except httpx.RequestError as exc:
            raise SourceUnavailableError(self.source_id, str(exc)) from exc
