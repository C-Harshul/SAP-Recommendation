"""Serialized pipeline output for disk cache."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from recommendation_engine.models.schemas import (
    CandidateSolution,
    ExtractedIdea,
    IdeaCluster,
    RankedMission,
    TrendSignal,
)


class PipelineSnapshot(BaseModel):
    schema_version: str = "1"
    input_fingerprint: str
    config_fingerprint: str
    created_at: datetime
    prompt_version: str
    weights_version: str
    git_sha: str
    interviews_count: int = 0
    community_count: int = 0
    trends_count: int = 0
    trend_signals: list[TrendSignal] = Field(default_factory=list)
    extracted_ideas: list[ExtractedIdea] = Field(default_factory=list)
    extracted_problems: list[ExtractedIdea] = Field(default_factory=list)
    candidate_solutions: list[CandidateSolution] = Field(default_factory=list)
    idea_clusters: list[IdeaCluster] = Field(default_factory=list)
    ranked_missions: list[RankedMission] = Field(default_factory=list)


class SourceExtractCache(BaseModel):
    """Per-source extract output — skip LLM if content unchanged."""

    source_type: str
    source_id: str
    content_hash: str
    extract_stage_fingerprint: str
    processed_at: datetime
    ideas: list[ExtractedIdea] = Field(default_factory=list)
