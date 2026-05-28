"""Per-source cursor persistence in S3."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from ingestion.errors import StateError
from ingestion.models.envelope import SourceCursor

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


class StateStore:
    """Read/write dedup cursors at s3://{bucket}/bronze/_state/{source_id}.json."""

    def __init__(
        self,
        s3_client: S3Client,
        bucket: str,
        prefix: str = "bronze",
    ) -> None:
        self._s3 = s3_client
        self._bucket = bucket
        self._prefix = prefix.rstrip("/")

    def _key(self, source_id: str) -> str:
        return f"{self._prefix}/_state/{source_id}.json"

    def load(self, source_id: str) -> SourceCursor:
        key = self._key(source_id)
        try:
            resp = self._s3.get_object(Bucket=self._bucket, Key=key)
            body = resp["Body"].read().decode("utf-8")
            data = json.loads(body)
            return SourceCursor.model_validate(data)
        except Exception as exc:
            from botocore.exceptions import ClientError

            if isinstance(exc, ClientError) and exc.response["Error"]["Code"] in (
                "NoSuchKey",
                "404",
            ):
                return SourceCursor(source_id=source_id)
            raise StateError(f"Failed to load cursor for {source_id}: {exc}") from exc

    def save(self, cursor: SourceCursor) -> None:
        key = self._key(cursor.source_id)
        cursor.last_run_at = datetime.now(UTC)
        payload = cursor.model_dump_json(indent=2)
        try:
            self._s3.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=payload.encode("utf-8"),
                ContentType="application/json",
            )
        except Exception as exc:
            raise StateError(f"Failed to save cursor for {cursor.source_id}: {exc}") from exc

    def mark_success(self, source_id: str, run_at: datetime | None = None) -> None:
        cursor = self.load(source_id)
        cursor.last_successful_run_at = run_at or datetime.now(UTC)
        self.save(cursor)
