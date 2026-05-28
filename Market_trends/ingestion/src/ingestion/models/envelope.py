"""Bronze record envelope — shared shape for all sources."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RecordEnvelope(BaseModel):
    """Standard bronze JSONL record."""

    source_id: str
    category: str
    ingested_at: datetime
    source_published_at: datetime | None = None
    source_url: str | None = None
    external_id: str
    raw: dict[str, Any] = Field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        return data


class RunResult(BaseModel):
    """Outcome of a single connector run."""

    source_id: str
    category: str
    records_ingested: int = 0
    bytes_written: int = 0
    dlq_count: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    run_timestamp: datetime
    bronze_path: str | None = None
    cursor_advanced_to: datetime | None = None


class SourceCursor(BaseModel):
    """Per-source dedup cursor persisted in S3."""

    source_id: str
    last_external_ids: list[str] = Field(default_factory=list)
    last_run_at: datetime | None = None
    last_source_published_at: datetime | None = None
    last_successful_run_at: datetime | None = None
