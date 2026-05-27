"""Low-level S3 access: list keys and read gzip JSONL / JSON."""

from __future__ import annotations

import gzip
import io
import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any, Iterator

import boto3
import structlog

from recommendation_engine.config.settings import Settings, get_settings

log = structlog.get_logger()

_DT_PATTERN = re.compile(r"dt=(\d{4}-\d{2}-\d{2})")
_SKIP_PREFIXES = ("_state/", "_dlq/")


def get_s3_client(settings: Settings | None = None):
    settings = settings or get_settings()
    session = boto3.Session(
        region_name=settings.aws_region,
        profile_name=settings.aws_profile,
    )
    return session.client(
        "s3",
        endpoint_url=settings.aws_endpoint_url,
    )


def list_keys(
    prefix: str,
    *,
    suffix: str | None = None,
    under_bronze: bool = True,
    settings: Settings | None = None,
) -> list[str]:
    """List object keys under bucket prefix."""
    settings = settings or get_settings()
    client = get_s3_client(settings)
    if under_bronze:
        base = f"{settings.s3_bronze_prefix.rstrip('/')}/"
        full_prefix = f"{base}{prefix.lstrip('/')}" if prefix else base
    else:
        full_prefix = prefix.lstrip("/")
        if full_prefix and not full_prefix.endswith("/"):
            full_prefix += "/"

    keys: list[str] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=settings.s3_bucket, Prefix=full_prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if any(part in key for part in _SKIP_PREFIXES):
                continue
            if suffix and not key.endswith(suffix):
                continue
            keys.append(key)
    return sorted(keys)


def _parse_partition_date(key: str) -> datetime | None:
    match = _DT_PATTERN.search(key)
    if not match:
        return None
    return datetime.strptime(match.group(1), "%Y-%m-%d").replace(tzinfo=UTC)


def filter_keys_by_lookback(keys: list[str], lookback_days: int) -> list[str]:
    if lookback_days <= 0:
        return keys
    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)
    filtered: list[str] = []
    for key in keys:
        dt = _parse_partition_date(key)
        if dt is None or dt >= cutoff:
            filtered.append(key)
    return filtered


def read_jsonl_gz_from_s3(key: str, settings: Settings | None = None) -> Iterator[dict[str, Any]]:
    settings = settings or get_settings()
    client = get_s3_client(settings)
    resp = client.get_object(Bucket=settings.s3_bucket, Key=key)
    body = resp["Body"].read()
    with gzip.GzipFile(fileobj=io.BytesIO(body), mode="rb") as gz:
        for line in gz:
            line = line.strip()
            if line:
                yield json.loads(line)


def read_json_from_s3(key: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    client = get_s3_client(settings)
    resp = client.get_object(Bucket=settings.s3_bucket, Key=key)
    return json.loads(resp["Body"].read().decode("utf-8"))
