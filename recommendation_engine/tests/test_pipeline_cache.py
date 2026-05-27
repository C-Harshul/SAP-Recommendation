from datetime import UTC, datetime

from recommendation_engine.config.settings import Settings
from recommendation_engine.io.fingerprints import input_fingerprint, interview_content_hash
from recommendation_engine.io.pipeline_cache import (
    hydrate_store,
    load_snapshot_by_fingerprint,
    save_snapshot,
    try_load_cached_run,
)
from recommendation_engine.io.store import get_store, reset_store
from recommendation_engine.models.pipeline_snapshot import PipelineSnapshot
from recommendation_engine.models.schemas import InterviewBronze, RankedMission


def test_fingerprint_stable_for_same_interview():
    i = InterviewBronze(
        interview_id="int-1",
        participant_role="PM",
        timestamp=datetime.now(UTC),
        transcript="Same text",
    )
    assert interview_content_hash(i) == interview_content_hash(i)


def test_save_and_load_pipeline_cache(tmp_path):
    settings = Settings(
        EG_PIPELINE_CACHE_DIR=str(tmp_path),
        EG_PIPELINE_CACHE=1,
    )
    reset_store()
    fp = "abc123" * 10
    snap = PipelineSnapshot(
        input_fingerprint=fp,
        config_fingerprint="cfg",
        created_at=datetime.now(UTC),
        prompt_version="v1",
        weights_version="v1",
        git_sha="dev",
        ranked_missions=[
            RankedMission(
                mission_id="m1",
                cluster_id="c1",
                rank=1,
                source_count=0.5,
                source_diversity=0.5,
                recency=1.0,
                specificity=0.5,
                signal_urgency=0.5,
                market_validation=0.5,
                feasibility=0.5,
                sap_relevance=0.5,
                novelty=0.5,
                effort_score=0.5,
                impact_score=0.5,
                final_score=0.8,
                weights_version="v1",
            )
        ],
    )
    save_snapshot(snap, settings)
    loaded = load_snapshot_by_fingerprint(fp, settings)
    assert loaded is not None
    assert len(loaded.ranked_missions) == 1
    hydrate_store(loaded)
    assert len(get_store().ranked_missions) == 1


def test_try_load_cached_run_miss(tmp_path):
    settings = Settings(EG_PIPELINE_CACHE_DIR=str(tmp_path), EG_PIPELINE_CACHE=1)
    result = try_load_cached_run([], [], [], settings)
    assert result is None
