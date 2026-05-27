"""Background execution of the weekly ranking pipeline for the dashboard API."""

from __future__ import annotations

import threading
import traceback
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import structlog

from recommendation_engine.api.pipeline_progress import GRAPH_NODE_LABELS, get_progress_tracker
from recommendation_engine.config.settings import Settings, get_settings
from recommendation_engine.config.validation import ConfigurationError, validate_production_config
from recommendation_engine.graph.workflow import run_weekly_pipeline
from recommendation_engine.io.data_loader import DataLoadError, load_pipeline_inputs
from recommendation_engine.io.embeddings import EmbeddingClient
from recommendation_engine.io.mission_api import mission_to_api, ranked_missions_api_from_store
from recommendation_engine.io.pipeline_cache import (
    get_last_s3_upload_status,
    hydrate_store,
    load_latest_into_store_if_empty,
    sync_latest_cache_to_s3,
    try_load_cached_run,
)
from recommendation_engine.io.store import get_store, reset_store

log = structlog.get_logger()


class PipelineStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PipelineRunState:
    status: PipelineStatus = PipelineStatus.IDLE
    message: str = "Ready"
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    interviews_loaded: int = 0
    community_loaded: int = 0
    trends_loaded: int = 0
    missions_count: int = 0
    from_cache: bool = False
    input_fingerprint: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            base = {
                "status": self.status.value,
                "message": self.message,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "finished_at": self.finished_at.isoformat() if self.finished_at else None,
                "error": self.error,
                "interviews_loaded": self.interviews_loaded,
                "community_loaded": self.community_loaded,
                "trends_loaded": self.trends_loaded,
                "missions_count": self.missions_count,
                "from_cache": self.from_cache,
                "input_fingerprint": self.input_fingerprint,
                "s3_upload": get_last_s3_upload_status(),
            }
            base.update(get_progress_tracker().snapshot())
            return base


_state = PipelineRunState()
_thread: threading.Thread | None = None


def get_pipeline_state() -> PipelineRunState:
    return _state


def _mark_progress_all_complete(*, detail: str) -> None:
    progress = get_progress_tracker()
    for step in progress.steps:
        if step.status.value not in ("completed", "skipped"):
            progress.complete_step(step.id, detail=detail)


def restore_cached_run(snapshot) -> None:
    """Load a cached pipeline snapshot into the store and mark UI progress done."""
    reset_store()
    hydrate_store(snapshot)
    _mark_progress_all_complete(detail="Loaded from cache")


def list_ranked_missions(settings: Settings | None = None) -> list[dict[str, Any]]:
    settings = settings or get_settings()
    load_latest_into_store_if_empty(settings)
    return ranked_missions_api_from_store(get_store(), settings)


def _run_pipeline(settings: Settings) -> None:
    global _state
    progress = get_progress_tracker()
    try:
        progress.begin_step("validate")
        with _state._lock:
            _state.message = "Validating configuration…"
        validate_production_config(settings)
        progress.complete_step("validate")

        progress.begin_step("load")
        with _state._lock:
            _state.message = "Loading interviews, community, and market trends…"
        interviews, community, trends = load_pipeline_inputs(settings)
        with _state._lock:
            _state.interviews_loaded = len(interviews)
            _state.community_loaded = len(community)
            _state.trends_loaded = len(trends)
            _state.message = (
                f"Loaded {len(interviews)} interviews, "
                f"{len(community)} community posts, {len(trends)} trends"
            )
        progress.complete_step(
            "load",
            detail=(
                f"{len(interviews)} interviews · "
                f"{len(community)} community · {len(trends)} trends"
            ),
        )

        embedder = EmbeddingClient(settings)
        missing = [t for t in trends if not t.embedding]
        if missing:
            progress.begin_step("embed")
            with _state._lock:
                _state.message = (
                    f"Embedding {len(missing)} trend signals "
                    f"(batched for API rate limits)…"
                )
            log.info(
                "trend_embed_start",
                count=len(missing),
                batch_size=settings.embedding_batch_size,
                delay_seconds=settings.embedding_request_delay_seconds,
            )
            texts = [f"{t.theme} {t.summary}" for t in missing]
            vectors = embedder.embed(texts)
            for trend, vec in zip(missing, vectors, strict=True):
                trend.embedding = vec
            progress.complete_step("embed", detail=f"{len(missing)} trends embedded")
        else:
            progress.skip_step("embed", detail="All trends already had embeddings")

        progress.begin_step("extract")
        with _state._lock:
            _state.message = "LangGraph: extract → synthesize → cluster → rank → writeup"

        log.info(
            "api_pipeline_start",
            interviews=len(interviews),
            community=len(community),
            trends=len(trends),
        )

        def _on_graph_node(node_id: str) -> None:
            progress.on_graph_node_finished(node_id)
            with _state._lock:
                _state.message = f"Completed: {GRAPH_NODE_LABELS.get(node_id, node_id)}"

        run_weekly_pipeline(
            interviews=interviews,
            community_posts=community,
            trend_signals=trends,
            on_graph_node_finish=_on_graph_node,
        )

        store = get_store()
        mission_count = len(store.ranked_missions)
        with _state._lock:
            _state.missions_count = mission_count
            _state.finished_at = datetime.now(UTC)
            if mission_count == 0:
                _state.status = PipelineStatus.FAILED
                _state.message = "Pipeline finished but produced no ranked missions"
                _state.error = (
                    "Check Gemini quota, S3 interview/community data, and API logs."
                )
            else:
                _state.status = PipelineStatus.COMPLETED
                _state.message = f"Ranking complete — {mission_count} missions"
                _state.error = None
                _state.from_cache = False
                store = get_store()
                _state.input_fingerprint = store.cached_input_fingerprint
    except (ConfigurationError, DataLoadError) as exc:
        progress.fail_at_current(str(exc))
        with _state._lock:
            _state.status = PipelineStatus.FAILED
            _state.finished_at = datetime.now(UTC)
            _state.error = str(exc)
            _state.message = "Pipeline failed"
        log.error("api_pipeline_failed", error=str(exc))
    except Exception as exc:
        progress.fail_at_current(str(exc))
        with _state._lock:
            _state.status = PipelineStatus.FAILED
            _state.finished_at = datetime.now(UTC)
            _state.error = str(exc)
            _state.message = "Pipeline failed"
        log.error("api_pipeline_failed", error=str(exc), trace=traceback.format_exc())
        raise


def _try_serve_from_cache(settings: Settings) -> dict[str, Any] | None:
    """If inputs match a prior run, hydrate store and skip the graph."""
    if settings.pipeline_force_rerun or not settings.pipeline_cache_enabled:
        return None
    validate_production_config(settings)
    interviews, community, trends = load_pipeline_inputs(settings)
    snapshot = try_load_cached_run(interviews, community, trends, settings)
    if not snapshot:
        return None

    restore_cached_run(snapshot)
    sync_latest_cache_to_s3(
        settings,
        ranked_missions_api=ranked_missions_api_from_store(get_store(), settings),
    )
    with _state._lock:
        _state.status = PipelineStatus.COMPLETED
        _state.message = (
            f"Loaded cached analysis ({len(snapshot.ranked_missions)} missions) — "
            "inputs unchanged"
        )
        _state.started_at = datetime.now(UTC)
        _state.finished_at = datetime.now(UTC)
        _state.error = None
        _state.interviews_loaded = snapshot.interviews_count
        _state.community_loaded = snapshot.community_count
        _state.trends_loaded = snapshot.trends_count
        _state.missions_count = len(snapshot.ranked_missions)
        _state.from_cache = True
        _state.input_fingerprint = snapshot.input_fingerprint

    log.info(
        "api_pipeline_cache_served",
        fingerprint=snapshot.input_fingerprint[:12],
        missions=len(snapshot.ranked_missions),
    )
    return {
        "accepted": True,
        "from_cache": True,
        "message": _state.message,
        **_state.snapshot(),
    }


def start_pipeline_run() -> dict[str, Any]:
    """Start the ranking pipeline in a background thread if idle."""
    global _thread, _state

    with _state._lock:
        if _state.status == PipelineStatus.RUNNING:
            return {
                "accepted": False,
                "message": "A ranking run is already in progress",
                **_state.snapshot(),
            }

    settings = get_settings()
    get_progress_tracker().reset()

    try:
        cached_response = _try_serve_from_cache(settings)
        if cached_response:
            return cached_response
    except (ConfigurationError, DataLoadError) as exc:
        return {
            "accepted": False,
            "message": str(exc),
            **_state.snapshot(),
        }

    reset_store()

    with _state._lock:
        _state.status = PipelineStatus.RUNNING
        _state.message = "Starting ranking pipeline…"
        _state.started_at = datetime.now(UTC)
        _state.finished_at = None
        _state.error = None
        _state.interviews_loaded = 0
        _state.community_loaded = 0
        _state.trends_loaded = 0
        _state.missions_count = 0
        _state.from_cache = False
        _state.input_fingerprint = None

    def _target() -> None:
        try:
            _run_pipeline(settings)
        except Exception:
            pass

    _thread = threading.Thread(target=_target, name="eg-pipeline-run", daemon=True)
    _thread.start()

    return {"accepted": True, "from_cache": False, "message": "Ranking pipeline started", **_state.snapshot()}
