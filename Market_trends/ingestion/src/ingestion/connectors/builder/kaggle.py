"""
Kaggle builder-platform connector.

ToS: Kaggle API Terms of Use apply — https://www.kaggle.com/terms
Credentials: KAGGLE_USERNAME + KAGGLE_KEY env vars (or ~/.kaggle/kaggle.json).
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import datetime
from typing import Any

from ingestion.connectors.base import BaseConnector
from ingestion.errors import ConnectorError


class KaggleConnector(BaseConnector):
    """Pull AI/ML-tagged competitions, datasets, and notebooks via official SDK."""

    requests_per_minute = 20.0

    def fetch(self, since: datetime | None) -> Iterator[dict[str, Any]]:
        try:
            from kaggle.api.kaggle_api_extended import KaggleApi
        except ImportError as exc:
            raise ConnectorError("kaggle package not installed") from exc

        tags: list[str] = self._config.get("tags", [])
        content_types: list[str] = self._config.get(
            "content_types", ["competition", "dataset", "notebook"]
        )

        api = KaggleApi()
        if os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY"):
            api.authenticate()
        else:
            try:
                api.authenticate()
            except OSError as exc:
                raise ConnectorError(
                    "Kaggle credentials missing: set KAGGLE_USERNAME/KAGGLE_KEY"
                ) from exc

        tag_search = " ".join(tags) if tags else "machine-learning"

        if "competition" in content_types:
            comps = api.competitions_list(search=tag_search)
            for comp in comps or []:
                yield from self._yield_competition(comp, since)

        if "dataset" in content_types:
            datasets = api.dataset_list(search=tag_search, sort_by="hottest")
            for ds in datasets or []:
                yield from self._yield_dataset(ds, since)

        if "notebook" in content_types:
            notebooks = api.kernels_list(search=tag_search, sort_by="hotness")
            for nb in notebooks or []:
                yield from self._yield_notebook(nb, since)

    def _yield_competition(self, comp: Any, since: datetime | None) -> Iterator[dict[str, Any]]:
        ref = getattr(comp, "ref", None) or str(comp)
        deadline = getattr(comp, "deadline", None)
        published = None
        if deadline:
            try:
                published = datetime.fromisoformat(str(deadline).replace("Z", "+00:00"))
            except ValueError:
                published = None
        if since and published and published <= since:
            return
        slug = ref.split("/")[-1] if "/" in ref else ref
        yield {
            "external_id": f"competition:{slug}",
            "source_published_at": published,
            "source_url": f"https://www.kaggle.com/competitions/{slug}",
            "raw": {
                "content_type": "competition",
                "ref": ref,
                "title": getattr(comp, "title", None),
                "category": getattr(comp, "category", None),
                "deadline": str(deadline) if deadline else None,
            },
        }

    def _yield_dataset(self, ds: Any, since: datetime | None) -> Iterator[dict[str, Any]]:
        ref = getattr(ds, "ref", None) or str(ds)
        slug = ref
        published = None
        if since and published and published <= since:
            return
        yield {
            "external_id": f"dataset:{slug}",
            "source_published_at": published,
            "source_url": f"https://www.kaggle.com/datasets/{slug}",
            "raw": {
                "content_type": "dataset",
                "ref": ref,
                "title": getattr(ds, "title", None),
                "size": getattr(ds, "size", None),
            },
        }

    def _yield_notebook(self, nb: Any, since: datetime | None) -> Iterator[dict[str, Any]]:
        ref = getattr(nb, "ref", None) or str(nb)
        slug = ref.split("/")[-1] if "/" in ref else ref
        published = None
        last_run = getattr(nb, "lastRunTime", None)
        if last_run:
            try:
                published = datetime.fromisoformat(str(last_run).replace("Z", "+00:00"))
            except ValueError:
                published = None
        if since and published and published <= since:
            return
        yield {
            "external_id": f"notebook:{slug}",
            "source_published_at": published,
            "source_url": f"https://www.kaggle.com/code/{ref}",
            "raw": {
                "content_type": "notebook",
                "ref": ref,
                "title": getattr(nb, "title", None),
                "totalVotes": getattr(nb, "totalVotes", None),
            },
        }
