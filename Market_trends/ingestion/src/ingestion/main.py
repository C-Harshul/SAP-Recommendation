"""CLI entrypoint and health HTTP server."""

from __future__ import annotations

import argparse
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import boto3

from ingestion.config.settings import get_settings
from ingestion.connectors.registry import load_sources_yaml
from ingestion.io.s3_writer import S3Writer
from ingestion.io.state_store import StateStore
from ingestion.runtime.logging_setup import configure_logging
from ingestion.runtime.metrics import MetricsEmitter
from ingestion.runtime.rate_limiter import RateLimiterRegistry
from ingestion.runtime.scheduler import Scheduler


def _s3_client(settings: Any) -> Any:
    kwargs: dict[str, Any] = {"region_name": settings.aws_region}
    if settings.aws_endpoint_url:
        kwargs["endpoint_url"] = settings.aws_endpoint_url
    return boto3.client("s3", **kwargs)


def _build_scheduler() -> Scheduler:
    settings = get_settings()
    s3 = _s3_client(settings)
    writer = S3Writer(s3, settings.s3_bucket, settings.s3_bronze_prefix)
    state = StateStore(s3, settings.s3_bucket, settings.s3_bronze_prefix)
    cw = None
    if settings.environment == "prod":
        cw = boto3.client("cloudwatch", region_name=settings.aws_region)
    metrics = MetricsEmitter(cw, enabled=settings.environment == "prod")
    return Scheduler(writer, state, RateLimiterRegistry(), metrics)


class HealthHandler(BaseHTTPRequestHandler):
    """GET /healthz — last successful run per source."""

    state_store: StateStore | None = None

    def do_GET(self) -> None:
        if self.path not in ("/healthz", "/health"):
            self.send_response(404)
            self.end_headers()
            return
        sources = load_sources_yaml()
        payload: dict[str, Any] = {"status": "ok", "sources": {}}
        store = self.state_store
        if store:
            for src in sources:
                sid = src["id"]
                cursor = store.load(sid)
                payload["sources"][sid] = {
                    "last_successful_run_at": (
                        cursor.last_successful_run_at.isoformat()
                        if cursor.last_successful_run_at
                        else None
                    ),
                    "last_source_published_at": (
                        cursor.last_source_published_at.isoformat()
                        if cursor.last_source_published_at
                        else None
                    ),
                }
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def start_health_server(port: int) -> HTTPServer:
    settings = get_settings()
    s3 = _s3_client(settings)
    state = StateStore(s3, settings.s3_bucket, settings.s3_bronze_prefix)
    HealthHandler.state_store = state
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EG market trends ingestion")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run ingestion for one or more sources")
    run_p.add_argument("--source", "-s", help="Single source_id")
    run_p.add_argument(
        "--group",
        "-g",
        help="Cadence group: rss_30, api_60, playwright_360, arxiv_1440",
    )
    run_p.add_argument("--all", action="store_true", help="Run all sources")

    sub.add_parser("health", help="Start health server only")

    health_p = sub.add_parser("serve", help="Start health server and optionally run")
    health_p.add_argument("--port", type=int, default=None)

    args = parser.parse_args(argv)
    settings = get_settings()
    configure_logging(settings.log_level)

    if args.command == "health":
        port = settings.health_port
        start_health_server(port)
        print(f"Health server on :{port}/healthz", flush=True)
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            return 0
        return 0

    if args.command == "serve":
        port = args.port or settings.health_port
        start_health_server(port)
        print(f"Health server on :{port}/healthz", flush=True)
        threading.Event().wait()
        return 0

    scheduler = _build_scheduler()
    if args.command == "run":
        if args.source:
            result = scheduler.run_source(args.source)
            print(json.dumps(result.model_dump(mode="json"), indent=2))
            return 0 if result.errors == 0 else 1
        if args.group:
            results = scheduler.run_group(args.group)
            print(json.dumps([r.model_dump(mode="json") for r in results], indent=2))
            return 0
        if args.all:
            results = scheduler.run_all()
            print(json.dumps([r.model_dump(mode="json") for r in results], indent=2))
            return 0
        run_p.error("Specify --source, --group, or --all")

    return 1


if __name__ == "__main__":
    sys.exit(cli())
