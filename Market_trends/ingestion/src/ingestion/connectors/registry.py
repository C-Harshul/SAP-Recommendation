"""Connector factory from sources.yaml registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ingestion.connectors.base import BaseConnector
from ingestion.connectors.builder.coursera import CourseraConnector
from ingestion.connectors.builder.forage import ForageConnector
from ingestion.connectors.builder.hackerrank import HackerRankConnector
from ingestion.connectors.builder.ideanote import IdeanoteConnector
from ingestion.connectors.builder.kaggle import KaggleConnector
from ingestion.connectors.builder.udemy import UdemyConnector
from ingestion.connectors.news.arxiv import ArxivConnector
from ingestion.connectors.news.github_trending import GitHubTrendingConnector
from ingestion.connectors.news.hacker_news import HackerNewsConnector
from ingestion.connectors.news.huggingface_trending import HuggingFaceTrendingConnector
from ingestion.connectors.news.product_hunt import ProductHuntConnector
from ingestion.connectors.news.rss_generic import RssGenericConnector
from ingestion.io.s3_writer import S3Writer
from ingestion.io.state_store import StateStore
from ingestion.runtime.metrics import MetricsEmitter
from ingestion.runtime.rate_limiter import RateLimiterRegistry

CONNECTOR_CLASSES: dict[str, type[BaseConnector]] = {
    "rss_generic": RssGenericConnector,
    "kaggle": KaggleConnector,
    "hackerrank": HackerRankConnector,
    "ideanote": IdeanoteConnector,
    "udemy": UdemyConnector,
    "coursera": CourseraConnector,
    "forage": ForageConnector,
    "hacker_news": HackerNewsConnector,
    "product_hunt": ProductHuntConnector,
    "huggingface_trending": HuggingFaceTrendingConnector,
    "github_trending": GitHubTrendingConnector,
    "arxiv": ArxivConnector,
}


def load_sources_yaml(path: Path | None = None) -> list[dict[str, Any]]:
    if path is None:
        path = Path(__file__).resolve().parents[1] / "config" / "sources.yaml"
    with path.open() as f:
        data = yaml.safe_load(f)
    return list(data.get("sources", []))


def build_connector(
    source_def: dict[str, Any],
    writer: S3Writer,
    state: StateStore,
    rate_limiters: RateLimiterRegistry,
    metrics: MetricsEmitter | None = None,
) -> BaseConnector:
    connector_name = source_def["connector"]
    cls = CONNECTOR_CLASSES.get(connector_name)
    if cls is None:
        raise ValueError(f"Unknown connector: {connector_name}")

    instance = cls(
        writer=writer,
        state=state,
        rate_limiters=rate_limiters,
        metrics=metrics,
        source_config=source_def.get("config", {}),
    )
    instance.source_id = source_def["id"]
    instance.category = source_def["category"]
    instance.cadence_minutes = source_def.get("cadence_minutes", 60)
    rpm = source_def.get("requests_per_minute")
    if rpm is not None:
        instance.requests_per_minute = float(rpm)
    return instance


def build_all_connectors(
    writer: S3Writer,
    state: StateStore,
    rate_limiters: RateLimiterRegistry,
    metrics: MetricsEmitter | None = None,
    sources_path: Path | None = None,
) -> list[BaseConnector]:
    sources = load_sources_yaml(sources_path)
    return [
        build_connector(s, writer, state, rate_limiters, metrics) for s in sources
    ]
