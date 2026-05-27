"""FastAPI server exposing ranked missions and pipeline triggers for the dashboard."""

from __future__ import annotations

import os
import secrets
import time

from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from recommendation_engine.api.pipeline_runner import (
    get_pipeline_state,
    list_ranked_missions,
    start_pipeline_run,
)
from recommendation_engine.api.newsletter import (
    NewsletterConfigError,
    build_oauth_authorize_url,
    exchange_code_for_tokens,
    resolve_sender_email,
    oauth_config_ready,
    send_ranked_missions_newsletter,
)
from recommendation_engine.config.settings import get_settings
from recommendation_engine.io.kanban import (
    apply_kanban_statuses,
    persist_kanban_to_cache,
    set_mission_kanban,
)
from recommendation_engine.io.mission_api import ranked_missions_api_from_store
from recommendation_engine.io.pipeline_cache import (
    get_last_s3_upload_status,
    load_latest_into_store_if_empty,
    sync_latest_cache_to_s3,
)
from recommendation_engine.io.store import get_store
from recommendation_engine.io.s3_loader import describe_s3_inventory

_default_origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

_extra = os.getenv("EG_CORS_ORIGINS", "")
_cors_origins = _default_origins + [o.strip() for o in _extra.split(",") if o.strip()]


@dataclass
class RuntimeNewsletterOAuth:
    refresh_token: str | None = None
    sender_email: str | None = None
    connected_at: float | None = None
    pending_states: dict[str, float] = field(default_factory=dict)


_oauth = RuntimeNewsletterOAuth()


def _new_oauth_state() -> str:
    state = secrets.token_urlsafe(24)
    _oauth.pending_states[state] = time.time() + 900
    now = time.time()
    _oauth.pending_states = {k: v for k, v in _oauth.pending_states.items() if v > now}
    return state


def _consume_oauth_state(state: str) -> None:
    expires = _oauth.pending_states.pop(state, None)
    if not expires or expires < time.time():
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    load_latest_into_store_if_empty(get_settings())
    yield


app = FastAPI(
    title="Experience Garage Recommendation API",
    version="0.1.0",
    description="Triggers the LangGraph ranking pipeline and serves results to rec-pilot-dash.",
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/pipeline/status")
def pipeline_status() -> dict:
    return get_pipeline_state().snapshot()


@app.post("/api/pipeline/run")
def pipeline_run() -> dict:
    return start_pipeline_run()


@app.post("/api/pipeline/sync-s3")
def pipeline_sync_s3() -> dict:
    """Backfill: upload latest local cache to S3 (bronze/gold/pipeline_runs/)."""
    settings = get_settings()
    store = get_store()
    api_payload = ranked_missions_api_from_store(store, settings) if store.ranked_missions else None
    status = sync_latest_cache_to_s3(settings, ranked_missions_api=api_payload)
    return {"s3_upload": status}


class KanbanStatusBody(BaseModel):
    status: str


class KanbanBulkBody(BaseModel):
    statuses: dict[str, str] = Field(..., min_length=1)


class NewsletterSendBody(BaseModel):
    recipient: str | None = None
    top_n: int = Field(default=10, ge=1, le=50)


class NewsletterOAuthStartBody(BaseModel):
    redirect_uri: str


class NewsletterOAuthExchangeBody(BaseModel):
    code: str
    state: str
    redirect_uri: str


@app.patch("/api/kanban/missions/{mission_id}")
def kanban_patch_mission(mission_id: str, body: KanbanStatusBody) -> dict:
    store = get_store()
    try:
        mission = set_mission_kanban(store, mission_id, body.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    persist = persist_kanban_to_cache(get_settings())
    return {
        "mission_id": mission.mission_id,
        "status": mission.kanban_status,
        "persist": persist,
    }


@app.put("/api/kanban/statuses")
def kanban_put_statuses(body: KanbanBulkBody) -> dict:
    store = get_store()
    try:
        updated = apply_kanban_statuses(store, body.statuses)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    persist = persist_kanban_to_cache(get_settings())
    return {"updated": updated, "count": len(updated), "persist": persist}


@app.get("/api/missions/ranked")
def missions_ranked() -> dict:
    settings = get_settings()
    missions = list_ranked_missions()
    state = get_pipeline_state().snapshot()
    return {
        "missions": missions,
        "count": len(missions),
        "pipeline": state,
        "data_source": {
            "interviews": "s3",
            "community": settings.community_source,
            "market_trends": "s3",
            "community_hardcoded": settings.use_mock_community,
            "embedding_provider": settings.embedding_provider,
            "databricks_embeddings": settings.use_databricks_embeddings,
        },
    }


@app.post("/api/newsletter/send")
def newsletter_send(body: NewsletterSendBody) -> dict:
    settings = get_settings()
    missions = list_ranked_missions(settings)[: body.top_n]
    if not missions:
        raise HTTPException(status_code=400, detail="No ranked missions available to email")
    try:
        result = send_ranked_missions_newsletter(
            settings=settings,
            missions=missions,
            recipient=body.recipient,
            refresh_token_override=_oauth.refresh_token,
            sender_override=_oauth.sender_email,
        )
    except NewsletterConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gmail send failed: {exc}") from exc
    return {"ok": True, **result}


@app.get("/api/newsletter/oauth/status")
def newsletter_oauth_status() -> dict:
    settings = get_settings()
    active_sender = _oauth.sender_email or settings.gmail_sender_email
    return {
        "oauth_client_ready": oauth_config_ready(settings),
        "connected": bool(_oauth.refresh_token or settings.gmail_refresh_token),
        "sender_email": active_sender,
        "runtime_connected": bool(_oauth.refresh_token),
    }


@app.post("/api/newsletter/oauth/start")
def newsletter_oauth_start(body: NewsletterOAuthStartBody) -> dict:
    settings = get_settings()
    state = _new_oauth_state()
    try:
        url = build_oauth_authorize_url(
            settings=settings,
            redirect_uri=body.redirect_uri,
            state=state,
        )
    except NewsletterConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"auth_url": url, "state": state}


@app.post("/api/newsletter/oauth/exchange")
def newsletter_oauth_exchange(body: NewsletterOAuthExchangeBody) -> dict:
    settings = get_settings()
    _consume_oauth_state(body.state)
    try:
        token_data = exchange_code_for_tokens(
            settings=settings,
            code=body.code,
            redirect_uri=body.redirect_uri,
        )
        refresh_token = token_data.get("refresh_token")
        access_token = token_data.get("access_token")
        if not refresh_token:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No refresh token returned by Google. Re-authorize with prompt=consent "
                    "and ensure Access type is offline."
                ),
            )
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token returned by Google")
        sender_email = resolve_sender_email(access_token=access_token, settings=settings)
    except HTTPException:
        raise
    except NewsletterConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OAuth exchange failed: {exc}") from exc
    _oauth.refresh_token = str(refresh_token)
    _oauth.sender_email = sender_email
    _oauth.connected_at = time.time()
    return {
        "ok": True,
        "sender_email": sender_email,
        "refresh_token": refresh_token,
        "note": "Saved in API runtime memory. Add to .env for persistence across restarts.",
    }


@app.get("/api/data/summary")
def data_summary() -> dict:
    settings = get_settings()
    inventory = describe_s3_inventory(settings)
    state = get_pipeline_state().snapshot()
    community_note = (
        "hardcoded fixtures (mock_community.json)"
        if settings.use_mock_community
        else "s3://…/community/"
    )
    return {
        "bucket": inventory.get("bucket"),
        "s3": inventory,
        "pipeline": state,
        "config": {
            "community_source": settings.community_source,
            "community_note": community_note,
            "enrich_bronze_trends": settings.enrich_bronze_trends,
            "lookback_days": settings.lookback_days,
        },
    }


@app.get("/api/data/inventory")
def data_inventory() -> dict:
    settings = get_settings()
    return describe_s3_inventory(settings)


def main() -> None:
    import uvicorn

    host = os.getenv("EG_API_HOST", "127.0.0.1")
    port = int(os.getenv("EG_API_PORT", "8000"))
    uvicorn.run(
        "recommendation_engine.api.server:app",
        host=host,
        port=port,
        reload=os.getenv("EG_API_RELOAD", "").lower() in ("1", "true", "yes"),
    )


if __name__ == "__main__":
    main()
