"""Ideanote public idea boards and changelog via REST API."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Any

from ingestion.connectors.base import BaseConnector
from ingestion.errors import ConnectorError


class IdeanoteConnector(BaseConnector):
    def fetch(self, since: datetime | None) -> Iterator[dict[str, Any]]:
        # TODO: authenticate with IDEANOTE_API_KEY and pull public boards
        raise ConnectorError("ideanote connector not yet implemented")
