"""Persist silver/gold outputs and emit audit metadata."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog

from recommendation_engine.config.settings import get_settings
from recommendation_engine.io.mission_api import ranked_missions_api_from_store
from recommendation_engine.io.pipeline_cache import (
    build_fingerprints,
    save_snapshot,
    snapshot_from_state,
)
from recommendation_engine.io.store import get_store
from recommendation_engine.models.state import RecommendationState

log = structlog.get_logger()


def persist_node(state: RecommendationState) -> dict:
    settings = get_settings()
    store = get_store()

    ideas = list(state.get("extracted_ideas", [])) + list(state.get("extracted_problems", []))
    solutions = state.get("candidate_solutions", [])
    clusters = state.get("clusters_with_trends") or state.get("idea_clusters", [])
    missions = state.get("missions_with_writeups") or state.get("ranked_missions", [])

    store.trend_signals = state.get("trend_signals", [])
    store.persist_run(ideas, solutions, clusters, missions)

    interviews = state.get("interviews", [])
    community = state.get("community_posts", [])
    trends = state.get("trend_signals", [])
    input_fp, config_fp = build_fingerprints(interviews, community, trends, settings)
    store.cached_input_fingerprint = input_fp
    store.cached_at = datetime.now(UTC)

    if settings.pipeline_cache_enabled and missions:
        snap = snapshot_from_state(
            state,
            input_fp=input_fp,
            config_fp=config_fp,
            settings=settings,
            interviews_count=len(interviews),
            community_count=len(community),
            trends_count=len(trends),
        )
        save_snapshot(
            snap,
            settings,
            ranked_missions_api=ranked_missions_api_from_store(store, settings),
        )

    log.info(
        "persist_complete",
        ideas=len(ideas),
        solutions=len(solutions),
        clusters=len(clusters),
        missions=len(missions),
        git_sha=settings.git_sha,
        weights_version=settings.weights_version,
        input_fingerprint=input_fp[:12],
        at=datetime.now(UTC).isoformat(),
    )
    return {}
