"""Load pipeline inputs: S3 for interviews & trends; community optional mock."""

from __future__ import annotations

import structlog

from recommendation_engine.config.settings import Settings, get_settings
from recommendation_engine.io import bronze_loader, s3_loader
from recommendation_engine.models.schemas import CommunityBronze, InterviewBronze, TrendSignal

log = structlog.get_logger()


class DataLoadError(Exception):
    pass


def _load_community(settings: Settings) -> list[CommunityBronze]:
    if settings.use_mock_community:
        posts = bronze_loader.load_community(settings=settings)
        log.info("community_loaded", mode="fixtures", count=len(posts))
        return posts
    posts = s3_loader.load_community_from_s3(settings)
    log.info("community_loaded", mode="s3", count=len(posts))
    return posts


def load_pipeline_inputs(
    settings: Settings | None = None,
    *,
    use_fixtures: bool = False,
) -> tuple[list[InterviewBronze], list[CommunityBronze], list[TrendSignal]]:
    settings = settings or get_settings()

    if use_fixtures:
        if not settings.allow_fixtures:
            raise DataLoadError(
                "Fixture data is disabled. Set EG_ALLOW_FIXTURES=1 for local test runs only."
            )
        log.info("data_source", mode="fixtures", allow_fixtures=True)
        return (
            bronze_loader.load_interviews(settings=settings),
            bronze_loader.load_community(settings=settings),
            bronze_loader.load_trend_signals(settings=settings),
        )

    if not settings.use_s3:
        raise DataLoadError("EG_DATA_SOURCE must be 's3' for production runs.")

    log.info(
        "data_source",
        mode="s3",
        bucket=settings.s3_bucket,
        profile=settings.aws_profile,
        lookback_days=settings.lookback_days,
        enrich_bronze_trends=settings.enrich_bronze_trends,
        community_source=settings.community_source,
    )
    interviews = s3_loader.load_interviews_from_s3(settings)
    community = _load_community(settings)
    trends = s3_loader.load_market_trends_from_s3(settings)

    if not trends:
        raise DataLoadError(
            f"No market trends in s3://{settings.s3_bucket}/ "
            f"(check gold/{settings.s3_gold_trend_prefix} or bronze builder/news/learning). "
            "Run Market_trends ingestion first."
        )

    user_sources = len(interviews) + len(community)
    if user_sources == 0:
        msg = (
            "No interviews on S3 and no community posts loaded "
            f"(community_source={settings.community_source})."
        )
        if settings.require_user_signals:
            raise DataLoadError(msg)
        log.warning("no_user_signals", detail=msg)

    return interviews, community, trends
