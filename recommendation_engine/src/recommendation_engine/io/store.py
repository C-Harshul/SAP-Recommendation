"""In-memory store for v0; swap for Postgres when DATABASE_URL is set."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from recommendation_engine.models.schemas import (
    CandidateSolution,
    ExtractedIdea,
    IdeaCluster,
    RankedMission,
    TrendSignal,
)


@dataclass
class PipelineStore:
    """Silver/gold tables in memory for local runs and tests."""

    trend_signals: list[TrendSignal] = field(default_factory=list)
    extracted_ideas: list[ExtractedIdea] = field(default_factory=list)
    candidate_solutions: list[CandidateSolution] = field(default_factory=list)
    idea_clusters: list[IdeaCluster] = field(default_factory=list)
    ranked_missions: list[RankedMission] = field(default_factory=list)
    last_persisted_at: datetime | None = None
    cached_input_fingerprint: str | None = None
    cached_at: datetime | None = None

    def persist_run(
        self,
        ideas: list[ExtractedIdea],
        solutions: list[CandidateSolution],
        clusters: list[IdeaCluster],
        missions: list[RankedMission],
    ) -> None:
        self.extracted_ideas.extend(ideas)
        self.candidate_solutions.extend(solutions)
        self.idea_clusters = clusters
        self.ranked_missions = missions
        self.last_persisted_at = datetime.now(UTC)


_store: PipelineStore | None = None


def get_store() -> PipelineStore:
    global _store
    if _store is None:
        _store = PipelineStore()
    return _store


def reset_store() -> None:
    global _store
    _store = PipelineStore()
