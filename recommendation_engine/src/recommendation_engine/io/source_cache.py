"""Per-source extract cache — skip Gemini when transcript/post unchanged."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import structlog

from recommendation_engine.config.settings import Settings, get_settings
from recommendation_engine.io.fingerprints import extract_stage_fingerprint
from recommendation_engine.io.pipeline_cache import cache_root
from recommendation_engine.models.pipeline_snapshot import SourceExtractCache
from recommendation_engine.models.schemas import ExtractedIdea

log = structlog.get_logger()


def _source_path(
    source_type: str,
    source_id: str,
    content_hash: str,
    stage_fp: str,
    settings: Settings | None = None,
) -> Path:
    root = cache_root(settings) / "sources"
    safe_id = source_id.replace("/", "_")
    name = f"{source_type}_{safe_id}_{content_hash[:16]}_{stage_fp[:12]}.json"
    return root / name


def get_cached_extract(
    *,
    source_type: str,
    source_id: str,
    content_hash: str,
    settings: Settings | None = None,
) -> list[ExtractedIdea] | None:
    settings = settings or get_settings()
    if not settings.pipeline_cache_enabled:
        return None
    stage_fp = extract_stage_fingerprint(settings)
    path = _source_path(source_type, source_id, content_hash, stage_fp, settings)
    if not path.is_file():
        return None
    try:
        record = SourceExtractCache.model_validate_json(path.read_text(encoding="utf-8"))
        if record.extract_stage_fingerprint != stage_fp:
            return None
        log.info(
            "source_extract_cache_hit",
            source_type=source_type,
            source_id=source_id,
            ideas=len(record.ideas),
        )
        return record.ideas
    except Exception as exc:
        log.warning("source_extract_cache_load_failed", path=str(path), error=str(exc))
        return None


def save_cached_extract(
    *,
    source_type: str,
    source_id: str,
    content_hash: str,
    ideas: list[ExtractedIdea],
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    if not settings.pipeline_cache_enabled:
        return
    stage_fp = extract_stage_fingerprint(settings)
    record = SourceExtractCache(
        source_type=source_type,
        source_id=source_id,
        content_hash=content_hash,
        extract_stage_fingerprint=stage_fp,
        processed_at=datetime.now(UTC),
        ideas=ideas,
    )
    path = _source_path(source_type, source_id, content_hash, stage_fp, settings)
    path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
    log.info(
        "source_extract_cache_saved",
        source_type=source_type,
        source_id=source_id,
        ideas=len(ideas),
    )
