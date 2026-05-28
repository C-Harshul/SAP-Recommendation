"""Product Hunt GraphQL — artificial-intelligence tagged launches."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Any

from ingestion.connectors.base import BaseConnector
from ingestion.errors import ConnectorError


class ProductHuntConnector(BaseConnector):
    requests_per_minute = 10.0

    def fetch(self, since: datetime | None) -> Iterator[dict[str, Any]]:
        # TODO: implement GraphQL query against Product Hunt API v2
        # Requires PRODUCT_HUNT_TOKEN env var
        raise ConnectorError("product_hunt connector not yet implemented")
