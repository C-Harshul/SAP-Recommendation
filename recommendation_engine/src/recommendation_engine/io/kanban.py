"""Kanban board status for ranked missions (dashboard Mission Board)."""

from __future__ import annotations

from typing import Any

import structlog

from recommendation_engine.config.settings import Settings, get_settings
from recommendation_engine.io.pipeline_cache import load_snapshot_by_fingerprint, save_snapshot
from recommendation_engine.io.store import PipelineStore, get_store
from recommendation_engine.models.schemas import RankedMission

log = structlog.get_logger()

KANBAN_STATUSES = frozenset({"backlog", "ideation", "analysis", "prototype"})
DEFAULT_KANBAN_STATUS = "ideation"


def normalize_kanban_status(status: str) -> str:
    s = status.strip().lower()
    if s not in KANBAN_STATUSES:
        raise ValueError(
            f"Invalid kanban status '{status}'; expected one of: {', '.join(sorted(KANBAN_STATUSES))}"
        )
    return s


def mission_kanban_status(mission: RankedMission) -> str:
    raw = getattr(mission, "kanban_status", None) or DEFAULT_KANBAN_STATUS
    return raw if raw in KANBAN_STATUSES else DEFAULT_KANBAN_STATUS


def set_mission_kanban(store: PipelineStore, mission_id: str, status: str) -> RankedMission:
    normalized = normalize_kanban_status(status)
    for mission in store.ranked_missions:
        if mission.mission_id == mission_id:
            mission.kanban_status = normalized
            return mission
    raise KeyError(f"Mission not found: {mission_id}")


def apply_kanban_statuses(
    store: PipelineStore, statuses: dict[str, str]
) -> list[str]:
    """Apply status map; returns mission ids that were updated."""
    updated: list[str] = []
    for mission_id, status in statuses.items():
        set_mission_kanban(store, mission_id, status)
        updated.append(mission_id)
    return updated


def persist_kanban_to_cache(settings: Settings | None = None) -> dict[str, Any]:
    """Rewrite the latest pipeline snapshot with current store kanban fields."""
    settings = settings or get_settings()
    store = get_store()
    if not store.ranked_missions:
        return {"ok": False, "error": "No ranked missions in store"}

    fp = store.cached_input_fingerprint
    if not fp:
        from recommendation_engine.io.pipeline_cache import load_latest_snapshot

        snap = load_latest_snapshot(settings)
        if snap:
            fp = snap.input_fingerprint
    if not fp:
        return {"ok": False, "error": "No pipeline fingerprint (run ranking first)"}

    snap = load_snapshot_by_fingerprint(fp, settings)
    if not snap:
        return {"ok": False, "error": f"No snapshot for fingerprint {fp[:12]}"}

    by_id = {m.mission_id: m for m in store.ranked_missions}
    snap.ranked_missions = [
        by_id.get(m.mission_id, m) for m in snap.ranked_missions
    ]
    from recommendation_engine.io.mission_api import ranked_missions_api_from_store

    api_payload = ranked_missions_api_from_store(store, settings)
    path = save_snapshot(snap, settings, ranked_missions_api=api_payload)
    log.info("kanban_persisted", path=str(path), missions=len(store.ranked_missions))
    return {"ok": True, "path": str(path), "fingerprint": fp[:12]}
