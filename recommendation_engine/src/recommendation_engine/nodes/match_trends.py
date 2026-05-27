"""Stage 5: Match each cluster to related market trends (asymmetric validation)."""

from __future__ import annotations

import structlog

from recommendation_engine.config.settings import get_settings
from recommendation_engine.io.embeddings import EmbeddingClient, cosine_similarity
from recommendation_engine.models.schemas import IdeaCluster
from recommendation_engine.models.state import RecommendationState
from recommendation_engine.scoring.programmatic import market_alignment_flag

log = structlog.get_logger()


def match_trends_node(state: RecommendationState) -> dict:
    settings = get_settings()
    embedder = EmbeddingClient(settings)
    trends = state.get("trend_signals", [])
    clusters: list[IdeaCluster] = list(state.get("idea_clusters", []))

    enriched: list[IdeaCluster] = []
    for cluster in clusters:
        query = embedder.embed_query(cluster.canonical)
        scored = []
        for t in trends:
            if not t.embedding:
                t.embedding = embedder.embed_query(f"{t.theme} {t.summary}")
            scored.append((cosine_similarity(query, t.embedding), t))
        scored.sort(key=lambda x: x[0], reverse=True)
        related = [t for _, t in scored[: settings.trend_retrieval_k]]
        flag = market_alignment_flag(cluster, len(related))
        enriched.append(
            cluster.model_copy(
                update={
                    "related_trends": related,
                    "market_alignment_flag": flag,
                }
            )
        )

    log.info("match_trends_complete", clusters=len(enriched))
    return {"clusters_with_trends": enriched}
