"""Bronze JSONL.gz writer and DLQ."""

from __future__ import annotations

import gzip
import io
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from ingestion.errors import WriteError
from ingestion.models.envelope import RecordEnvelope

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


class S3Writer:
    """
    Writes gzip JSONL to bronze layout:
    s3://{bucket}/bronze/{category}/{source_id}/dt=YYYY-MM-DD/run_{timestamp}.jsonl.gz
    """

    def __init__(
        self,
        s3_client: S3Client,
        bucket: str,
        prefix: str = "bronze",
    ) -> None:
        self._s3 = s3_client
        self._bucket = bucket
        self._prefix = prefix.rstrip("/")

    def bronze_key(
        self,
        category: str,
        source_id: str,
        run_timestamp: datetime,
    ) -> str:
        dt = run_timestamp.strftime("%Y-%m-%d")
        ts = run_timestamp.strftime("%Y%m%dT%H%M%SZ")
        return f"{self._prefix}/{category}/{source_id}/dt={dt}/run_{ts}.jsonl"

    def dlq_key(self, source_id: str, run_timestamp: datetime) -> str:
        dt = run_timestamp.strftime("%Y-%m-%d")
        ts = run_timestamp.strftime("%Y%m%dT%H%M%SZ")
        return f"{self._prefix}/_dlq/{source_id}/dt={dt}/failed_{ts}.jsonl"

    def write_records(
        self,
        records: list[RecordEnvelope],
        category: str,
        source_id: str,
        run_timestamp: datetime | None = None,
    ) -> tuple[str, int]:
        """Write envelopes as gzip JSONL; returns (s3 key, bytes written)."""
        if not records:
            return "", 0
        run_ts = run_timestamp or datetime.now(UTC)
        key = self.bronze_key(category, source_id, run_ts)
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            for rec in records:
                line = json.dumps(rec.to_json_dict(), default=str) + "\n"
                gz.write(line.encode("utf-8"))
        body = buf.getvalue()
        try:
            self._s3.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=body,
                ContentType="application/gzip",
                ContentEncoding="gzip",
            )
        except Exception as exc:
            raise WriteError(f"Failed to write bronze for {source_id}: {exc}") from exc
        return key, len(body)

    def write_dlq(
        self,
        failed_records: list[dict[str, object]],
        source_id: str,
        run_timestamp: datetime | None = None,
    ) -> tuple[str, int]:
        if not failed_records:
            return "", 0
        run_ts = run_timestamp or datetime.now(UTC)
        key = self.dlq_key(source_id, run_ts)
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            for rec in failed_records:
                line = json.dumps(rec, default=str) + "\n"
                gz.write(line.encode("utf-8"))
        body = buf.getvalue()
        try:
            self._s3.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=body,
                ContentType="application/gzip",
            )
        except Exception as exc:
            raise WriteError(f"Failed to write DLQ for {source_id}: {exc}") from exc
        return key, len(body)
