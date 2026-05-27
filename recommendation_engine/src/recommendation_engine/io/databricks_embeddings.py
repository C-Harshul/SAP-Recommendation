"""Databricks Foundation Model embedding API (OpenAI-compatible serving endpoints)."""

from __future__ import annotations

import re
import time
from typing import Any

import httpx
import structlog

from recommendation_engine.config.settings import Settings

log = structlog.get_logger()

# Pay-per-token embedding endpoint (see Databricks Serving → Foundation Model APIs)
DEFAULT_DATABRICKS_EMBEDDING_ENDPOINT = "databricks-gte-large-en"
DATABRICKS_EMBED_BATCH_MAX = 128


class DatabricksEmbeddingError(RuntimeError):
    pass


class DatabricksEmbeddingAuthError(DatabricksEmbeddingError):
    """403/401 — token missing model-serving scope or invalid."""


def is_auth_or_scope_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return (
        isinstance(exc, DatabricksEmbeddingAuthError)
        or "403" in text
        or "401" in text
        or "model-serving" in text
        or "required scopes" in text
    )


def _normalize_host(host: str) -> str:
    h = host.strip().rstrip("/")
    if not h.startswith("http"):
        h = f"https://{h}"
    return h


def _parse_embeddings_payload(payload: dict[str, Any]) -> list[list[float]]:
    """OpenAI-style: { data: [{ embedding, index }, ...] }."""
    if "data" in payload and isinstance(payload["data"], list):
        rows = payload["data"]
        if rows and isinstance(rows[0], dict) and "embedding" in rows[0]:
            ordered = sorted(rows, key=lambda r: r.get("index", 0))
            return [list(r["embedding"]) for r in ordered]
    # Single vector: { embedding: [...] }
    if "embedding" in payload and isinstance(payload["embedding"], list):
        return [list(payload["embedding"])]
    raise DatabricksEmbeddingError(f"Unexpected embedding response shape: {list(payload.keys())}")


def _is_rate_limit(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "429" in text or "rate" in text or "quota" in text


def _retry_after_seconds(exc: BaseException) -> float:
    match = re.search(r"retry in (\d+(?:\.\d+)?)s", str(exc), re.I)
    return float(match.group(1)) + 2.0 if match else 15.0


def embed_texts_databricks(
    texts: list[str],
    *,
    settings: Settings,
) -> list[list[float]]:
    """Call Databricks serving endpoint for document embeddings."""
    if not texts:
        return []

    host = settings.databricks_host
    token = settings.databricks_token
    if not host or not token:
        raise DatabricksEmbeddingError(
            "DATABRICKS_HOST and DATABRICKS_TOKEN are required for EG_EMBEDDING_PROVIDER=databricks."
        )

    endpoint = settings.databricks_embedding_endpoint
    base = _normalize_host(host)
    url = f"{base}/serving-endpoints/{endpoint}/invocations"
    batch_size = min(
        max(1, settings.embedding_batch_size),
        DATABRICKS_EMBED_BATCH_MAX,
    )
    delay = max(0.0, settings.embedding_request_delay_seconds)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    all_vectors: list[list[float]] = []
    total_batches = (len(texts) + batch_size - 1) // batch_size

    with httpx.Client(timeout=120.0) as client:
        for batch_idx, start in enumerate(range(0, len(texts), batch_size)):
            if batch_idx > 0 and delay > 0:
                time.sleep(delay)
            batch = texts[start : start + batch_size]
            payload = {"input": batch if len(batch) > 1 else batch[0]}

            max_attempts = 5
            for attempt in range(1, max_attempts + 1):
                try:
                    resp = client.post(url, json=payload, headers=headers)
                    if resp.status_code in (401, 403):
                        raise DatabricksEmbeddingAuthError(
                            "Databricks PAT needs the **model-serving** scope to call Foundation "
                            "Model embedding endpoints. In the workspace: Settings → Developer → "
                            "Access tokens → Generate new token → enable model-serving. "
                            "Or set EG_EMBEDDING_PROVIDER=gemini in .env. "
                            f"Response: {resp.text[:400]}"
                        )
                    if resp.status_code >= 400:
                        raise DatabricksEmbeddingError(
                            f"Databricks embed HTTP {resp.status_code}: {resp.text[:500]}"
                        )
                    data = resp.json()
                    vectors = _parse_embeddings_payload(data)
                    if len(vectors) != len(batch):
                        raise DatabricksEmbeddingError(
                            f"Expected {len(batch)} embeddings, got {len(vectors)}"
                        )
                    all_vectors.extend(vectors)
                    if batch_idx == 0 or batch_idx + 1 == total_batches:
                        log.info(
                            "databricks_embed_batch",
                            endpoint=endpoint,
                            batch=batch_idx + 1,
                            total_batches=total_batches,
                            items=len(batch),
                        )
                    break
                except Exception as exc:
                    if _is_rate_limit(exc) and attempt < max_attempts:
                        wait_s = _retry_after_seconds(exc)
                        log.warning(
                            "databricks_embed_rate_limited",
                            attempt=attempt,
                            wait_seconds=wait_s,
                        )
                        time.sleep(wait_s)
                        continue
                    raise

    return all_vectors
