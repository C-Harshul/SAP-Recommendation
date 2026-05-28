"""Typed errors for connector and runtime handling."""

from __future__ import annotations


class IngestionError(Exception):
    """Base for ingestion-layer errors."""


class ConnectorError(IngestionError):
    """Non-retryable connector failure (bad config, parse error)."""


class RateLimitError(IngestionError):
    """Source or local rate limit exceeded."""

    def __init__(self, source_id: str, message: str = "Rate limit exceeded") -> None:
        self.source_id = source_id
        super().__init__(message)


class SourceUnavailableError(IngestionError):
    """Transient upstream failure (5xx, timeout)."""

    def __init__(self, source_id: str, message: str = "Source unavailable") -> None:
        self.source_id = source_id
        super().__init__(message)


class StateError(IngestionError):
    """Cursor / state store failure."""


class WriteError(IngestionError):
    """S3 write failure."""
