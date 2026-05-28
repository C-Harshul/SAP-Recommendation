"""Run connectors by cadence group or single source."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from ingestion.connectors.registry import build_all_connectors, build_connector, load_sources_yaml
from ingestion.models.envelope import RunResult

if TYPE_CHECKING:
    from ingestion.io.s3_writer import S3Writer
    from ingestion.io.state_store import StateStore
    from ingestion.runtime.metrics import MetricsEmitter
    from ingestion.runtime.rate_limiter import RateLimiterRegistry

log = structlog.get_logger()


class Scheduler:
    """Execute ingestion runs for one or all sources."""

    def __init__(
        self,
        writer: S3Writer,
        state: StateStore,
        rate_limiters: RateLimiterRegistry,
        metrics: MetricsEmitter | None = None,
    ) -> None:
        self._writer = writer
        self._state = state
        self._rate_limiters = rate_limiters
        self._metrics = metrics

    def run_source(self, source_id: str) -> RunResult:
        sources = load_sources_yaml()
        match = next((s for s in sources if s["id"] == source_id), None)
        if not match:
            raise ValueError(f"Unknown source_id: {source_id}")
        connector = build_connector(
            match, self._writer, self._state, self._rate_limiters, self._metrics
        )
        return connector.run()

    def run_all(self, cadence_minutes: int | None = None) -> list[RunResult]:
        connectors = build_all_connectors(
            self._writer, self._state, self._rate_limiters, self._metrics
        )
        if cadence_minutes is not None:
            connectors = [c for c in connectors if c.cadence_minutes == cadence_minutes]
        results: list[RunResult] = []
        for connector in connectors:
            try:
                results.append(connector.run())
            except Exception as exc:
                from datetime import UTC, datetime

                log.error("run_failed", source_id=connector.source_id, error=str(exc))
                results.append(
                    RunResult(
                        source_id=connector.source_id,
                        category=connector.category,
                        errors=1,
                        run_timestamp=datetime.now(UTC),
                    )
                )
        return results

    def run_group(self, group: str) -> list[RunResult]:
        """group: rss_30 | api_60 | playwright_360 | arxiv_1440"""
        cadence_map = {
            "rss_30": 30,
            "api_60": 60,
            "playwright_360": 360,
            "arxiv_1440": 1440,
        }
        cadence = cadence_map.get(group)
        if cadence is None:
            raise ValueError(f"Unknown group: {group}")
        return self.run_all(cadence_minutes=cadence)
