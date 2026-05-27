"""Build TrendSignal rows from market-trends bronze JSONL records."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any

from recommendation_engine.models.schemas import MarketBronzeRecord, Momentum, TrendSignal


def _slug(value: str, max_len: int = 80) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug[:max_len] or "unknown"


def _text_from_raw(raw: dict[str, Any]) -> tuple[str, str]:
    title = (
        raw.get("title")
        or raw.get("name")
        or raw.get("competitionName")
        or raw.get("dataset")
        or ""
    )
    summary = (
        raw.get("summary")
        or raw.get("description")
        or raw.get("tagline")
        or raw.get("subtitle")
        or ""
    )
    if isinstance(summary, dict):
        summary = str(summary)
    return str(title).strip(), str(summary).strip()[:2000]


def bronze_record_to_trend(record: dict[str, Any]) -> TrendSignal | None:
    """Map one bronze envelope to a lightweight trend signal (pre-gold enrichment)."""
    try:
        env = MarketBronzeRecord.model_validate(record)
    except Exception:
        return None

    title, summary = _text_from_raw(env.raw)
    if not title and not summary:
        return None

    theme = title or f"{env.source_id} signal"
    body = summary or title
    full_summary = f"[{env.category}/{env.source_id}] {body}"

    trend_id = hashlib.sha256(f"{env.source_id}:{env.external_id}".encode()).hexdigest()[:16]
    trend_id = f"trend-{_slug(env.source_id, 40)}-{trend_id}"

    urls: list[str] = []
    if env.source_url:
        urls.append(env.source_url)

    return TrendSignal(
        trend_id=trend_id,
        theme=theme,
        summary=full_summary,
        evidence_urls=urls,
        source_count=1,
        momentum=Momentum.STABLE,
        novelty="emerging",
        first_seen=env.source_published_at or env.ingested_at,
        last_updated=env.ingested_at,
    )
