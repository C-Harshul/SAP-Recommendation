"""Hugging Face Hub trending models, datasets, and spaces."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Any

from ingestion.connectors.base import BaseConnector
from ingestion.errors import ConnectorError


class HuggingFaceTrendingConnector(BaseConnector):
    requests_per_minute = 20.0

    def fetch(self, since: datetime | None) -> Iterator[dict[str, Any]]:
        # TODO: GET https://huggingface.co/api/models?sort=trending
        # TODO: repeat for datasets and spaces endpoints
        raise ConnectorError("huggingface_trending connector not yet implemented")
