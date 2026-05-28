"""
GitHub Trending (AI/ML topics) via Playwright.

ToS: GitHub Terms of Service — scraping trending page is unofficial; use polite delays.
Robots.txt checked at startup in PlaywrightScraperMixin (TODO).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Any

from ingestion.connectors.base import BaseConnector
from ingestion.errors import ConnectorError


class GitHubTrendingConnector(BaseConnector):
    requests_per_minute = 5.0
    cadence_minutes = 360

    def fetch(self, since: datetime | None) -> Iterator[dict[str, Any]]:
        # TODO: Playwright scrape https://github.com/trending
        # TODO: filter Python/JS repos with AI/ML topics
        raise ConnectorError("github_trending connector not yet implemented")
