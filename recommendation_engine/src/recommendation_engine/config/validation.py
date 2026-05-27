"""Validate production runtime requirements before pipeline execution."""

from __future__ import annotations

from recommendation_engine.config.settings import Settings


class ConfigurationError(Exception):
    """Missing or invalid configuration for a live run."""


def validate_production_config(settings: Settings) -> None:
    errors: list[str] = []

    if settings.llm_mode.lower() != "live":
        errors.append("EG_LLM_MODE must be 'live' (mock mode is disabled for production runs).")
    if not settings.google_api_key:
        errors.append("GOOGLE_API_KEY or GEMINI_API_KEY is required.")
    if not settings.use_databricks_embeddings and not settings.google_api_key:
        errors.append(
            "Embeddings require DATABRICKS_HOST + DATABRICKS_TOKEN "
            "(EG_EMBEDDING_PROVIDER=databricks) or GOOGLE_API_KEY (gemini)."
        )
    if not settings.use_s3:
        errors.append("EG_DATA_SOURCE must be 's3'.")
    if settings.allow_fixtures:
        errors.append("EG_ALLOW_FIXTURES must not be set for production runs.")

    if errors:
        raise ConfigurationError(
            "Production configuration incomplete:\n- " + "\n- ".join(errors)
        )
