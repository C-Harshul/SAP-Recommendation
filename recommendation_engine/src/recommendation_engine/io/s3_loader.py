"""Load interviews, community, and market trends from S3."""

from __future__ import annotations

import json
from datetime import datetime
import structlog

from recommendation_engine.config.settings import Settings, get_settings
from recommendation_engine.io.s3_reader import (
    filter_keys_by_lookback,
    list_keys,
    read_json_from_s3,
    read_jsonl_gz_from_s3,
)
from recommendation_engine.io.interview_parser import parse_interview_document
from recommendation_engine.io.trend_builder import bronze_record_to_trend
from recommendation_engine.models.schemas import CommunityBronze, InterviewBronze, TrendSignal

log = structlog.get_logger()

MARKET_CATEGORIES = ("builder", "news", "learning")
GOLD_TREND_PREFIX = "gold/trend_signals"


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def load_gold_trend_signals(settings: Settings | None = None) -> list[TrendSignal]:
    """Load pre-enriched gold.trend_signals JSON objects if present on S3."""
    settings = settings or get_settings()
    prefix = settings.s3_gold_trend_prefix.strip("/")
    keys = list_keys(f"{prefix}/", suffix=".json", under_bronze=False, settings=settings)
    signals: list[TrendSignal] = []
    for key in keys:
        try:
            data = read_json_from_s3(key, settings)
            signals.append(
                TrendSignal(
                    trend_id=data["trend_id"],
                    theme=data["theme"],
                    summary=data["summary"],
                    evidence_urls=data.get("evidence_urls", []),
                    source_count=data.get("source_count", 1),
                    momentum=data.get("momentum", "stable"),
                    novelty=data.get("novelty", "emerging"),
                    first_seen=_parse_dt(data.get("first_seen")),
                    peak_week=data.get("peak_week"),
                    last_updated=_parse_dt(data.get("last_updated")),
                )
            )
        except Exception as exc:
            log.warning("gold_trend_skip", key=key, error=str(exc))
    return signals


def load_market_trends_from_s3(settings: Settings | None = None) -> list[TrendSignal]:
    """
    Load market trend signals from S3.

    Priority:
    1. gold/trend_signals/*.json if any exist
    2. Else bronze JSONL under builder/, news/, learning/
    """
    settings = settings or get_settings()
    gold = load_gold_trend_signals(settings)
    if gold:
        log.info("trends_loaded", source="gold", count=len(gold))
        return gold[: settings.max_market_records]

    keys: list[str] = []
    for category in MARKET_CATEGORIES:
        cat_keys = list_keys(f"{category}/", suffix=".jsonl.gz", settings=settings)
        keys.extend(cat_keys)
    keys = filter_keys_by_lookback(keys, settings.lookback_days)
    keys = sorted(keys, reverse=True)

    signals: list[TrendSignal] = []
    seen_ids: set[str] = set()

    for key in keys:
        if len(signals) >= settings.max_market_records:
            break
        try:
            for record in read_jsonl_gz_from_s3(key, settings):
                trend = bronze_record_to_trend(record)
                if trend and trend.trend_id not in seen_ids:
                    seen_ids.add(trend.trend_id)
                    signals.append(trend)
                if len(signals) >= settings.max_market_records:
                    break
        except Exception as exc:
            log.warning("bronze_file_skip", key=key, error=str(exc))

    log.info(
        "trends_loaded",
        source="bronze",
        files_scanned=min(len(keys), 500),
        count=len(signals),
    )

    if signals and settings.enrich_bronze_trends:
        from recommendation_engine.io.trend_enrichment import enrich_trends_with_llm

        try:
            signals = enrich_trends_with_llm(signals, settings=settings)
            log.info("trends_enriched_via_llm", count=len(signals))
        except Exception as exc:
            log.warning(
                "trends_enrichment_failed_using_bronze",
                error=str(exc),
                count=len(signals),
                hint="Set EG_ENRICH_BRONZE_TRENDS=0 to skip LLM enrichment, or retry later",
            )

    return signals


def _load_json_documents(prefix: str, settings: Settings) -> list[dict]:
    keys = list_keys(prefix, suffix=".json", settings=settings)
    keys = filter_keys_by_lookback(keys, settings.lookback_days)
    docs: list[dict] = []
    for key in keys:
        try:
            docs.append(read_json_from_s3(key, settings))
        except Exception as exc:
            log.warning("json_doc_skip", key=key, error=str(exc))
    return docs


def load_interviews_from_s3(settings: Settings | None = None) -> list[InterviewBronze]:
    settings = settings or get_settings()
    keys = list_keys("interviews/", suffix=".json", settings=settings)
    keys = filter_keys_by_lookback(keys, settings.lookback_days)
    interviews: list[InterviewBronze] = []
    for key in keys:
        try:
            item = read_json_from_s3(key, settings)
            parsed = parse_interview_document(item, key)
            if parsed:
                interviews.append(parsed)
            else:
                log.warning("interview_parse_skip", key=key, reason="unrecognized schema")
        except Exception as exc:
            log.warning("interview_skip", key=key, error=str(exc))
    log.info("interviews_loaded", count=len(interviews))
    return interviews


def load_community_from_s3(settings: Settings | None = None) -> list[CommunityBronze]:
    settings = settings or get_settings()
    docs = _load_json_documents("community/", settings)
    posts: list[CommunityBronze] = []
    for item in docs:
        posts.append(
            CommunityBronze(
                post_id=item["post_id"],
                author_role=item.get("author_role", "unknown"),
                timestamp=_parse_dt(item.get("timestamp")) or datetime.now(),
                body=item.get("body", ""),
                upvote_count=int(item.get("upvote_count", 0)),
                tags=item.get("tags", []),
            )
        )
    log.info("community_loaded", count=len(posts))
    return posts


def describe_s3_inventory(settings: Settings | None = None) -> dict[str, int | list[str]]:
    """Summarize what is available in the bucket (for CLI discovery)."""
    settings = settings or get_settings()
    summary: dict[str, int | list[str]] = {"bucket": settings.s3_bucket}

    gold_prefix = f"{settings.s3_gold_trend_prefix.strip('/')}/"
    gold_keys = list_keys(gold_prefix, suffix=".json", under_bronze=False, settings=settings)
    summary["gold_trend_signals_json_count"] = len(gold_keys)
    summary["gold_trend_signals_sample_keys"] = gold_keys[:5]

    for label, prefix in [
        ("interviews", "interviews/"),
        ("community", "community/"),
    ]:
        keys = list_keys(prefix, suffix=".json", settings=settings)
        summary[f"{label}_json_count"] = len(keys)
        summary[f"{label}_sample_keys"] = keys[:5]

    market_count = 0
    sample: list[str] = []
    for category in MARKET_CATEGORIES:
        keys = filter_keys_by_lookback(
            list_keys(f"{category}/", suffix=".jsonl.gz", settings=settings),
            settings.lookback_days,
        )
        market_count += len(keys)
        sample.extend(keys[:2])
    summary["market_bronze_file_count"] = market_count
    summary["market_bronze_sample_keys"] = sample[:8]
    return summary
