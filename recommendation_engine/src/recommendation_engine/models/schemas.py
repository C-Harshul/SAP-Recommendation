"""Pydantic schemas for pipeline I/O and LLM structured outputs."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Specificity(StrEnum):
    VAGUE = "vague"
    SPECIFIC = "specific"
    ACTIONABLE = "actionable"


class Momentum(StrEnum):
    RISING = "rising"
    STABLE = "stable"
    FADING = "fading"


class SolutionOrigin(StrEnum):
    USER_PROPOSED = "user_proposed"
    LLM_SYNTHESIZED = "llm_synthesized"


# --- Bronze inputs (aligned with Market_trends ingestion envelope) ---


class MarketBronzeRecord(BaseModel):
    """Bronze JSONL row from market ingestion — basis for trend_signals enrichment."""

    source_id: str
    category: str
    ingested_at: datetime
    source_published_at: datetime | None = None
    source_url: str | None = None
    external_id: str
    raw: dict[str, Any] = Field(default_factory=dict)


class InterviewBronze(BaseModel):
    interview_id: str
    participant_role: str
    timestamp: datetime
    transcript: str
    tags: list[str] = Field(default_factory=list)
    interviewer: str | None = None
    duration_minutes: int | None = None


class CommunityBronze(BaseModel):
    post_id: str
    author_role: str
    timestamp: datetime
    body: str
    upvote_count: int = 0
    tags: list[str] = Field(default_factory=list)


# --- Gold trend signals (enrichment output; graph reads these) ---


class TrendSignal(BaseModel):
    trend_id: str
    theme: str
    summary: str
    evidence_urls: list[str] = Field(default_factory=list)
    source_count: int = 1
    momentum: Momentum = Momentum.STABLE
    novelty: str = "emerging"
    first_seen: datetime | None = None
    peak_week: str | None = None
    embedding: list[float] | None = None
    last_updated: datetime | None = None


# --- Silver / gold pipeline entities ---


class EvidenceQuote(BaseModel):
    quote: str
    source_type: str
    source_id: str


class ExtractedIdea(BaseModel):
    idea_id: str
    source_type: str
    source_id: str
    pain_point: str
    proposed_solution: str | None = None
    evidence_quotes: list[EvidenceQuote]
    sentiment: str = "neutral"
    specificity: Specificity
    embedding: list[float] | None = None
    is_problem_only: bool = False


class CandidateSolution(BaseModel):
    solution_id: str
    problem_id: str
    solution_text: str
    approach: str
    origin: SolutionOrigin
    inspired_by: list[str] = Field(default_factory=list)
    embedding: list[float] | None = None


class IdeaCluster(BaseModel):
    cluster_id: str
    canonical: str
    source_count: int
    evidence_ids: list[str]
    member_idea_ids: list[str] = Field(default_factory=list)
    embedding: list[float] | None = None
    related_trends: list[TrendSignal] = Field(default_factory=list)
    market_alignment_flag: str | None = None


class QualitativeScores(BaseModel):
    """LLM-scored dimensions (0–1)."""

    signal_urgency: float = Field(ge=0, le=1)
    market_validation: float = Field(ge=0, le=1)
    sap_relevance: float = Field(ge=0, le=1)
    feasibility: float = Field(ge=0, le=1)
    novelty: float = Field(ge=0, le=1)
    rationale: str = ""


class RankedMission(BaseModel):
    mission_id: str
    cluster_id: str
    rank: int
    source_count: float
    source_diversity: float
    recency: float
    specificity: float
    signal_urgency: float
    market_validation: float
    feasibility: float
    sap_relevance: float
    novelty: float
    effort_score: float
    impact_score: float
    final_score: float
    weights_version: str
    writeup: str | None = None
    related_trend_ids: list[str] = Field(default_factory=list)
    trace_id: str | None = None
    prompt_version: str = "v1.0"
    kanban_status: str = "ideation"


# --- LLM structured extraction outputs ---


class ExtractedIdeaLLM(BaseModel):
    pain_point: str
    proposed_solution: str | None = None
    evidence_quotes: list[str]
    sentiment: str = "neutral"
    specificity: Specificity


class ExtractNodeOutput(BaseModel):
    ideas: list[ExtractedIdeaLLM]


class SynthesizedSolutionLLM(BaseModel):
    solution_text: str
    approach: str


class SynthesizeNodeOutput(BaseModel):
    solutions: list[SynthesizedSolutionLLM]


class ClusterCanonicalLLM(BaseModel):
    canonical_statement: str


class ClusterBatchItemLLM(BaseModel):
    cluster_index: int = Field(ge=0)
    canonical_statement: str


class ClusterBatchLLM(BaseModel):
    clusters: list[ClusterBatchItemLLM]


class RankBatchItemLLM(BaseModel):
    cluster_index: int = Field(ge=0)
    signal_urgency: float = Field(ge=0, le=1)
    market_validation: float = Field(ge=0, le=1)
    sap_relevance: float = Field(ge=0, le=1)
    feasibility: float = Field(ge=0, le=1)
    novelty: float = Field(ge=0, le=1)
    rationale: str = ""


class RankBatchLLM(BaseModel):
    rankings: list[RankBatchItemLLM]


class SynthesizeBatchItemLLM(BaseModel):
    problem_index: int = Field(ge=0)
    solutions: list[SynthesizedSolutionLLM]


class SynthesizeBatchLLM(BaseModel):
    problems: list[SynthesizeBatchItemLLM]


class EnrichedTrendItemLLM(BaseModel):
    trend_id: str
    theme: str
    summary: str
    momentum: str
    novelty: str
    evidence_urls: list[str] = Field(default_factory=list)


class EnrichedTrendBatchLLM(BaseModel):
    trends: list[EnrichedTrendItemLLM]


class MissionWriteupLLM(BaseModel):
    the_mission: str
    why_this_matters: str
    industry_context: str
    suggested_approach: str
    risks_and_open_questions: str

    def to_markdown(self) -> str:
        return (
            f"## The Mission\n\n{self.the_mission}\n\n"
            f"## Why This Matters\n\n{self.why_this_matters}\n\n"
            f"## Industry Context\n\n{self.industry_context}\n\n"
            f"## Suggested Approach\n\n{self.suggested_approach}\n\n"
            f"## Risks and Open Questions\n\n{self.risks_and_open_questions}\n"
        )
