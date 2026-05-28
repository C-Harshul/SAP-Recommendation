"""Coursera Catalog API — new AI specializations and certificates."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Any

from ingestion.connectors.base import BaseConnector
from ingestion.errors import ConnectorError


class CourseraConnector(BaseConnector):
    def fetch(self, since: datetime | None) -> Iterator[dict[str, Any]]:
        # TODO: Coursera Catalog API with COURSERA_API_KEY
        raise ConnectorError("coursera connector not yet implemented")
