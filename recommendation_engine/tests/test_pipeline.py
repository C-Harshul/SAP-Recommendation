"""End-to-end pipeline test (fixture data + patched APIs)."""

from __future__ import annotations

from recommendation_engine.config.validation import validate_production_config
from recommendation_engine.graph.workflow import run_weekly_pipeline
from recommendation_engine.io.data_loader import load_pipeline_inputs
from recommendation_engine.io.embeddings import EmbeddingClient
from recommendation_engine.io.store import reset_store


def test_validate_production_rejects_fixtures(test_settings):
    import pytest

    with pytest.raises(Exception):
        validate_production_config(test_settings)


def test_weekly_pipeline_e2e(test_settings):
    reset_store()
    interviews, community, trends = load_pipeline_inputs(test_settings, use_fixtures=True)
    embedder = EmbeddingClient(test_settings)
    for t in trends:
        t.embedding = embedder.embed_query(f"{t.theme} {t.summary}")

    result = run_weekly_pipeline(
        interviews=interviews,
        community_posts=community,
        trend_signals=trends,
    )

    missions = result.get("missions_with_writeups") or result.get("ranked_missions", [])
    assert len(missions) >= 1
    top = missions[0]
    assert top.final_score > 0
    assert top.rank == 1

    top_with_writeup = next((m for m in missions if m.writeup), None)
    assert top_with_writeup is not None
    assert "## The Mission" in (top_with_writeup.writeup or "")


def test_programmatic_scoring():
    import pytest

    from recommendation_engine.scoring.programmatic import (
        effort_score,
        final_weighted_score,
        impact_score,
        load_weights,
    )

    weights = load_weights()
    sub = {
        "source_count": 0.8,
        "signal_urgency": 0.7,
        "market_validation": 0.6,
        "sap_relevance": 0.9,
        "source_diversity": 0.5,
        "feasibility": 0.65,
        "recency": 0.9,
        "specificity": 0.75,
        "novelty": 0.55,
    }
    final = final_weighted_score(sub, weights)
    assert 0 < final <= 1
    assert effort_score(0.65) == pytest.approx(0.35, abs=0.01)
    assert impact_score(
        source_count=0.8,
        signal_urgency=0.7,
        market_validation=0.6,
        sap_relevance=0.9,
        novelty=0.55,
    ) > 0
