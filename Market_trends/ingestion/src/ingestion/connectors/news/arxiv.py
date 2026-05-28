"""arXiv cs.AI / cs.LG / cs.CL via Atom feed."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Any

from ingestion.connectors.base import BaseConnector
from ingestion.errors import ConnectorError


class ArxivConnector(BaseConnector):
    requests_per_minute = 3.0
    cadence_minutes = 1440

    def fetch(self, since: datetime | None) -> Iterator[dict[str, Any]]:
        # TODO: OAI-PMH or http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.LG
        raise ConnectorError("arxiv connector not yet implemented")
