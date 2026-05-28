"""RSS generic connector — covers news and learning RSS sources."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ingestion.connectors.news.rss_generic import RssGenericConnector
from ingestion.models.envelope import RecordEnvelope

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def techcrunch_connector(s3_setup: dict) -> RssGenericConnector:
    conn = RssGenericConnector(
        writer=s3_setup["writer"],
        state=s3_setup["state"],
        rate_limiters=s3_setup["limiters"],
        source_config={
            "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
            "keyword_filter": None,
        },
    )
    conn.source_id = "techcrunch_ai"
    conn.category = "news"
    return conn


def test_fetch_parses_feed(techcrunch_connector: RssGenericConnector) -> None:
    xml = (FIXTURES / "techcrunch_feed.xml").read_text()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = xml
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
        items = list(techcrunch_connector.fetch(since=None))

    assert len(items) == 1
    assert items[0]["external_id"] == "https://techcrunch.com/?p=12345"
    assert "Test AI Article" in items[0]["raw"]["title"]


def test_run_writes_bronze(techcrunch_connector: RssGenericConnector, s3_setup: dict) -> None:
    xml = (FIXTURES / "techcrunch_feed.xml").read_text()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = xml
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
        result = techcrunch_connector.run()

    assert result.records_ingested == 1
    assert result.bronze_path is not None
    assert "news/techcrunch_ai" in result.bronze_path

    cursor = s3_setup["state"].load("techcrunch_ai")
    assert "https://techcrunch.com/?p=12345" in cursor.last_external_ids


@pytest.fixture
def pluralsight_connector(s3_setup: dict) -> RssGenericConnector:
    conn = RssGenericConnector(
        writer=s3_setup["writer"],
        state=s3_setup["state"],
        rate_limiters=s3_setup["limiters"],
        source_config={
            "url": "https://www.pluralsight.com/blog/rss.xml",
            "keyword_filter": None,
        },
    )
    conn.source_id = "pluralsight_blog"
    conn.category = "learning"
    return conn


def test_pluralsight_learning_category(pluralsight_connector: RssGenericConnector) -> None:
    xml = (FIXTURES / "pluralsight_feed.xml").read_text()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = xml
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
        result = pluralsight_connector.run()

    assert result.category == "learning"
    assert result.records_ingested == 1
    assert "learning/pluralsight_blog" in (result.bronze_path or "")


def test_envelope_shape() -> None:
    from datetime import UTC, datetime

    env = RecordEnvelope(
        source_id="techcrunch_ai",
        category="news",
        ingested_at=datetime.now(UTC),
        external_id="abc",
        raw={"title": "x"},
    )
    d = env.to_json_dict()
    assert d["source_id"] == "techcrunch_ai"
    assert d["raw"]["title"] == "x"
