"""Disk-backed pipeline run cache keyed by input + config fingerprints."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
from botocore.exceptions import ClientError

from recommendation_engine.config.settings import Settings, get_settings
from recommendation_engine.io.fingerprints import config_fingerprint, input_fingerprint
from recommendation_engine.io.s3_writer import (
    get_json_object,
    latest_pointer_key,
    latest_ranked_missions_key,
    put_json_object,
    put_text_object,
    run_snapshot_key,
)
from recommendation_engine.io.store import get_store
from recommendation_engine.models.pipeline_snapshot import PipelineSnapshot
from recommendation_engine.models.schemas import (
    CommunityBronze,
    InterviewBronze,
    TrendSignal,
)
from recommendation_engine.models.state import RecommendationState

log = structlog.get_logger()

LATEST_POINTER = "latest_run.json"
_LEGACY_S3_PREFIX = "gold/pipeline_runs"

_last_s3_upload: dict[str, Any] = {"ok": None, "error": None, "keys": []}


def get_last_s3_upload_status() -> dict[str, Any]:
    return dict(_last_s3_upload)


def cache_root(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    root = settings.pipeline_cache_dir
    root.mkdir(parents=True, exist_ok=True)
    (root / "runs").mkdir(exist_ok=True)
    (root / "sources").mkdir(exist_ok=True)
    return root


def _run_path(fingerprint: str, settings: Settings | None = None) -> Path:
    return cache_root(settings) / "runs" / f"{fingerprint}.json"


def snapshot_from_state(
    state: RecommendationState,
    *,
    input_fp: str,
    config_fp: str,
    settings: Settings,
    interviews_count: int,
    community_count: int,
    trends_count: int,
) -> PipelineSnapshot:
    clusters = state.get("clusters_with_trends") or state.get("idea_clusters", [])
    missions = state.get("missions_with_writeups") or state.get("ranked_missions", [])
    return PipelineSnapshot(
        input_fingerprint=input_fp,
        config_fingerprint=config_fp,
        created_at=datetime.now(UTC),
        prompt_version=settings.prompt_version,
        weights_version=settings.weights_version,
        git_sha=settings.git_sha,
        interviews_count=interviews_count,
        community_count=community_count,
        trends_count=trends_count,
        trend_signals=list(state.get("trend_signals", [])),
        extracted_ideas=list(state.get("extracted_ideas", [])),
        extracted_problems=list(state.get("extracted_problems", [])),
        candidate_solutions=list(state.get("candidate_solutions", [])),
        idea_clusters=list(clusters),
        ranked_missions=list(missions),
    )


def hydrate_store(snapshot: PipelineSnapshot) -> None:
    store = get_store()
    store.trend_signals = snapshot.trend_signals
    store.extracted_ideas = list(snapshot.extracted_ideas) + list(snapshot.extracted_problems)
    store.candidate_solutions = snapshot.candidate_solutions
    store.idea_clusters = snapshot.idea_clusters
    store.ranked_missions = snapshot.ranked_missions
    store.last_persisted_at = snapshot.created_at
    store.cached_input_fingerprint = snapshot.input_fingerprint
    store.cached_at = snapshot.created_at


def _should_upload_s3(settings: Settings) -> bool:
    return (
        settings.pipeline_results_s3_enabled
        and settings.use_s3
        and bool(settings.s3_bucket)
    )


def _s3_prefixes_to_try(settings: Settings) -> list[str]:
    configured = settings.s3_pipeline_results_prefix.strip("/")
    prefixes = [configured]
    legacy = _LEGACY_S3_PREFIX.strip("/")
    if legacy not in prefixes:
        prefixes.append(legacy)
    return prefixes


def _run_snapshot_key_for_prefix(fingerprint: str, prefix: str) -> str:
    return f"{prefix.strip('/')}/runs/{fingerprint}.json"


def _latest_pointer_key_for_prefix(prefix: str) -> str:
    return f"{prefix.strip('/')}/latest_run.json"


def _latest_ranked_key_for_prefix(prefix: str) -> str:
    return f"{prefix.strip('/')}/latest_ranked_missions.json"


def _upload_snapshot_to_s3(
    snapshot: PipelineSnapshot,
    *,
    settings: Settings,
    ranked_missions_api: list[dict] | None = None,
) -> bool:
    global _last_s3_upload
    if not _should_upload_s3(settings):
        _last_s3_upload = {"ok": False, "error": "S3 upload disabled", "keys": []}
        return False

    body = snapshot.model_dump_json(indent=2)
    pointer_payload = {
        "input_fingerprint": snapshot.input_fingerprint,
        "created_at": snapshot.created_at.isoformat(),
        "missions_count": len(snapshot.ranked_missions),
    }
    missions_payload = None
    if ranked_missions_api is not None:
        missions_payload = {
            "created_at": snapshot.created_at.isoformat(),
            "input_fingerprint": snapshot.input_fingerprint,
            "count": len(ranked_missions_api),
            "missions": ranked_missions_api,
        }

    last_error: str | None = None
    for prefix in _s3_prefixes_to_try(settings):
        try:
            snap_key = _run_snapshot_key_for_prefix(snapshot.input_fingerprint, prefix)
            put_text_object(snap_key, body, settings=settings)
            pointer_payload["s3_snapshot_key"] = snap_key
            put_json_object(
                _latest_pointer_key_for_prefix(prefix), pointer_payload, settings=settings
            )
            keys = [snap_key]
            if missions_payload:
                missions_key = _latest_ranked_key_for_prefix(prefix)
                put_json_object(missions_key, missions_payload, settings=settings)
                keys.append(missions_key)
            _last_s3_upload = {
                "ok": True,
                "error": None,
                "keys": keys,
                "bucket": settings.s3_bucket,
                "prefix": prefix,
            }
            log.info(
                "pipeline_cache_s3_saved",
                bucket=settings.s3_bucket,
                prefix=prefix,
                keys=keys,
                fingerprint=snapshot.input_fingerprint[:12],
            )
            return True
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            last_error = f"{prefix}: {code} — {exc}"
            log.warning("pipeline_cache_s3_prefix_failed", prefix=prefix, error=str(exc))
        except Exception as exc:
            last_error = f"{prefix}: {exc}"
            log.warning("pipeline_cache_s3_prefix_failed", prefix=prefix, error=str(exc))

    _last_s3_upload = {"ok": False, "error": last_error, "keys": []}
    log.error("pipeline_cache_s3_failed", error=last_error)
    return False


def _load_snapshot_from_s3(fingerprint: str, settings: Settings) -> PipelineSnapshot | None:
    if not _should_upload_s3(settings):
        return None
    for prefix in _s3_prefixes_to_try(settings):
        try:
            key = _run_snapshot_key_for_prefix(fingerprint, prefix)
            raw = get_json_object(key, settings)
            if raw:
                return PipelineSnapshot.model_validate(raw)
        except Exception as exc:
            log.warning(
                "pipeline_cache_s3_load_failed",
                prefix=prefix,
                fingerprint=fingerprint[:12],
                error=str(exc),
            )
    return None


def save_snapshot(
    snapshot: PipelineSnapshot,
    settings: Settings | None = None,
    *,
    ranked_missions_api: list[dict] | None = None,
) -> Path:
    settings = settings or get_settings()
    path = _run_path(snapshot.input_fingerprint, settings)
    path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
    pointer = cache_root(settings) / LATEST_POINTER
    pointer.write_text(
        json.dumps(
            {
                "input_fingerprint": snapshot.input_fingerprint,
                "created_at": snapshot.created_at.isoformat(),
                "missions_count": len(snapshot.ranked_missions),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _upload_snapshot_to_s3(
        snapshot, settings=settings, ranked_missions_api=ranked_missions_api
    )
    log.info(
        "pipeline_cache_saved",
        path=str(path),
        fingerprint=snapshot.input_fingerprint[:12],
        missions=len(snapshot.ranked_missions),
        s3=_last_s3_upload.get("ok"),
    )
    return path


def sync_latest_cache_to_s3(
    settings: Settings | None = None,
    *,
    ranked_missions_api: list[dict] | None = None,
) -> dict[str, Any]:
    """Upload the latest on-disk cache to S3 (for backfill after failed PutObject)."""
    settings = settings or get_settings()
    pointer = cache_root(settings) / LATEST_POINTER
    if not pointer.is_file():
        return {"ok": False, "error": "No local cache (latest_run.json missing)"}
    meta = json.loads(pointer.read_text(encoding="utf-8"))
    fp = meta["input_fingerprint"]
    snap = load_snapshot_by_fingerprint(fp, settings)
    if not snap:
        return {"ok": False, "error": f"No snapshot for fingerprint {fp[:12]}"}
    ok = _upload_snapshot_to_s3(
        snap, settings=settings, ranked_missions_api=ranked_missions_api
    )
    return get_last_s3_upload_status() | {"ok": ok}


def load_snapshot_by_fingerprint(
    fingerprint: str, settings: Settings | None = None
) -> PipelineSnapshot | None:
    settings = settings or get_settings()
    path = _run_path(fingerprint, settings)
    if path.is_file():
        try:
            return PipelineSnapshot.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning("pipeline_cache_load_failed", path=str(path), error=str(exc))
    return _load_snapshot_from_s3(fingerprint, settings)


def _latest_fingerprint_local(settings: Settings) -> str | None:
    pointer = cache_root(settings) / LATEST_POINTER
    if not pointer.is_file():
        return None
    try:
        meta = json.loads(pointer.read_text(encoding="utf-8"))
        return meta["input_fingerprint"]
    except (json.JSONDecodeError, KeyError):
        return None


def _latest_fingerprint_s3(settings: Settings) -> str | None:
    if not _should_upload_s3(settings):
        return None
    for prefix in _s3_prefixes_to_try(settings):
        meta = get_json_object(_latest_pointer_key_for_prefix(prefix), settings)
        if meta:
            return meta.get("input_fingerprint")
    return None


def _latest_fingerprint(settings: Settings) -> str | None:
    return _latest_fingerprint_local(settings) or _latest_fingerprint_s3(settings)


def load_latest_snapshot(settings: Settings | None = None) -> PipelineSnapshot | None:
    settings = settings or get_settings()
    fp = _latest_fingerprint(settings)
    if not fp:
        return None
    return load_snapshot_by_fingerprint(fp, settings)


def try_load_cached_run(
    interviews: list[InterviewBronze],
    community: list[CommunityBronze],
    trends: list[TrendSignal],
    settings: Settings | None = None,
) -> PipelineSnapshot | None:
    settings = settings or get_settings()
    if not settings.pipeline_cache_enabled:
        return None
    fp = input_fingerprint(interviews, community, trends, settings)
    snap = load_snapshot_by_fingerprint(fp, settings)
    if snap and snap.ranked_missions:
        log.info(
            "pipeline_cache_hit",
            fingerprint=fp[:12],
            missions=len(snap.ranked_missions),
            created_at=snap.created_at.isoformat(),
        )
        return snap
    return None


def build_fingerprints(
    interviews: list[InterviewBronze],
    community: list[CommunityBronze],
    trends: list[TrendSignal],
    settings: Settings | None = None,
) -> tuple[str, str]:
    settings = settings or get_settings()
    return input_fingerprint(interviews, community, trends, settings), config_fingerprint(
        settings
    )


def load_latest_into_store_if_empty(settings: Settings | None = None) -> bool:
    """On API startup, restore last successful run into memory."""
    settings = settings or get_settings()
    store = get_store()
    if store.ranked_missions:
        return False
    snap = load_latest_snapshot(settings)
    if not snap or not snap.ranked_missions:
        return False
    hydrate_store(snap)
    log.info("pipeline_cache_restored_latest", missions=len(snap.ranked_missions))
    return True
