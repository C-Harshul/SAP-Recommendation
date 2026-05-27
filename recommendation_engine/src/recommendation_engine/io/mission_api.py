"""Dashboard-shaped mission payloads (shared by API and S3 export)."""

from __future__ import annotations

from typing import Any

from recommendation_engine.config.settings import Settings, get_settings
from recommendation_engine.io.kanban import mission_kanban_status
from recommendation_engine.io.store import PipelineStore
from recommendation_engine.models.schemas import RankedMission


def _mission_title(writeup: str | None, mission_id: str) -> str:
    if not writeup:
        return mission_id.replace("_", " ").title()
    if "## The Mission" in writeup:
        tail = writeup.split("## The Mission", 1)[1]
        for line in tail.splitlines():
            text = line.strip()
            if text and not text.startswith("#"):
                return text[:160]
    first = writeup.strip().splitlines()[0] if writeup.strip() else mission_id
    return first[:160]


def mission_to_api(mission: RankedMission, clusters: dict[str, str]) -> dict[str, Any]:
    scale = 100.0
    title = _mission_title(mission.writeup, mission.mission_id)
    if title == mission.mission_id and mission.cluster_id in clusters:
        title = clusters[mission.cluster_id][:160]

    trend_count = len(mission.related_trend_ids)
    sources = [
        f"{int(mission.source_count)} source signals",
        f"{trend_count} market trend{'s' if trend_count != 1 else ''}",
    ]

    return {
        "id": mission.mission_id,
        "rank": mission.rank,
        "title": title,
        "impact": round(mission.impact_score * scale, 1),
        "effort": round(mission.effort_score * scale, 1),
        "value": round(mission.final_score * scale, 1),
        "score": round(mission.final_score * scale, 2),
        "status": mission_kanban_status(mission),
        "contributors": max(1, int(mission.source_count)),
        "sources": sources,
        "writeup": mission.writeup,
        "cluster_id": mission.cluster_id,
        "subscores": {
            "source_count": mission.source_count,
            "signal_urgency": mission.signal_urgency,
            "market_validation": mission.market_validation,
            "feasibility": mission.feasibility,
            "sap_relevance": mission.sap_relevance,
            "novelty": mission.novelty,
        },
        "related_trend_ids": mission.related_trend_ids,
    }


def ranked_missions_api_from_store(
    store: PipelineStore,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    settings = settings or get_settings()
    clusters = {c.cluster_id: c.canonical for c in store.idea_clusters}
    top = sorted(store.ranked_missions, key=lambda m: m.final_score, reverse=True)[
        : settings.top_missions
    ]
    return [mission_to_api(m, clusters) for m in top]
