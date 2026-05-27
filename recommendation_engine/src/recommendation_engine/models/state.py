"""LangGraph workflow state."""

from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

from recommendation_engine.models.schemas import (
    CandidateSolution,
    ExtractedIdea,
    IdeaCluster,
    InterviewBronze,
    CommunityBronze,
    RankedMission,
    TrendSignal,
)


def _merge_lists(left: list, right: list) -> list:
    return left + right


class RecommendationState(TypedDict, total=False):
    """State passed through the weekly recommendation graph."""

    run_id: str
    trace_id: str

    # Inputs loaded at graph start
    interviews: list[InterviewBronze]
    community_posts: list[CommunityBronze]
    trend_signals: list[TrendSignal]

    # Stage 2
    extracted_ideas: Annotated[list[ExtractedIdea], _merge_lists]
    extracted_problems: Annotated[list[ExtractedIdea], _merge_lists]

    # Stage 3
    candidate_solutions: Annotated[list[CandidateSolution], _merge_lists]

    # Stage 4
    idea_clusters: list[IdeaCluster]

    # Stage 5 — clusters enriched with related_trends in-place
    clusters_with_trends: list[IdeaCluster]

    # Stage 6
    ranked_missions: list[RankedMission]

    # Stage 7 — writeups attached to top missions
    missions_with_writeups: list[RankedMission]

    # Audit / messages for LangSmith
    messages: Annotated[list, add_messages]
    errors: Annotated[list[str], _merge_lists]
