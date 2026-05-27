"""Stage 6: Hybrid ranking — programmatic features + LLM qualitative scores."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

from recommendation_engine.config.settings import get_settings
from recommendation_engine.llm.client import LLMClient
from recommendation_engine.llm import prompts
from recommendation_engine.models.schemas import (
    ExtractedIdea,
    QualitativeScores,
    RankBatchLLM,
    RankedMission,
)
from recommendation_engine.models.state import RecommendationState
from recommendation_engine.scoring.programmatic import (
    effort_score,
    final_weighted_score,
    impact_score,
    load_weights,
    log_scaled_source_count,
    recency_score,
    shannon_entropy_source_diversity,
    specificity_fraction,
)

log = structlog.get_logger()


def _ideas_by_id(state: RecommendationState) -> dict[str, ExtractedIdea]:
    mapping: dict[str, ExtractedIdea] = {}
    for idea in state.get("extracted_ideas", []):
        mapping[idea.idea_id] = idea
    for idea in state.get("extracted_problems", []):
        mapping[idea.idea_id] = idea
    for sol in state.get("candidate_solutions", []):
        parent = mapping.get(sol.problem_id)
        mapping[sol.solution_id] = ExtractedIdea(
            idea_id=sol.solution_id,
            source_type="synthesized",
            source_id=sol.problem_id,
            pain_point=parent.pain_point if parent else "",
            proposed_solution=sol.solution_text,
            evidence_quotes=parent.evidence_quotes if parent else [],
            specificity=parent.specificity if parent else "specific",
        )
    return mapping


def rank_node(state: RecommendationState) -> dict:
    settings = get_settings()
    llm = LLMClient(settings)
    weights = load_weights()
    idea_map = _ideas_by_id(state)
    clusters = state.get("clusters_with_trends") or state.get("idea_clusters", [])

    missions: list[RankedMission] = []
    for cluster in clusters:
        member_ideas = [idea_map[iid] for iid in cluster.member_idea_ids if iid in idea_map]
        source_types = [i.source_type for i in member_ideas]
        prog_source_count = log_scaled_source_count(cluster.source_count)
        prog_diversity = shannon_entropy_source_diversity(source_types)
        prog_specificity = specificity_fraction(member_ideas)
        prog_recency = recency_score([datetime.now(UTC)])

        trend_block = "\n".join(
            f"- {t.theme} ({t.momentum}): {t.summary} urls={t.evidence_urls}"
            for t in cluster.related_trends
        )
        qualitative = llm.structured(
            model=settings.model_rank_qualitative,
            system=prompts.RANK_QUALITATIVE_SYSTEM,
            user=prompts.RANK_QUALITATIVE_USER.format(
                canonical=cluster.canonical,
                source_count=cluster.source_count,
                specificity_note=f"{prog_specificity:.2f} actionable/specific fraction",
                trends=trend_block or "(none)",
            ),
            output_schema=QualitativeScores,
        )

        subscores = {
            "source_count": prog_source_count,
            "source_diversity": prog_diversity,
            "recency": prog_recency,
            "specificity": prog_specificity,
            "signal_urgency": qualitative.signal_urgency,
            "market_validation": qualitative.market_validation,
            "feasibility": qualitative.feasibility,
            "sap_relevance": qualitative.sap_relevance,
            "novelty": qualitative.novelty,
        }
        final = final_weighted_score(subscores, weights)
        eff = effort_score(qualitative.feasibility)
        imp = impact_score(
            source_count=prog_source_count,
            signal_urgency=qualitative.signal_urgency,
            market_validation=qualitative.market_validation,
            sap_relevance=qualitative.sap_relevance,
            novelty=qualitative.novelty,
        )

        missions.append(
            RankedMission(
                mission_id=f"mission-{uuid.uuid4().hex[:8]}",
                cluster_id=cluster.cluster_id,
                rank=0,
                source_count=subscores["source_count"],
                source_diversity=subscores["source_diversity"],
                recency=subscores["recency"],
                specificity=subscores["specificity"],
                signal_urgency=subscores["signal_urgency"],
                market_validation=subscores["market_validation"],
                feasibility=subscores["feasibility"],
                sap_relevance=subscores["sap_relevance"],
                novelty=subscores["novelty"],
                effort_score=eff,
                impact_score=imp,
                final_score=final,
                weights_version=settings.weights_version,
                related_trend_ids=[t.trend_id for t in cluster.related_trends],
                trace_id=state.get("trace_id"),
                prompt_version=settings.prompt_version,
            )
        )

    missions.sort(key=lambda m: m.final_score, reverse=True)
    for idx, mission in enumerate(missions, start=1):
        mission.rank = idx

    log.info("rank_complete", missions=len(missions))
    return {"ranked_missions": missions}
