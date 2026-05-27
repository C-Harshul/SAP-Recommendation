"""Embeddings — Databricks Foundation Model APIs (default) or Gemini fallback."""

from __future__ import annotations

import re
import time

import numpy as np
import structlog

from recommendation_engine.config.settings import Settings, get_settings
from recommendation_engine.io.databricks_embeddings import (
    DatabricksEmbeddingError,
    embed_texts_databricks,
    is_auth_or_scope_error,
)

log = structlog.get_logger()

GEMINI_EMBED_API_BATCH_MAX = 100


class EmbeddingNotConfiguredError(RuntimeError):
    pass


def _is_embed_rate_limit(exc: BaseException) -> bool:
    text = str(exc)
    return (
        "429" in text
        or "RESOURCE_EXHAUSTED" in text
        or "rate limit" in text.lower()
        or "RPM" in text
    )


def _retry_seconds_from_error(exc: BaseException) -> float:
    match = re.search(r"retry in (\d+(?:\.\d+)?)s", str(exc), re.I)
    if match:
        return float(match.group(1)) + 2.0
    return 15.0


class EmbeddingClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._gemini = None
        provider = self._settings.embedding_provider.lower()

        # Keep Gemini available for fallback when Databricks token lacks model-serving scope
        if self._settings.google_api_key:
            from google import genai

            self._gemini = genai.Client(api_key=self._settings.google_api_key)

        if not self._settings.has_databricks_embeddings and not self._gemini:
            raise EmbeddingNotConfiguredError(
                "Embeddings require DATABRICKS_HOST + DATABRICKS_TOKEN (with model-serving scope), "
                "or GOOGLE_API_KEY with EG_EMBEDDING_PROVIDER=gemini."
            )
        if provider == "databricks" and not self._settings.has_databricks_embeddings:
            raise EmbeddingNotConfiguredError(
                "EG_EMBEDDING_PROVIDER=databricks but DATABRICKS_TOKEN is missing."
            )

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._settings.use_databricks_embeddings:
            try:
                return embed_texts_databricks(texts, settings=self._settings)
            except Exception as exc:
                if self._gemini and (
                    isinstance(exc, DatabricksEmbeddingError)
                    or _is_embed_rate_limit(exc)
                    or is_auth_or_scope_error(exc)
                ):
                    log.warning(
                        "databricks_embed_fallback_gemini",
                        reason="auth_scope" if is_auth_or_scope_error(exc) else "error",
                        error=str(exc)[:300],
                        count=len(texts),
                    )
                    return self._embed_gemini(texts)
                raise
        return self._embed_gemini(texts)

    def _gemini_batch_size(self) -> int:
        return min(
            max(1, self._settings.embedding_batch_size),
            GEMINI_EMBED_API_BATCH_MAX,
        )

    def _embed_gemini(self, texts: list[str]) -> list[list[float]]:
        if not self._gemini:
            raise EmbeddingNotConfiguredError(
                "Gemini embeddings unavailable. Set GOOGLE_API_KEY or Databricks credentials."
            )
        batch_size = self._gemini_batch_size()
        delay = max(0.0, self._settings.embedding_request_delay_seconds)
        vectors: list[list[float]] = []
        total_batches = (len(texts) + batch_size - 1) // batch_size

        for batch_idx, start in enumerate(range(0, len(texts), batch_size)):
            if batch_idx > 0 and delay > 0:
                time.sleep(delay)
            batch = texts[start : start + batch_size]
            vectors.extend(self._embed_gemini_batch(batch, batch_idx + 1, total_batches))

        return vectors

    def _embed_gemini_batch(
        self,
        batch: list[str],
        batch_num: int,
        total_batches: int,
    ) -> list[list[float]]:
        assert self._gemini is not None
        max_attempts = 6
        for attempt in range(1, max_attempts + 1):
            try:
                result = self._gemini.models.embed_content(
                    model=self._settings.gemini_embedding_model,
                    contents=batch,
                )
                if batch_num == 1 or batch_num == total_batches or batch_num % 5 == 0:
                    log.info(
                        "gemini_embed_batch",
                        batch=batch_num,
                        total_batches=total_batches,
                        items=len(batch),
                    )
                return [list(e.values) for e in result.embeddings]
            except Exception as exc:
                if _is_embed_rate_limit(exc) and attempt < max_attempts:
                    wait_s = _retry_seconds_from_error(exc)
                    log.warning(
                        "gemini_embed_rate_limited",
                        batch=batch_num,
                        attempt=attempt,
                        wait_seconds=wait_s,
                    )
                    time.sleep(wait_s)
                    continue
                raise
        raise RuntimeError("unreachable")

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.array(a, dtype=np.float64)
    vb = np.array(b, dtype=np.float64)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)
