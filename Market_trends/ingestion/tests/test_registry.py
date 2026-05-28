"""Source registry loads all configured sources."""

from __future__ import annotations

from ingestion.connectors.registry import load_sources_yaml


def test_sources_yaml_loads() -> None:
    sources = load_sources_yaml()
    ids = {s["id"] for s in sources}
    assert "techcrunch_ai" in ids
    assert "kaggle" in ids
    assert "pluralsight_blog" in ids
    assert len(sources) >= 30
