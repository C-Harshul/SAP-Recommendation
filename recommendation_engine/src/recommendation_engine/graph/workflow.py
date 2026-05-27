"""LangGraph workflow — weekly recommendation pipeline."""

from __future__ import annotations

import uuid

from langgraph.graph import END, START, StateGraph

from recommendation_engine.models.state import RecommendationState
from recommendation_engine.nodes import (
    cluster_node,
    extract_node,
    match_trends_node,
    persist_node,
    rank_node,
    synthesize_node,
    writeup_node,
)


def build_recommendation_graph():
    """
    Pipeline stages (plan § Tier 3):
      2. extract_node
      3. synthesize_node
      4. cluster_node
      5. match_trends_node
      6. rank_node
      7. writeup_node
      persist_node

    Stage 1 (market trend enrichment) runs continuously upstream;
    this graph reads gold.trend_signals / fixtures only.
    """
    graph = StateGraph(RecommendationState)

    graph.add_node("extract", extract_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("cluster", cluster_node)
    graph.add_node("match_trends", match_trends_node)
    graph.add_node("rank", rank_node)
    graph.add_node("writeup", writeup_node)
    graph.add_node("persist", persist_node)

    graph.add_edge(START, "extract")
    graph.add_edge("extract", "synthesize")
    graph.add_edge("synthesize", "cluster")
    graph.add_edge("cluster", "match_trends")
    graph.add_edge("match_trends", "rank")
    graph.add_edge("rank", "writeup")
    graph.add_edge("writeup", "persist")
    graph.add_edge("persist", END)

    return graph.compile()


def _initial_state(
    *,
    interviews,
    community_posts,
    trend_signals,
) -> RecommendationState:
    return {
        "run_id": uuid.uuid4().hex,
        "trace_id": uuid.uuid4().hex,
        "interviews": interviews,
        "community_posts": community_posts,
        "trend_signals": trend_signals,
        "extracted_ideas": [],
        "extracted_problems": [],
        "candidate_solutions": [],
        "errors": [],
    }


def run_weekly_pipeline(
    *,
    interviews,
    community_posts,
    trend_signals,
    on_graph_node_finish=None,
) -> RecommendationState:
    """Run the LangGraph pipeline; optional callback fires after each graph node."""
    app = build_recommendation_graph()
    initial = _initial_state(
        interviews=interviews,
        community_posts=community_posts,
        trend_signals=trend_signals,
    )
    if not on_graph_node_finish:
        return app.invoke(initial)

    state: dict = dict(initial)
    for chunk in app.stream(initial, stream_mode="updates"):
        for node_name, state_update in chunk.items():
            if isinstance(state_update, dict):
                state.update(state_update)
            on_graph_node_finish(node_name)
    return state  # type: ignore[return-value]
