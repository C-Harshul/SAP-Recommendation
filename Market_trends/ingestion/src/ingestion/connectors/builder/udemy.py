"""
Udemy AI/ML course listings — Affiliate API preferred, Playwright fallback.

ToS: Udemy Affiliate Program terms apply; verify before Playwright fallback.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Any

from ingestion.connectors.base import BaseConnector
from ingestion.errors import ConnectorError


class UdemyConnector(BaseConnector):
    cadence_minutes = 360

    def fetch(self, since: datetime | None) -> Iterator[dict[str, Any]]:
        # TODO: Udemy Affiliate API course search with AI/ML keywords
        # TODO: Playwright fallback if affiliate credentials absent
        raise ConnectorError("udemy connector not yet implemented")
