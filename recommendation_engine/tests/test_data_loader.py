"""Hybrid data loading: fixture community."""

from __future__ import annotations

from pathlib import Path

from recommendation_engine.config.settings import Settings
from recommendation_engine.io.data_loader import _load_community


def test_mock_community_from_fixtures():
    fixtures_dir = Path(__file__).resolve().parents[1] / "src" / "recommendation_engine" / "fixtures"
    settings = Settings(
        community_source="fixtures",
        fixtures_dir=fixtures_dir,
    )
    community = _load_community(settings)
    assert len(community) == 4
    assert community[0].post_id == "post-101"
