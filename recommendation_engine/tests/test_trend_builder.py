from recommendation_engine.io.trend_builder import bronze_record_to_trend


def test_bronze_record_to_trend():
    record = {
        "source_id": "techcrunch_ai",
        "category": "news",
        "ingested_at": "2026-05-20T10:00:00Z",
        "source_published_at": "2026-05-19T14:00:00Z",
        "source_url": "https://example.com/article",
        "external_id": "abc123",
        "raw": {"title": "AI agents reshape enterprise", "summary": "Teams adopt tool-use RAG."},
    }
    trend = bronze_record_to_trend(record)
    assert trend is not None
    assert trend.theme == "AI agents reshape enterprise"
    assert trend.evidence_urls == ["https://example.com/article"]
