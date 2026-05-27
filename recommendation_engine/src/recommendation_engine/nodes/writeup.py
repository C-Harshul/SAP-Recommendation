"""Stage 7: Generate 5-section mission write-ups for top-ranked clusters."""

from __future__ import annotations

import structlog

from recommendation_engine.config.settings import get_settings
from recommendation_engine.llm.client import LLMClient
from recommendation_engine.llm import prompts
from recommendation_engine.models.schemas import MissionWriteupLLM, RankedMission
from recommendation_engine.models.state import RecommendationState

log = structlog.get_logger()


def writeup_node(state: RecommendationState) -> dict:
    settings = get_settings()
    llm = LLMClient(settings)
    top_n = settings.top_missions
    missions = sorted(state.get("ranked_missions", []), key=lambda m: m.final_score, reverse=True)
    clusters = {c.cluster_id: c for c in state.get("clusters_with_trends", [])}

    with_writeups: list[RankedMission] = []
    for mission in missions:
        if mission.rank > top_n:
            with_writeups.append(mission)
            continue
        cluster = clusters.get(mission.cluster_id)
        if not cluster:
            with_writeups.append(mission)
            continue

        evidence = cluster.canonical
        trends = "\n".join(
            f"- {t.theme}: {t.summary}\n  URLs: {', '.join(t.evidence_urls)}"
            for t in cluster.related_trends
        )
        writeup = llm.structured(
            model=settings.model_writeup,
            system=prompts.WRITEUP_SYSTEM,
            user=prompts.WRITEUP_USER.format(
                canonical=cluster.canonical,
                feasibility=mission.feasibility,
                market_validation=mission.market_validation,
                impact_score=mission.impact_score,
                effort_score=mission.effort_score,
                evidence=evidence,
                trends=trends or "(no market trends matched)",
            ),
            output_schema=MissionWriteupLLM,
        )
        with_writeups.append(mission.model_copy(update={"writeup": writeup.to_markdown()}))

    log.info("writeup_complete", top_writeups=min(top_n, len(missions)))
    return {"missions_with_writeups": with_writeups}
