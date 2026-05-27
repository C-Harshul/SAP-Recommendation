"""Write pipeline outputs to S3 (same bucket as inputs)."""

from __future__ import annotations

import json
from typing import Any

import structlog
from botocore.exceptions import ClientError

from recommendation_engine.config.settings import Settings, get_settings
from recommendation_engine.io.s3_reader import get_s3_client

log = structlog.get_logger()


def pipeline_results_prefix(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    return settings.s3_pipeline_results_prefix.strip("/")


def run_snapshot_key(fingerprint: str, settings: Settings | None = None) -> str:
    prefix = pipeline_results_prefix(settings)
    return f"{prefix}/runs/{fingerprint}.json"


def latest_pointer_key(settings: Settings | None = None) -> str:
    prefix = pipeline_results_prefix(settings)
    return f"{prefix}/latest_run.json"


def latest_ranked_missions_key(settings: Settings | None = None) -> str:
    prefix = pipeline_results_prefix(settings)
    return f"{prefix}/latest_ranked_missions.json"


def put_json_object(
    key: str,
    payload: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> str:
    """Upload JSON object; returns s3:// URI."""
    settings = settings or get_settings()
    body = json.dumps(payload, indent=2, default=str)
    return put_text_object(key, body, content_type="application/json", settings=settings)


def put_text_object(
    key: str,
    body: str,
    *,
    content_type: str = "application/json",
    settings: Settings | None = None,
) -> str:
    settings = settings or get_settings()
    client = get_s3_client(settings)
    client.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=body.encode("utf-8"),
        ContentType=content_type,
    )
    uri = f"s3://{settings.s3_bucket}/{key}"
    log.info("s3_put_object", bucket=settings.s3_bucket, key=key)
    return uri


def get_json_object(key: str, settings: Settings | None = None) -> dict[str, Any] | None:
    settings = settings or get_settings()
    client = get_s3_client(settings)
    try:
        resp = client.get_object(Bucket=settings.s3_bucket, Key=key)
        return json.loads(resp["Body"].read().decode("utf-8"))
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
            return None
        log.warning("s3_get_object_failed", key=key, error=str(exc))
        return None
    except Exception as exc:
        log.warning("s3_get_object_failed", key=key, error=str(exc))
        return None
