"""
Forage virtual work experiences (AI/ML/data) via Playwright.

ToS: Review Forage Terms of Service before production use.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Any

from ingestion.connectors.base import BaseConnector
from ingestion.errors import ConnectorError


class ForageConnector(BaseConnector):
    cadence_minutes = 360

    def fetch(self, since: datetime | None) -> Iterator[dict[str, Any]]:
        # TODO: Playwright scrape programs tagged AI/ML/data
        raise ConnectorError("forage connector not yet implemented")
