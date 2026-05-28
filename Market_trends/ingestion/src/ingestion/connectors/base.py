"""Base connector contract and run orchestration."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

from ingestion.errors import ConnectorError, SourceUnavailableError
from ingestion.models.envelope import RecordEnvelope, RunResult
from ingestion.runtime.retry import with_retry

if TYPE_CHECKING:
    from ingestion.io.s3_writer import S3Writer
    from ingestion.io.state_store import StateStore
    from ingestion.runtime.metrics import MetricsEmitter
    from ingestion.runtime.rate_limiter import RateLimiterRegistry

log = structlog.get_logger()


class BaseConnector(ABC):
    source_id: str
    category: str
    cadence_minutes: int = 60
    requests_per_minute: float = 30.0
    max_cursor_ids: int = 5000

    def __init__(
        self,
        writer: S3Writer,
        state: StateStore,
        rate_limiters: RateLimiterRegistry,
        metrics: MetricsEmitter | None = None,
        source_config: dict[str, Any] | None = None,
    ) -> None:
        self._writer = writer
        self._state = state
        self._rate_limiters = rate_limiters
        self._metrics = metrics
        self._config = source_config or {}

    @abstractmethod
    def fetch(self, since: datetime | None) -> Iterator[dict[str, Any]]:
        """Yield dicts with keys: external_id, raw, source_published_at?, source_url?."""

    def _rate_limit(self) -> None:
        bucket = self._rate_limiters.get(self.source_id, self.requests_per_minute)
        bucket.acquire()

    def _wrap_record(self, item: dict[str, Any]) -> RecordEnvelope:
        external_id = str(item["external_id"])
        raw = item.get("raw", item)
        if "external_id" in raw and raw is not item.get("raw"):
            pass
        elif raw is item:
            skip = ("external_id", "source_published_at", "source_url")
            raw = {k: v for k, v in item.items() if k not in skip}
        return RecordEnvelope(
            source_id=self.source_id,
            category=self.category,
            ingested_at=datetime.now(UTC),
            source_published_at=item.get("source_published_at"),
            source_url=item.get("source_url"),
            external_id=external_id,
            raw=raw if isinstance(raw, dict) else {"value": raw},
        )

    def run(self) -> RunResult:
        start = time.monotonic()
        run_ts = datetime.now(UTC)
        cursor = self._state.load(self.source_id)
        since = cursor.last_source_published_at
        seen_ids = set(cursor.last_external_ids)

        envelopes: list[RecordEnvelope] = []
        dlq_batch: list[dict[str, object]] = []
        errors = 0
        max_published: datetime | None = since

        def _do_fetch() -> list[dict[str, Any]]:
            self._rate_limit()
            return list(self.fetch(since))

        try:
            items = with_retry(_do_fetch)
        except SourceUnavailableError as exc:
            log.error("fetch_failed", source_id=self.source_id, error=str(exc))
            return RunResult(
                source_id=self.source_id,
                category=self.category,
                errors=1,
                duration_seconds=time.monotonic() - start,
                run_timestamp=run_ts,
            )
        except Exception as exc:
            log.error("fetch_failed", source_id=self.source_id, error=str(exc))
            raise ConnectorError(f"{self.source_id} fetch failed: {exc}") from exc

        for item in items:
            try:
                ext_id = str(item["external_id"])
                if ext_id in seen_ids:
                    continue
                env = self._wrap_record(item)
                envelopes.append(env)
                seen_ids.add(ext_id)
                pub = item.get("source_published_at")
                if isinstance(pub, datetime) and (max_published is None or pub > max_published):
                    max_published = pub
            except Exception as exc:
                errors += 1
                dlq_batch.append({"source_id": self.source_id, "item": item, "error": str(exc)})

        bronze_path = None
        bytes_written = 0
        if envelopes:
            bronze_path, bytes_written = self._writer.write_records(
                envelopes, self.category, self.source_id, run_ts
            )

        dlq_count = 0
        if dlq_batch:
            _, dlq_bytes = self._writer.write_dlq(dlq_batch, self.source_id, run_ts)
            dlq_count = len(dlq_batch)
            bytes_written += dlq_bytes

        new_ids = list(seen_ids)[-self.max_cursor_ids :]
        cursor.last_external_ids = new_ids
        if max_published:
            cursor.last_source_published_at = max_published
        cursor.last_successful_run_at = run_ts
        self._state.save(cursor)

        duration = time.monotonic() - start
        result = RunResult(
            source_id=self.source_id,
            category=self.category,
            records_ingested=len(envelopes),
            bytes_written=bytes_written,
            dlq_count=dlq_count,
            errors=errors,
            duration_seconds=duration,
            run_timestamp=run_ts,
            bronze_path=bronze_path,
            cursor_advanced_to=max_published,
        )

        if self._metrics:
            self._metrics.emit_run_metrics(
                self.source_id,
                result.records_ingested,
                result.errors,
                result.dlq_count,
            )

        log.info(
            "run_complete",
            source_id=self.source_id,
            records=result.records_ingested,
            bytes=result.bytes_written,
            duration_s=round(duration, 3),
            errors=result.errors,
            dlq=result.dlq_count,
        )
        return result
