"""Load bronze/fixture data for interviews, community, and trend signals."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from recommendation_engine.config.settings import Settings, get_settings
from recommendation_engine.models.schemas import (
    CommunityBronze,
    InterviewBronze,
    TrendSignal,
)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_interviews(path: Path | None = None, settings: Settings | None = None) -> list[InterviewBronze]:
    settings = settings or get_settings()
    path = path or settings.fixtures_dir / "mock_interviews.json"
    data = json.loads(path.read_text())
    return [
        InterviewBronze(
            interview_id=item["interview_id"],
            participant_role=item["participant_role"],
            timestamp=_parse_dt(item["timestamp"]) or datetime.now(),
            transcript=item["transcript"],
            tags=item.get("tags", []),
            interviewer=item.get("interviewer"),
            duration_minutes=item.get("duration_minutes"),
        )
        for item in data
    ]


def load_community(path: Path | None = None, settings: Settings | None = None) -> list[CommunityBronze]:
    settings = settings or get_settings()
    path = path or settings.fixtures_dir / "mock_community.json"
    data = json.loads(path.read_text())
    return [
        CommunityBronze(
            post_id=item["post_id"],
            author_role=item["author_role"],
            timestamp=_parse_dt(item["timestamp"]) or datetime.now(),
            body=item["body"],
            upvote_count=item.get("upvote_count", 0),
            tags=item.get("tags", []),
        )
        for item in data
    ]


def load_trend_signals(path: Path | None = None, settings: Settings | None = None) -> list[TrendSignal]:
    settings = settings or get_settings()
    path = path or settings.fixtures_dir / "mock_trend_signals.json"
    data = json.loads(path.read_text())
    signals: list[TrendSignal] = []
    for item in data:
        signals.append(
            TrendSignal(
                trend_id=item["trend_id"],
                theme=item["theme"],
                summary=item["summary"],
                evidence_urls=item.get("evidence_urls", []),
                source_count=item.get("source_count", 1),
                momentum=item.get("momentum", "stable"),
                novelty=item.get("novelty", "emerging"),
                first_seen=_parse_dt(item.get("first_seen")),
                peak_week=item.get("peak_week"),
                last_updated=_parse_dt(item.get("last_updated")),
            )
        )
    return signals
