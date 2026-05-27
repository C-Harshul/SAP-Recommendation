"""CLI entrypoint for the weekly recommendation job."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import structlog

from recommendation_engine.config.settings import get_settings
from recommendation_engine.config.validation import ConfigurationError, validate_production_config
from recommendation_engine.graph.workflow import run_weekly_pipeline
from recommendation_engine.io.data_loader import DataLoadError, load_pipeline_inputs
from recommendation_engine.io.embeddings import EmbeddingClient
from recommendation_engine.io.s3_loader import describe_s3_inventory
from recommendation_engine.io.pipeline_cache import load_latest_into_store_if_empty
from recommendation_engine.io.store import get_store, reset_store

log = structlog.get_logger()


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Experience Garage recommendation engine")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run weekly LangGraph pipeline (S3 + live APIs)")
    run_p.add_argument("--output", type=Path, help="Write ranked missions JSON to path")

    sub.add_parser("list-s3", help="Show what data exists in the S3 bucket")
    sub.add_parser("reset-store", help="Clear in-memory store")
    sub.add_parser("sync-s3", help="Upload latest local pipeline cache to S3")

    args = parser.parse_args()
    if args.command == "reset-store":
        reset_store()
        print("Store cleared.")
        return

    if args.command == "sync-s3":
        _sync_s3()
        return

    if args.command == "list-s3":
        _list_s3()
        return

    if args.command == "run":
        _run(args)


def _sync_s3() -> None:
    from recommendation_engine.io.mission_api import ranked_missions_api_from_store
    from recommendation_engine.io.pipeline_cache import sync_latest_cache_to_s3

    settings = get_settings()
    store = get_store()
    load_latest_into_store_if_empty(settings)
    api = ranked_missions_api_from_store(store, settings) if store.ranked_missions else None
    status = sync_latest_cache_to_s3(settings, ranked_missions_api=api)
    print(json.dumps(status, indent=2))
    if not status.get("ok"):
        sys.exit(1)


def _list_s3() -> None:
    settings = get_settings()
    try:
        inventory = describe_s3_inventory(settings)
        print(json.dumps(inventory, indent=2))
    except Exception as exc:
        print(f"Failed to list S3: {exc}", file=sys.stderr)
        print(
            "Check AWS_PROFILE, credentials, and EG_S3_BUCKET in .env",
            file=sys.stderr,
        )
        sys.exit(1)


def _run(args) -> None:
    settings = get_settings()
    reset_store()

    try:
        validate_production_config(settings)
    except ConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    try:
        interviews, community, trends = load_pipeline_inputs(settings)
    except DataLoadError as exc:
        print(str(exc), file=sys.stderr)
        print("Run: python -m recommendation_engine.main list-s3", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Failed to load data: {exc}", file=sys.stderr)
        sys.exit(1)

    embedder = EmbeddingClient(settings)
    missing = [t for t in trends if not t.embedding]
    if missing:
        texts = [f"{t.theme} {t.summary}" for t in missing]
        vectors = embedder.embed(texts)
        for trend, vec in zip(missing, vectors, strict=True):
            trend.embedding = vec

    log.info(
        "pipeline_start",
        interviews=len(interviews),
        community=len(community),
        trends=len(trends),
        llm_mode=settings.llm_mode,
        data_source=settings.data_source,
        enrich_bronze_trends=settings.enrich_bronze_trends,
        community_source=settings.community_source,
    )

    run_weekly_pipeline(
        interviews=interviews,
        community_posts=community,
        trend_signals=trends,
    )

    store = get_store()
    top = sorted(store.ranked_missions, key=lambda m: m.final_score, reverse=True)[
        : settings.top_missions
    ]

    payload = [
        {
            "rank": m.rank,
            "mission_id": m.mission_id,
            "cluster_id": m.cluster_id,
            "final_score": m.final_score,
            "impact_score": m.impact_score,
            "effort_score": m.effort_score,
            "subscores": {
                "source_count": m.source_count,
                "signal_urgency": m.signal_urgency,
                "market_validation": m.market_validation,
                "feasibility": m.feasibility,
                "sap_relevance": m.sap_relevance,
                "novelty": m.novelty,
            },
            "related_trend_ids": m.related_trend_ids,
            "writeup": m.writeup,
        }
        for m in top
    ]

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2))
        print(f"Wrote {len(payload)} missions to {args.output}")
    else:
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    cli()
