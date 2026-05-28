"""Shared pytest fixtures — moto S3 + connector deps."""

from __future__ import annotations

from typing import Any

import boto3
import pytest
from moto import mock_aws

from ingestion.io.s3_writer import S3Writer
from ingestion.io.state_store import StateStore
from ingestion.runtime.rate_limiter import RateLimiterRegistry


@pytest.fixture
def aws_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def s3_setup(aws_credentials: None) -> dict[str, Any]:
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="eg-lakehouse")
        writer = S3Writer(client, "eg-lakehouse")
        state = StateStore(client, "eg-lakehouse")
        limiters = RateLimiterRegistry()
        yield {"client": client, "writer": writer, "state": state, "limiters": limiters}


@pytest.fixture
def sample_rss_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>TechCrunch AI</title>
    <item>
      <title>Test AI Article</title>
      <link>https://techcrunch.com/2026/05/19/test-ai-article/</link>
      <guid>https://techcrunch.com/?p=12345</guid>
      <pubDate>Mon, 19 May 2026 14:32:00 +0000</pubDate>
      <description>Sample description</description>
    </item>
  </channel>
</rss>"""


@pytest.fixture
def pluralsight_rss_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Pluralsight Blog</title>
    <item>
      <title>New AI Learning Path</title>
      <link>https://www.pluralsight.com/blog/ai-learning-path</link>
      <guid>ps-blog-999</guid>
      <pubDate>Tue, 18 May 2026 10:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>"""
