"""
HackerRank AI/ML challenges via Playwright.

ToS: Review HackerRank Terms before production scraping.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Any

from ingestion.connectors.base import BaseConnector
from ingestion.errors import ConnectorError


class HackerRankConnector(BaseConnector):
    cadence_minutes = 360

    def fetch(self, since: datetime | None) -> Iterator[dict[str, Any]]:
        # TODO: Playwright scrape AI/ML challenge and skills certification pages
        raise ConnectorError("hackerrank connector not yet implemented")
