"""Stage 4: Cluster ideas by embedding similarity and canonicalize."""

from __future__ import annotations

import uuid
import numpy as np
import structlog

from recommendation_engine.config.settings import get_settings
from recommendation_engine.io.embeddings import EmbeddingClient, cosine_similarity
from recommendation_engine.llm.client import LLMClient
from recommendation_engine.llm import prompts
from recommendation_engine.models.schemas import (
    ClusterBatchLLM,
    ClusterCanonicalLLM,
    ExtractedIdea,
    IdeaCluster,
    Specificity,
)
from recommendation_engine.models.state import RecommendationState

log = structlog.get_logger()


def _all_ideas(state: RecommendationState) -> list[ExtractedIdea]:
    ideas = list(state.get("extracted_ideas", []))
    # Promote synthesized solutions as pseudo-ideas for clustering
    for sol in state.get("candidate_solutions", []):
        parent = next((i for i in state.get("extracted_problems", []) if i.idea_id == sol.problem_id), None)
        pain = parent.pain_point if parent else "Synthesized mission"
        ideas.append(
            ExtractedIdea(
                idea_id=sol.solution_id,
                source_type="synthesized",
                source_id=sol.problem_id,
                pain_point=pain,
                proposed_solution=sol.solution_text,
                evidence_quotes=parent.evidence_quotes if parent else [],
                specificity=parent.specificity if parent else Specificity.SPECIFIC,
                embedding=sol.embedding,
                is_problem_only=False,
            )
        )
    return ideas


def cluster_node(state: RecommendationState) -> dict:
    settings = get_settings()
    llm = LLMClient(settings)
    embedder = EmbeddingClient(settings)
    threshold = settings.cluster_cosine_threshold

    ideas = _all_ideas(state)
    if not ideas:
        return {"idea_clusters": []}

    for idea in ideas:
        if not idea.embedding:
            idea.embedding = embedder.embed_query(f"{idea.pain_point} {idea.proposed_solution or ''}")

    assigned: set[str] = set()
    cluster_builds: list[tuple[list[ExtractedIdea], list[str]]] = []

    for seed in ideas:
        if seed.idea_id in assigned:
            continue
        members = [seed]
        assigned.add(seed.idea_id)
        for other in ideas:
            if other.idea_id in assigned or not other.embedding or not seed.embedding:
                continue
            if cosine_similarity(seed.embedding, other.embedding) >= threshold:
                members.append(other)
                assigned.add(other.idea_id)

        statements = [f"{m.pain_point}. {m.proposed_solution or ''}".strip() for m in members]
        cluster_builds.append((members, statements))

    canonical_by_index: dict[int, str] = {}
    if settings.llm_batch_cluster and len(cluster_builds) > 1:
        blocks = []
        for cidx, (_, statements) in enumerate(cluster_builds):
            bullets = "\n".join(f"  - {s}" for s in statements)
            blocks.append(f"### Cluster {cidx}\n{bullets}")
        batch_out = llm.structured(
            model=settings.model_cluster,
            system=prompts.CLUSTER_BATCH_SYSTEM,
            user=prompts.CLUSTER_BATCH_USER.format(clusters_block="\n\n".join(blocks)),
            output_schema=ClusterBatchLLM,
            max_tokens=8192,
        )
        for item in batch_out.clusters:
            canonical_by_index[item.cluster_index] = item.canonical_statement
    else:
        for cidx, (_, statements) in enumerate(cluster_builds):
            canonical_out = llm.structured(
                model=settings.model_cluster,
                system=prompts.CLUSTER_SYSTEM,
                user=prompts.CLUSTER_USER.format(
                    statements="\n".join(f"- {s}" for s in statements)
                ),
                output_schema=ClusterCanonicalLLM,
            )
            canonical_by_index[cidx] = canonical_out.canonical_statement

    clusters: list[IdeaCluster] = []
    for cidx, (members, statements) in enumerate(cluster_builds):
        source_ids = {f"{m.source_type}:{m.source_id}" for m in members}
        centroid = np.mean([m.embedding for m in members if m.embedding], axis=0).tolist()
        canonical = canonical_by_index.get(cidx) or (statements[0] if statements else "Cluster")
        clusters.append(
            IdeaCluster(
                cluster_id=f"cluster-{uuid.uuid4().hex[:8]}",
                canonical=canonical,
                source_count=len(source_ids),
                evidence_ids=[m.idea_id for m in members],
                member_idea_ids=[m.idea_id for m in members],
                embedding=centroid,
            )
        )

    log.info("cluster_complete", clusters=len(clusters), ideas=len(ideas))
    return {"idea_clusters": clusters}
